import json
import random
import re
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Text, Tuple

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher


NUM_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}

TENS_WORDS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

SCALE_WORDS = {
    "hundred": 100,
    "thousand": 1000,
}

IGNORED_TOKENS = {
    "and",
    "room",
    "rooms",
    "night",
    "nights",
    "guest",
    "guests",
    "people",
    "persons",
    "person",
}


def _generate_booking_reference(prefix: str = "SA-") -> str:
    random_digits = "".join(random.choices(string.digits, k=6))
    return f"{prefix}{random_digits}"


def _parse_numeric_value(value: Any) -> Optional[float]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().lower()
    if not text:
        return None

    # remove commas and non numeric symbols except dot and minus
    cleaned = re.sub(r"[^0-9\.\-\s]", "", text)
    try:
        return float(cleaned)
    except ValueError:
        pass

    tokens = text.replace("-", " ").replace(",", " ").split()
    if not tokens:
        return None

    total = 0
    current = 0

    for token in tokens:
        if token in NUM_WORDS:
            current += NUM_WORDS[token]
        elif token in TENS_WORDS:
            current += TENS_WORDS[token]
        elif token in SCALE_WORDS:
            multiplier = SCALE_WORDS[token]
            if current == 0:
                current = 1
            current *= multiplier
            total += current
            current = 0
        else:
            if token in IGNORED_TOKENS:
                continue
            return None

    return float(total + current)


def _validate_date(date_str: str) -> tuple[bool, Optional[str]]:
    """Validate date string. Returns (is_valid, error_message or None)."""
    if not date_str or not date_str.strip():
        return False, None
    
    date_str = date_str.strip()
    
    # Common date formats to try
    formats = [
        "%d %B %Y",      # 15 February 2024
        "%d %b %Y",      # 15 Feb 2024
        "%d-%m-%Y",      # 15-02-2024
        "%d/%m/%Y",      # 15/02/2024
        "%Y-%m-%d",      # 2024-02-15
        "%d.%m.%Y",      # 15.02.2024
        "%B %d, %Y",     # February 15, 2024
        "%b %d, %Y",     # Feb 15, 2024
        "%d %B",         # 15 February (assume current year)
        "%d %b",         # 15 Feb (assume current year)
    ]
    
    parsed_date = None
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            # If format doesn't include year, assume current or next year
            if "%Y" not in fmt:
                now = datetime.now()
                if parsed_date.replace(year=now.year) < now:
                    parsed_date = parsed_date.replace(year=now.year + 1)
                else:
                    parsed_date = parsed_date.replace(year=now.year)
            break
        except ValueError:
            continue
    
    if parsed_date is None:
        return False, "I couldn't understand that date format."
    
    # Check if date is in the past (allow today)
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    check_date = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if check_date < now:
        return False, "That date is in the past. Please provide a future date."
    
    # Check for impossible dates (like 44 February)
    day = parsed_date.day
    month = parsed_date.month
    year = parsed_date.year
    
    # Basic sanity check
    if day > 31 or month > 12:
        return False, "That date doesn't exist. Please provide a valid date."
    
    # Check if day exists in that month
    try:
        datetime(year, month, day)
    except ValueError:
        return False, f"That date doesn't exist. {month}/{day}/{year} is not a valid date. Please provide a valid date like '15 February 2024' or '15/02/2024'."
    
    return True, None


def _validate_positive_number(value: Any, field_name: str = "number", allow_zero: bool = False) -> tuple[bool, Optional[str], Optional[float]]:
    """Validate that a number is positive (and optionally non-zero). Returns (is_valid, error_message or None, parsed_value or None)."""
    parsed = _parse_numeric_value(value)
    
    if parsed is None:
        return False, f"I didn't understand that {field_name}. Please provide a number.", None
    
    if parsed < 0:
        return False, f"{field_name.capitalize()} cannot be negative. Please provide a positive number.", None
    
    if not allow_zero and parsed == 0:
        return False, f"{field_name.capitalize()} cannot be zero. Please provide a number greater than zero.", None
    
    return True, None, parsed


def _is_question(message: str) -> bool:
    """Check if the message is a question."""
    if not message:
        return False
    message_lower = message.lower().strip()
    question_words = ["what", "which", "how", "when", "where", "why", "who", "tell me", "can you", "do you", "is there", "are there", "i don't know", "i dont know"]
    return any(word in message_lower for word in question_words)


