from typing import Any, Dict, List, Text
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher


class ActionAskGuests(Action):
    """Custom action to ask for guests, but only if information_sufficient is not 'asked'.
    Also handles 'continue' responses when information_sufficient == 'asked'."""
    
    def name(self) -> Text:
        return "action_ask_guests"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        # Check if information_sufficient is "asked" or "continue_detected"
        information_sufficient = tracker.get_slot("information_sufficient")
        
        # If information_sufficient is being handled by validate_information_sufficient,
        # don't do anything here to avoid duplicate messages
        if information_sufficient in ["asked", "continue_detected", "more_info_needed"]:
            # Let validate_information_sufficient handle this
            return []
        
        # Only ask for guests if information_sufficient is NOT being handled
        dispatcher.utter_message(text="For how many guests?")
        return []





