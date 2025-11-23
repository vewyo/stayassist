import random
import re
import string
from datetime import datetime
from typing import Any, Dict, List, Optional, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, ActiveLoop
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
            # Clear the slot and reactivate the loop to ask again
            return [SlotSet("arrival_date", None), ActiveLoop("book_room")]
        
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
            return [SlotSet("nights", None), ActiveLoop("book_room")]
        
        is_valid, error_msg, parsed_value = _validate_positive_number(nights, "number of nights", allow_zero=False)
        
        if not is_valid:
            dispatcher.utter_message(
                text=(
                    f"{error_msg} "
                    "For example, you could say 'one night', 'two nights', or just '1' or '2'."
                )
            )
            return [SlotSet("nights", None), ActiveLoop("book_room")]
        
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
            return [SlotSet("rooms", None), ActiveLoop("book_room")]
        
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
        
        if not guests:
            return []
        
        is_valid, error_msg, parsed_value = _validate_positive_number(guests, "number of guests", allow_zero=False)
        
        if not is_valid:
            dispatcher.utter_message(
                text=(
                    f"{error_msg} "
                    "For example, you could say 'one guest', 'two guests', or just '1' or '2'."
                )
            )
            return [SlotSet("guests", None), ActiveLoop("book_room")]
        
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