def _is_facility_question(message: str) -> Tuple[bool, Optional[str]]:
    """Check if the message is asking about facilities and return the response if it is."""
    if not message:
        return False, None
    
    message_lower = message.lower().strip()
    
    # Facility keywords
    facility_keywords = {
        "pool": "The pool is open daily from 07:30 to 18:00.",
        "parking": "Parking is available for €5 per 24 hours.",
        "breakfast": "Breakfast is served daily from 07:00 to 10:00.",
        "lunch": "Lunch is served daily from 12:00 to 14:00.",
        "dinner": "Dinner is served daily from 18:00 to 21:00.",
        "gym": "Our gym is open 24/7 and includes cardio equipment and free weights.",
        "wifi": "Free WiFi is available throughout the hotel.",
        "accessibility": "Our hotel is fully accessible. We have an elevator/lift available, and all areas including rooms, restaurant, pool, and common areas are wheelchair accessible. Our staff is available 24/7 to assist with mobility needs. If you need assistance during your stay, please let us know and we'll be happy to help.",
        "disabled": "Our hotel is fully accessible. We have an elevator/lift available, and all areas including rooms, restaurant, pool, and common areas are wheelchair accessible. Our staff is available 24/7 to assist with mobility needs. If you need assistance during your stay, please let us know and we'll be happy to help.",
        "wheelchair": "Our hotel is fully accessible. We have an elevator/lift available, and all areas including rooms, restaurant, pool, and common areas are wheelchair accessible. Our staff is available 24/7 to assist with mobility needs. If you need assistance during your stay, please let us know and we'll be happy to help.",
        "lift": "Yes, we have an elevator/lift available.",
        "elevator": "Yes, we have an elevator/lift available.",
    }
    
    # Room type information
    room_summary = "Standard rooms are €50 per night and suites are €120 per night. Both offer king-size beds that can be converted into two singles on request, plus a refrigerator, shower, and full bathroom; suites include 3 rooms with king-size beds and a second WC."
    
    # Check for room type questions (but NOT simple selections like "standard" or "suite" alone)
    # Simple selections should be handled by ValidateRoomType, not here
    if len(message_lower.split()) <= 2 and (message_lower == "standard" or message_lower == "suite" or message_lower == "standard room" or message_lower == "suite room"):
        # This is a selection, not a question
        return False, None
    
    # Check for room type questions
    room_type_keywords = ["what type of rooms", "what rooms", "room types", "types of rooms", "difference", "differences", "what is the difference", "what are the", "tell me about"]
    if any(keyword in message_lower for keyword in room_type_keywords):
        return True, room_summary
    
    # Also check if it contains "room" or "rooms" but only if it's clearly a question
    if ("room" in message_lower or "rooms" in message_lower) and any(q_word in message_lower for q_word in ["what", "which", "how", "tell me", "can you", "do you"]):
        return True, room_summary
    
    # Check for price/cost questions
    price_keywords = ["price", "cost", "how much", "pricing", "rate", "rates"]
    if any(keyword in message_lower for keyword in price_keywords):
        return True, room_summary
    
    # Check for facility keywords
    for keyword, response in facility_keywords.items():
        if keyword in message_lower:
            return True, response
    
    return False, None


def _ask_for_current_slot(tracker: Tracker, dispatcher: CollectingDispatcher, slot_name: str, domain: Dict[Text, Any] = None) -> None:
    """Ask for the current slot based on which slot is being collected."""
    guests = tracker.get_slot("guests")
    room_type = tracker.get_slot("room_type")
    arrival_date = tracker.get_slot("arrival_date")
    departure_date = tracker.get_slot("departure_date")
    payment_option = tracker.get_slot("payment_option")
    
    # Determine which slot we're currently collecting and ask for it
    if slot_name == "guests" and not guests:
        dispatcher.utter_message(text="For how many guests?")
    elif slot_name == "room_type" and not room_type:
        dispatcher.utter_message(text="Which room would you like? (standard or suite)")
    elif slot_name == "arrival_date" and not arrival_date:
        # Show calendar widget - create calendar data directly to avoid circular import
        try:
            today = datetime.now()
            calendar_data = {
                "type": "calendar",
                "mode": "booking",
                "message": "Please select your arrival and departure date",
                "min_date": today.strftime("%Y-%m-%d"),
                "arrival_date": None,
                "departure_date": None,
            }
            dispatcher.utter_message(text="Please select your arrival and departure date:")
            dispatcher.utter_message(text="", custom=json.dumps(calendar_data))
        except Exception as e:
            dispatcher.utter_message(text="Please select your arrival and departure date:")
    elif slot_name == "departure_date" and not departure_date:
        # Show calendar widget - create calendar data directly to avoid circular import
        try:
            today = datetime.now()
            arrival_date = tracker.get_slot("arrival_date")
            calendar_data = {
                "type": "calendar",
                "mode": "booking",
                "message": "Please select your arrival and departure date",
                "min_date": today.strftime("%Y-%m-%d"),
                "arrival_date": arrival_date if arrival_date else None,
                "departure_date": None,
            }
            dispatcher.utter_message(text="Please select your arrival and departure date:")
            dispatcher.utter_message(text="", custom=json.dumps(calendar_data))
        except Exception as e:
            dispatcher.utter_message(text="Please select your departure date:")
    elif slot_name == "payment_option" and not payment_option:
        dispatcher.utter_message(text="Would you like to pay at the front desk or complete the payment online now?")


class ActionValidateDate(Action):
    """Validate arrival date and provide friendly error messages."""
    def name(self) -> Text:
        return "action_validate_date"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        arrival_date = tracker.get_slot("arrival_date")
        
        if not arrival_date:
            return []
        
        is_valid, error_msg = _validate_date(arrival_date)
        
        if not is_valid:
            if error_msg:
                dispatcher.utter_message(
                    text=(
                        f"I noticed an issue with the date: {error_msg} "
                        "Could you please provide a valid arrival date? "
                        "For example: '15 February 2024', '15/02/2024', or '2024-02-15'."
                    )
                )
            else:
                dispatcher.utter_message(
                    text=(
                        "I didn't quite catch the arrival date. "
                        "Could you provide it in a format like '15 February 2024', '15/02/2024', or '2024-02-15'?"
                    )
                )
            # Clear the slot to ask again (Rasa flow will handle this automatically)
            return [SlotSet("arrival_date", None)]
        
        return []


