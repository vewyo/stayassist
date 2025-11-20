import random
import re
import string
from typing import Any, Dict, List, Optional, Text

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