class ActionValidateNights(Action):
    """Validate number of nights and provide friendly error messages."""
    def name(self) -> Text:
        return "action_validate_nights"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        nights = tracker.get_slot("nights")
        
        if not nights:
            return []
        
        # Check if the input looks like a date or month (common mistake)
        nights_lower = str(nights).lower()
        month_names = ["january", "february", "march", "april", "may", "june", 
                      "july", "august", "september", "october", "november", "december",
                      "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        
        if any(month in nights_lower for month in month_names):
            dispatcher.utter_message(
                text=(
                    "I think there might be some confusion. You mentioned a month, but I'm asking for the number of nights you'd like to stay. "
                    "For example, if you want to stay for 3 nights, just say '3' or 'three nights'. "
                    "Could you tell me how many nights you'd like to stay?"
                )
            )
            return [SlotSet("nights", None)]
        
        is_valid, error_msg, parsed_value = _validate_positive_number(nights, "number of nights", allow_zero=False)
        
        if not is_valid:
            dispatcher.utter_message(
                text=(
                    f"{error_msg} "
                    "For example, you could say 'one night', 'two nights', or just '1' or '2'."
                )
            )
            return [SlotSet("nights", None)]
        
        # Check for unreasonably high numbers
        if parsed_value and parsed_value > 365:
            dispatcher.utter_message(
                text=(
                    f"{int(parsed_value)} nights seems like a very long stay (more than a year). "
                    "Could you please confirm the number of nights? For example, '3 nights' or '7 nights'."
                )
            )
            return [SlotSet("nights", None)]
        
        return [SlotSet("nights", str(int(parsed_value)))]


class ActionValidateRooms(Action):
    """Validate number of rooms and provide friendly error messages."""
    def name(self) -> Text:
        return "action_validate_rooms"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        rooms = tracker.get_slot("rooms")
        
        if not rooms:
            return []
        
        is_valid, error_msg, parsed_value = _validate_positive_number(rooms, "number of rooms", allow_zero=False)
        
        if not is_valid:
            dispatcher.utter_message(
                text=(
                    f"{error_msg} "
                    "For example, you could say 'one room', 'two rooms', or just '1' or '2'."
                )
            )
            return [SlotSet("rooms", None)]
        
        return [SlotSet("rooms", str(int(parsed_value)))]


class ActionValidateGuests(Action):
    """Validate number of guests and provide friendly error messages."""
    def name(self) -> Text:
        return "action_validate_guests"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        guests = tracker.get_slot("guests")
        information_sufficient = tracker.get_slot("information_sufficient")

        if not guests:
            # Only ask if information_sufficient is NOT "asked"
            if information_sufficient != "asked":
                dispatcher.utter_message(text="For how many guests?")
            return []
        
        is_valid, error_msg, parsed_value = _validate_positive_number(guests, "number of guests", allow_zero=False)
        
        if not is_valid:
            dispatcher.utter_message(
                text=(
                    f"{error_msg} "
                    "For example, you could say 'one guest', 'two guests', or just '1' or '2'."
                )
            )
            return [SlotSet("guests", None)]
        
        return [SlotSet("guests", str(int(parsed_value)))]


class ActionConfirmReservationHold(Action):
    def name(self) -> Text:
        return "action_confirm_reservation_hold"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        arrival_date = tracker.get_slot("arrival_date") or "your requested date"
        nights = tracker.get_slot("nights")
        nights_value = _parse_numeric_value(nights)
        if nights_value is not None:
            nights_text = f" for {int(nights_value)} night(s)"
        elif nights:
            nights_text = f" for {nights} night(s)"
        else:
            nights_text = ""
        dispatcher.utter_message(
            text=(
                f"Perfect. I'll keep your reservation active starting {arrival_date}{nights_text} "
                "until you arrive to pay at the front desk."
            )
        )
        return []


class ActionSendPaymentLink(Action):
    def name(self) -> Text:
        return "action_send_payment_link"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        reference_stub = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        payment_url = f"https://stayassist.example/pay/{reference_stub}"
        dispatcher.utter_message(
            text=(
                "I've generated a secure payment link for you. "
                f"Please complete the payment here: {payment_url}"
            )
        )
        dispatcher.utter_message(
            text="Let me know once the payment is done so I can finalize the booking."
        )
        return []


class ActionConfirmPaymentReceived(Action):
    def name(self) -> Text:
        return "action_confirm_payment_received"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(
            text="Great, I have marked your online payment as received."
        )
        return []


class ActionGenerateBookingNumber(Action):
    def name(self) -> Text:
        return "action_generate_booking_number"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        existing_reference: Optional[Text] = tracker.get_slot("booking_reference")
        booking_reference = existing_reference or _generate_booking_reference()
        dispatcher.utter_message(
            text=(
                f"Your booking reference is {booking_reference}. "
                "Please keep it handy for payments, changes, or cancellations."
            )
        )
        return [SlotSet("booking_reference", booking_reference)]


class ActionCancelBooking(Action):
    def name(self) -> Text:
        return "action_cancel_booking"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        provided = (tracker.get_slot("booking_number") or "").strip().upper()
        stored = (tracker.get_slot("booking_reference") or "").strip().upper()

        if not provided:
            dispatcher.utter_message(text="I didn't catch a booking number to cancel.")
            return []

        if not stored:
            dispatcher.utter_message(
                text=(
                    "I don't have an active booking reference on file. "
                    "Please double-check the number or create a new reservation."
                )
            )
            return []

        if provided == stored:
            dispatcher.utter_message(
                text=f"Booking {stored} has been cancelled. You're always welcome to book again!"
            )
            return [SlotSet("booking_reference", None), SlotSet("booking_number", None)]

        dispatcher.utter_message(
            text=(
                f"I couldn't match booking number {provided} to the reservation on file. "
                "Please verify the number and try again."
            )
        )
        return []


class ActionAnswerFacilityQuestion(Action):
    def name(self) -> Text:
        return "action_answer_facility_question"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        topic = (tracker.get_slot("facility_topic") or "").lower()
        room_summary = (
            "Standard rooms are €50 per night and suites are €120 per night. "
            "Both offer king-size beds that can be converted into two singles on request, "
            "plus a refrigerator, shower, and full bathroom; suites include a second WC."
        )
        info_map = {
            "pool": "The pool is open daily from 07:30 to 18:00.",
            "parking": "Parking is available for €5 per 24 hours.",
            "breakfast": "Breakfast is served from 07:00 to 11:00.",
            "lunch": "Lunch is available from 13:00 to 15:00.",
            "dinner": "Dinner service runs from 18:00 to 20:00.",
            "gym": "The gym is open 24 hours a day.",
            "suite": room_summary + " Suites also include extra living space for added comfort.",
            "standard": room_summary,
            "room": room_summary,
        }

        response = None
        for keyword, message in info_map.items():
            if keyword in topic:
                response = message
                break

        if response is None:
            response = (
                "Here's a quick overview: "
                f"{room_summary} Pool 07:30-18:00, parking €5/24h, "
                "breakfast 07:00-11:00, lunch 13:00-15:00, dinner 18:00-20:00, gym 24/7. "
                "Let me know if you need details on anything else."
            )

        dispatcher.utter_message(text=response)
        return []


class ActionClarifyExplanation(Action):
    """Provide simpler, step-by-step explanation when guest doesn't understand."""
    def name(self) -> Text:
        return "action_clarify_explanation"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        # Get the last bot message to provide a simpler version
        last_bot_message = None
        for event in reversed(tracker.events):
            if event.get("event") == "bot" and event.get("text"):
                last_bot_message = event.get("text")
                break
        
        if last_bot_message:
            dispatcher.utter_message(
                text=(
                    "Let me explain that in a simpler way. "
                    "I'll break it down step by step so it's easier to understand. "
                    "If anything is still unclear, just let me know and I'll explain it differently."
                )
            )
            # The LLM will handle the actual simplification via the rephrase prompt
        else:
            dispatcher.utter_message(
                text=(
                    "I'm here to help! Could you tell me which part you'd like me to explain? "
                    "I can break things down step by step to make it clearer."
                )
            )
        
        return []


class ValidateRoomType(Action):
    """Validate room type - automatically called by Rasa when room_type slot is set."""
    def name(self) -> Text:
        return "validate_room_type"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        latest_message = tracker.latest_message.get("text", "") if tracker.latest_message else ""
        latest_lower = latest_message.lower().strip()

        # Check if user is responding to "is information sufficient" question
        information_sufficient = tracker.get_slot("information_sufficient")
        if information_sufficient == "asked":
            latest_lower = latest_message.lower().strip()
            yes_words = ["yes", "yeah", "yep", "sure", "ok", "okay", "continue", "go ahead", "ja", "jep", "oké", "doorgaan", "proceed", "let's go", "lets go", "i dont need anymore", "i don't need anymore", "no more", "no more questions"]
            if any(word in latest_lower for word in yes_words):
                dispatcher.utter_message(text="Great! Let's continue with your booking.")
                # CRITICAL: Ask for room_type again - clear the slot to restart collection
                dispatcher.utter_message(text="Which room would you like? (standard or suite)")
                return [SlotSet("information_sufficient", None), SlotSet("room_type", None)]
            elif any(word in latest_lower for word in ["no", "nope", "nee", "more", "else", "other", "another"]) and "no more" not in latest_lower and "don't need" not in latest_lower:
                dispatcher.utter_message(text="Of course! What else would you like to know?")
                return [SlotSet("information_sufficient", None)]
            # CRITICAL: If information_sufficient is "asked" but user hasn't responded yes/no yet, wait
            # Return empty list to prevent Rasa from automatically continuing
            return []

        # FIRST: Check if the message is just a number (like "2", "3", etc.) - this is NOT a room type
        # Numbers are answers to "how many guests", not "which room type"
        try:
            # Try to parse as number
            float(latest_lower)
            # If it's just a number, clear the slot and return - this is not a room type
            return [SlotSet("room_type", None)]
        except ValueError:
            # Not a pure number, continue
            pass

        # SECOND: Check if it's a valid room type selection (standard or suite)
        # This must come BEFORE checking if it's a question, otherwise "standard" gets treated as a question
        if "standard" in latest_lower and len(latest_lower.split()) <= 2:
            # Simple selection like "standard" or "standard room"
            return [SlotSet("room_type", "standard")]
        elif "suite" in latest_lower and len(latest_lower.split()) <= 2:
            # Simple selection like "suite" or "suite room"
            return [SlotSet("room_type", "suite")]

        # Get the slot value (might be set by LLM mapping)
        room_type = tracker.get_slot("room_type")
        if room_type:
            room_type_lower = str(room_type).lower().strip()
            # CRITICAL: If slot is "waiting", it means we're waiting for user to say "continue"
            # Don't process it, just return empty list to wait
            # Check if slot value is just a number - if so, clear it
            try:
                float(room_type_lower)
                return [SlotSet("room_type", None)]
            except ValueError:
                pass
            # Normalize room type
            if "standard" in room_type_lower:
                return [SlotSet("room_type", "standard")]
            elif "suite" in room_type_lower:
                return [SlotSet("room_type", "suite")]

        # SECOND: Check if it's a question about available rooms (only if not a valid selection)
        is_question = _is_question(latest_message)
        if is_question:
            is_facility, facility_response = _is_facility_question(latest_message)
            if is_facility and facility_response:
                dispatcher.utter_message(text=facility_response)
                dispatcher.utter_message(
                    text="I hope I've provided you with sufficient information. Is there anything else you'd like to know, or shall we continue with your booking?"
                )
                # CRITICAL: Only set information_sufficient to "asked", keep slot as None
                # The validate action will check information_sufficient and not ask if it's "asked"
                return [SlotSet("information_sufficient", "asked")]
            # If it's a question but not a facility question, clear the slot
            return [SlotSet("room_type", None)]

        # If no room_type slot and not a question, it's invalid
        if not room_type:
            dispatcher.utter_message(
                text="I didn't understand that. Please choose either 'standard' or 'suite'."
            )
            return [SlotSet("room_type", None)]

        return []


class ActionShowBookingCalendar(Action):
    """Show a booking calendar widget for selecting both arrival and departure dates."""
    def name(self) -> Text:
        return "action_show_booking_calendar"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        try:
            # First send the text message
            dispatcher.utter_message(text="Please select your arrival and departure date:")
            
            # Then send the calendar widget separately
            today = datetime.now()
            arrival_date = tracker.get_slot("arrival_date")
            departure_date = tracker.get_slot("departure_date")
            
            calendar_data = {
                "type": "calendar",
                "mode": "booking",  # Special mode for booking with both dates
                "message": "Please select your arrival and departure date",
                "min_date": today.strftime("%Y-%m-%d"),
                "arrival_date": arrival_date if arrival_date else None,
                "departure_date": departure_date if departure_date else None,
            }
            
            dispatcher.utter_message(
                text="",
                custom=json.dumps(calendar_data)
            )
            return []
        except Exception as e:
            # Fallback: just send the text message if there's an error
            dispatcher.utter_message(text="Please select your arrival and departure date:")
            return []


class ValidateArrivalDate(Action):
    """Validate arrival date - automatically called by Rasa when arrival_date slot is set."""
    def name(self) -> Text:
        return "validate_arrival_date"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        latest_message = tracker.latest_message.get("text", "") if tracker.latest_message else ""
        is_question = _is_question(latest_message)
        is_facility, facility_response = _is_facility_question(latest_message)

        # Check if user is responding to "is information sufficient" question
        information_sufficient = tracker.get_slot("information_sufficient")
        if information_sufficient == "asked":
            latest_lower = latest_message.lower().strip()
            yes_words = ["yes", "yeah", "yep", "sure", "ok", "okay", "continue", "go ahead", "ja", "jep", "oké", "doorgaan", "proceed", "let's go", "lets go", "i dont need anymore", "i don't need anymore", "no more", "no more questions"]
            if any(word in latest_lower for word in yes_words):
                dispatcher.utter_message(text="Great! Let's continue with your booking.")
                # CRITICAL: Show calendar widget again for arrival_date - clear the slot to restart collection
                try:
                    today = datetime.now()
                    calendar_data = {
                        "type": "calendar",
                        "mode": "booking",
                        "message": "Please select your arrival and departure date",
                        "min_date": today.strftime("%Y-%m-%d"),
                        "arrival_date": None,
                        "departure_date": None,
                    }
                    dispatcher.utter_message(text="Please select your arrival and departure date:")
                    dispatcher.utter_message(text="", custom=json.dumps(calendar_data))
                except Exception as e:
                    dispatcher.utter_message(text="Please select your arrival and departure date:")
                return [SlotSet("information_sufficient", None), SlotSet("arrival_date", None)]
            elif any(word in latest_lower for word in ["no", "nope", "nee", "more", "else", "other", "another"]) and "no more" not in latest_lower and "don't need" not in latest_lower:
                dispatcher.utter_message(text="Of course! What else would you like to know?")
                return [SlotSet("information_sufficient", None)]
            # CRITICAL: If information_sufficient is "asked" but user hasn't responded yes/no yet, wait
            # Return empty list to prevent Rasa from automatically continuing
            return []

        if is_question or (is_facility and facility_response):
            if is_facility and facility_response:
                dispatcher.utter_message(text=facility_response)
                dispatcher.utter_message(
                    text="I hope I've provided you with sufficient information. Is there anything else you'd like to know, or shall we continue with your booking?"
                )
                # CRITICAL: Only set information_sufficient to "asked", keep slot as None
                # The validate action will check information_sufficient and not ask if it's "asked"
                return [SlotSet("information_sufficient", "asked")]
            return [SlotSet("arrival_date", None)]

        arrival_date = tracker.get_slot("arrival_date")
        
        # CRITICAL: If slot is "waiting", it means we're waiting for user to say "continue"
        # Don't process it, just return empty list to wait
        # Check if booking calendar was just shown
        latest_action = None
        events_list = list(tracker.events)
        for i in range(len(events_list) - 1, max(-1, len(events_list) - 20), -1):
            event = events_list[i]
            if hasattr(event, 'action_name') and event.action_name == 'action_show_booking_calendar':
                latest_action = event.action_name
                break
        
        if latest_action == 'action_show_booking_calendar' and not arrival_date:
            return []

        if not arrival_date:
            return []

        is_valid, error_msg = _validate_date(arrival_date)
        if not is_valid:
            return [SlotSet("arrival_date", None)]

        return []


class ValidateDepartureDate(Action):
    """Validate departure date - automatically called by Rasa when departure_date slot is set."""
    def name(self) -> Text:
        return "validate_departure_date"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        latest_message = tracker.latest_message.get("text", "") if tracker.latest_message else ""
        
        is_question = _is_question(latest_message)
        is_facility, facility_response = _is_facility_question(latest_message)

        # Check if user is responding to "is information sufficient" question
        information_sufficient = tracker.get_slot("information_sufficient")
        if information_sufficient == "asked":
            latest_lower = latest_message.lower().strip()
            yes_words = ["yes", "yeah", "yep", "sure", "ok", "okay", "continue", "go ahead", "ja", "jep", "oké", "doorgaan", "proceed", "let's go", "lets go", "i dont need anymore", "i don't need anymore", "no more", "no more questions"]
            if any(word in latest_lower for word in yes_words):
                dispatcher.utter_message(text="Great! Let's continue with your booking.")
                try:
                    today = datetime.now()
                    arrival_date = tracker.get_slot("arrival_date")
                    calendar_data = {
                        "type": "calendar",
                        "mode": "booking",
                        "message": "Please select your arrival and departure date",
                        "min_date": today.strftime("%Y-%m-%d"),
                        "arrival_date": arrival_date if arrival_date else None,
                        "departure_date": None,
                    }
                    dispatcher.utter_message(text="Please select your arrival and departure date:")
                    dispatcher.utter_message(text="", custom=json.dumps(calendar_data))
                except Exception as e:
                    dispatcher.utter_message(text="Please select your departure date:")
                return [SlotSet("information_sufficient", None), SlotSet("departure_date", None)]
            elif any(word in latest_lower for word in ["no", "nope", "nee", "more", "else", "other", "another"]) and "no more" not in latest_lower and "don't need" not in latest_lower:
                dispatcher.utter_message(text="Of course! What else would you like to know?")
                return [SlotSet("information_sufficient", None)]
            # CRITICAL: If information_sufficient is "asked" but user hasn't responded yes/no yet, wait
            # Return empty list to prevent Rasa from automatically continuing
            return []

        if is_question or (is_facility and facility_response):
            if is_facility and facility_response:
                dispatcher.utter_message(text=facility_response)
                dispatcher.utter_message(
                    text="I hope I've provided you with sufficient information. Is there anything else you'd like to know, or shall we continue with your booking?"
                )
                # CRITICAL: Only set information_sufficient to "asked", keep slot as None
                # The validate action will check information_sufficient and not ask if it's "asked"
                return [SlotSet("information_sufficient", "asked")]
            return [SlotSet("departure_date", None)]

        departure_date = tracker.get_slot("departure_date")
        arrival_date = tracker.get_slot("arrival_date")

        # CRITICAL: If slot is "waiting", it means we're waiting for user to say "continue"
        # Don't process it, just return empty list to wait
        # If both dates are already set, validate them
        if arrival_date and departure_date:
            is_arrival_valid, _ = _validate_date(arrival_date)
            is_departure_valid, _ = _validate_date(departure_date)

            if is_arrival_valid and is_departure_valid:
                # Parse dates to compare
                arrival_parsed = None
                departure_parsed = None
                for fmt in ["%d %B %Y", "%d %b %Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y", "%B %d, %Y", "%b %d, %Y"]:
                    try:
                        if arrival_date:
                            arrival_parsed = datetime.strptime(arrival_date, fmt)
                        if departure_date:
                            departure_parsed = datetime.strptime(departure_date, fmt)
                        break
                    except ValueError:
                        continue
                
                if arrival_parsed and departure_parsed:
                    if departure_parsed <= arrival_parsed:
                        arrival_str = arrival_parsed.strftime("%d %B %Y")
                        dispatcher.utter_message(
                            text=f"The departure date must be after the arrival date ({arrival_str}). Please select a later date."
                        )
                        return [SlotSet("departure_date", None)]
            return []

        if not departure_date:
            return []

        is_valid, error_msg = _validate_date(departure_date)
        if not is_valid:
            return [SlotSet("departure_date", None)]

        # Check if departure is after arrival
        if arrival_date:
            arrival_parsed = None
            departure_parsed = None
            for fmt in ["%d %B %Y", "%d %b %Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y", "%B %d, %Y", "%b %d, %Y"]:
                try:
                    if arrival_date:
                        arrival_parsed = datetime.strptime(arrival_date, fmt)
                    if departure_date:
                        departure_parsed = datetime.strptime(departure_date, fmt)
                    break
                except ValueError:
                    continue

            if arrival_parsed and departure_parsed:
                if departure_parsed <= arrival_parsed:
                    arrival_str = arrival_parsed.strftime("%d %B %Y")
                    dispatcher.utter_message(
                        text=f"The departure date must be after the arrival date ({arrival_str}). Please select a later date."
                    )
                    return [SlotSet("departure_date", None)]

        return []


class ValidatePaymentOption(Action):
    """Validate payment option - automatically called by Rasa when payment_option slot is set."""
    def name(self) -> Text:
        return "validate_payment_option"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        latest_message = tracker.latest_message.get("text", "") if tracker.latest_message else ""
        
        # CRITICAL: Check information_sufficient FIRST, before anything else
        information_sufficient = tracker.get_slot("information_sufficient")
        if information_sufficient == "asked":
            latest_lower = latest_message.lower().strip()
            # Check for yes/continue responses - be more flexible with combinations
            # First check for explicit yes words
            yes_words = ["yes", "yeah", "yep", "sure", "ok", "okay", "continue", "go ahead", "ja", "jep", "oké", "doorgaan", "proceed", "let's go", "lets go", "i dont need anymore", "i don't need anymore", "no more", "no more questions"]
            # Check if message contains any yes word
            if any(word in latest_lower for word in yes_words):
                dispatcher.utter_message(text="Great! Let's continue with your booking.")
                # CRITICAL: Clear payment_option slot to None to ensure Rasa knows we're still collecting it
                # This forces Rasa to stay in the flow and ask the question again
                dispatcher.utter_message(
                    text="Would you like to pay at the front desk or complete the payment online now?"
                )
                # Clear both slots: information_sufficient to exit the question loop, payment_option to restart collection
                return [SlotSet("information_sufficient", None), SlotSet("payment_option", None)]
            # Check for no/more questions responses
            elif any(word in latest_lower for word in ["no", "nope", "nee", "more", "else", "other", "another"]) and "no more" not in latest_lower and "don't need" not in latest_lower:
                dispatcher.utter_message(text="Of course! What else would you like to know?")
                return [SlotSet("information_sufficient", None)]
            # If information_sufficient is "asked" but user hasn't responded yes/no yet, wait
            # But if it's a very short message (1-2 words) that might be "yes", try to interpret it
            if len(latest_lower.split()) <= 2:
                # Very short response - likely "yes" or similar
                dispatcher.utter_message(text="Great! Let's continue with your booking.")
                # CRITICAL: Clear payment_option slot to None to ensure Rasa knows we're still collecting it
                # This forces Rasa to stay in the flow and ask the question again
                dispatcher.utter_message(
                    text="Would you like to pay at the front desk or complete the payment online now?"
                )
                # Clear both slots: information_sufficient to exit the question loop, payment_option to restart collection
                return [SlotSet("information_sufficient", None), SlotSet("payment_option", None)]
            return []

        is_question = _is_question(latest_message)

        # Check if it's a question
        if is_question:
            is_facility, facility_response = _is_facility_question(latest_message)
            if is_facility and facility_response:
                dispatcher.utter_message(text=facility_response)
                dispatcher.utter_message(
                    text="I hope I've provided you with sufficient information. Is there anything else you'd like to know, or shall we continue with your booking?"
                )
                # CRITICAL: Only set information_sufficient to "asked", keep slot as None
                # The validate action will check information_sufficient and not ask if it's "asked"
                return [SlotSet("information_sufficient", "asked")]
            # If it's a question but not a facility question, clear the slot
            return [SlotSet("payment_option", None)]

        payment_option = tracker.get_slot("payment_option")

        # CRITICAL: If slot is "waiting", it means we're waiting for user to say "continue"
        # Don't process it, just return empty list to wait
        # If payment_option is not set, ask for it (only if information_sufficient is NOT "asked")
        if not payment_option:
            dispatcher.utter_message(
                text="Would you like to pay at the front desk or complete the payment online now?"
            )
            return []

        payment_option_lower = str(payment_option).lower().strip()

        # Normalize payment option
        if any(word in payment_option_lower for word in ["desk", "front desk", "at desk", "reception", "counter"]):
            return [SlotSet("payment_option", "at_desk")]
        elif any(word in payment_option_lower for word in ["online", "now", "pay now", "card", "credit", "debit"]):
            return [SlotSet("payment_option", "online")]
        else:
            dispatcher.utter_message(
                text="I didn't understand that. Please choose either 'at the front desk' or 'online'."
            )
            return [SlotSet("payment_option", None)]


class ValidateGuests(Action):
    """Validate number of guests - automatically called by Rasa when guests slot is set."""
    def name(self) -> Text:
        return "validate_guests"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        latest_message = tracker.latest_message.get("text", "") if tracker.latest_message else ""

        # Check if user is responding to "is information sufficient" question
        information_sufficient = tracker.get_slot("information_sufficient")
        if information_sufficient == "asked":
            latest_lower = latest_message.lower().strip()
            yes_words = ["yes", "yeah", "yep", "sure", "ok", "okay", "continue", "go ahead", "ja", "jep", "oké", "doorgaan", "proceed", "let's go", "lets go", "i dont need anymore", "i don't need anymore", "no more", "no more questions"]
            if any(word in latest_lower for word in yes_words):
                dispatcher.utter_message(text="Great! Let's continue with your booking.")
                # CRITICAL: Ask for guests again - clear the slot to restart collection
                dispatcher.utter_message(text="For how many guests?")
                return [SlotSet("information_sufficient", None), SlotSet("guests", None)]
            elif any(word in latest_lower for word in ["no", "nope", "nee", "more", "else", "other", "another"]) and "no more" not in latest_lower and "don't need" not in latest_lower:
                dispatcher.utter_message(text="Of course! What else would you like to know?")
                return [SlotSet("information_sufficient", None)]
            # CRITICAL: If information_sufficient is "asked" but user hasn't responded yes/no yet, wait
            # Return empty list to prevent Rasa from automatically continuing
            return []

        # Check if the latest user message is a question (not an answer)
        is_question = _is_question(latest_message)

        if is_question:
            # Check if it's a facility question we can answer
            is_facility, facility_response = _is_facility_question(latest_message)
            if is_facility and facility_response:
                dispatcher.utter_message(text=facility_response)
                dispatcher.utter_message(
                    text="I hope I've provided you with sufficient information. Is there anything else you'd like to know, or shall we continue with your booking?"
                )
                # CRITICAL: Only set information_sufficient to "asked", keep slot as None
                # The validate action will check information_sufficient and prevent utter_ask_guests
                return [SlotSet("information_sufficient", "asked")]
            # If it's a question but not a facility question, clear the slot
            return [SlotSet("guests", None)]

        if not guests:
            # Only ask if information_sufficient is NOT "asked"
            if information_sufficient != "asked":
                dispatcher.utter_message(text="For how many guests?")
            return []
        
        is_valid, error_msg, parsed_value = _validate_positive_number(guests, "number of guests", allow_zero=False)
        
        if not is_valid:
            dispatcher.utter_message(
                text=(
                    f"{error_msg} "
                    "For example, you could say 'one guest', 'two guests', or just '1' or '2'."
                )
            )
            return [SlotSet("guests", None)]
        
        return [SlotSet("guests", str(int(parsed_value)))]


class ValidateNights(Action):
    """Validate number of nights - automatically called by Rasa when nights slot is set."""
    def name(self) -> Text:
        return "validate_nights"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        latest_message = tracker.latest_message.get("text", "") if tracker.latest_message else ""

        # Check if user is responding to "is information sufficient" question
        information_sufficient = tracker.get_slot("information_sufficient")
        if information_sufficient == "asked":
            latest_lower = latest_message.lower().strip()
            yes_words = ["yes", "yeah", "yep", "sure", "ok", "okay", "continue", "go ahead", "ja", "jep", "oké", "doorgaan", "proceed", "let's go", "lets go", "i dont need anymore", "i don't need anymore", "no more", "no more questions"]
            if any(word in latest_lower for word in yes_words):
                dispatcher.utter_message(text="Great! Let's continue with your booking.")
                # CRITICAL: Show calendar widget again for arrival_date - clear the slot to restart collection
                try:
                    today = datetime.now()
                    calendar_data = {
                        "type": "calendar",
                        "mode": "booking",
                        "message": "Please select your arrival and departure date",
                        "min_date": today.strftime("%Y-%m-%d"),
                        "arrival_date": None,
                        "departure_date": None,
                    }
                    dispatcher.utter_message(text="Please select your arrival and departure date:")
                    dispatcher.utter_message(text="", custom=json.dumps(calendar_data))
                except Exception as e:
                    dispatcher.utter_message(text="Please select your arrival and departure date:")
                return [SlotSet("information_sufficient", None), SlotSet("arrival_date", None)]
            elif any(word in latest_lower for word in ["no", "nope", "nee", "more", "else", "other", "another"]) and "no more" not in latest_lower and "don't need" not in latest_lower:
                dispatcher.utter_message(text="Of course! What else would you like to know?")
                return [SlotSet("information_sufficient", None)]

        # Check if the latest user message is a question (not an answer)
        is_question = _is_question(latest_message)

        if is_question:
            # Check if it's a facility question we can answer
            is_facility, facility_response = _is_facility_question(latest_message)
            if is_facility and facility_response:
                dispatcher.utter_message(text=facility_response)
                dispatcher.utter_message(
                    text="I hope I've provided you with sufficient information. Is there anything else you'd like to know, or shall we continue with your booking?"
                )
                return [SlotSet("nights", None), SlotSet("information_sufficient", "asked")]
            # If it's a question but not a facility question, clear the slot
            return [SlotSet("nights", None)]

        nights = tracker.get_slot("nights")
        
        if not nights:
            return []
        
        is_valid, error_msg, parsed_value = _validate_positive_number(nights, "number of nights", allow_zero=False)
        
        if not is_valid:
            dispatcher.utter_message(
                text=(
                    f"{error_msg} "
                    "For example, you could say 'one night', 'two nights', or just '1' or '2'."
                )
            )
            return [SlotSet("nights", None)]
        
        return [SlotSet("nights", str(int(parsed_value)))]


class ValidateRooms(Action):
    """Validate number of rooms - automatically called by Rasa when rooms slot is set."""
    def name(self) -> Text:
        return "validate_rooms"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        latest_message = tracker.latest_message.get("text", "") if tracker.latest_message else ""

        # Check if user is responding to "is information sufficient" question
        information_sufficient = tracker.get_slot("information_sufficient")
        if information_sufficient == "asked":
            latest_lower = latest_message.lower().strip()
            yes_words = ["yes", "yeah", "yep", "sure", "ok", "okay", "continue", "go ahead", "ja", "jep", "oké", "doorgaan", "proceed", "let's go", "lets go", "i dont need anymore", "i don't need anymore", "no more", "no more questions"]
            if any(word in latest_lower for word in yes_words):
                dispatcher.utter_message(text="Great! Let's continue with your booking.")
                # CRITICAL: Show calendar widget again for arrival_date - clear the slot to restart collection
                try:
                    today = datetime.now()
                    calendar_data = {
                        "type": "calendar",
                        "mode": "booking",
                        "message": "Please select your arrival and departure date",
                        "min_date": today.strftime("%Y-%m-%d"),
                        "arrival_date": None,
                        "departure_date": None,
                    }
                    dispatcher.utter_message(text="Please select your arrival and departure date:")
                    dispatcher.utter_message(text="", custom=json.dumps(calendar_data))
                except Exception as e:
                    dispatcher.utter_message(text="Please select your arrival and departure date:")
                return [SlotSet("information_sufficient", None), SlotSet("arrival_date", None)]
            elif any(word in latest_lower for word in ["no", "nope", "nee", "more", "else", "other", "another"]) and "no more" not in latest_lower and "don't need" not in latest_lower:
                dispatcher.utter_message(text="Of course! What else would you like to know?")
                return [SlotSet("information_sufficient", None)]

        # Check if the latest user message is a question (not an answer)
        is_question = _is_question(latest_message)

        if is_question:
            # Check if it's a facility question we can answer
            is_facility, facility_response = _is_facility_question(latest_message)
            if is_facility and facility_response:
                dispatcher.utter_message(text=facility_response)
                dispatcher.utter_message(
                    text="I hope I've provided you with sufficient information. Is there anything else you'd like to know, or shall we continue with your booking?"
                )
                return [SlotSet("rooms", None), SlotSet("information_sufficient", "asked")]
            # If it's a question but not a facility question, clear the slot
            return [SlotSet("rooms", None)]

        rooms = tracker.get_slot("rooms")
        
        if not rooms:
            return []
        
        is_valid, error_msg, parsed_value = _validate_positive_number(rooms, "number of rooms", allow_zero=False)
        
        if not is_valid:
            dispatcher.utter_message(
                text=(
                    f"{error_msg} "
                    "For example, you could say 'one room', 'two rooms', or just '1' or '2'."
                )
            )
            return [SlotSet("rooms", None)]
        
        return [SlotSet("rooms", str(int(parsed_value)))]
