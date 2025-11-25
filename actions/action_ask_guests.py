from typing import Any, Dict, List, Text
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher


class ActionAskGuests(Action):
    """Custom action to ask for guests, but only if information_sufficient is not 'asked'."""
    
    def name(self) -> Text:
        return "action_ask_guests"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        # Check if information_sufficient is "asked"
        information_sufficient = tracker.get_slot("information_sufficient")
        
        # Only ask for guests if information_sufficient is NOT "asked"
        if information_sufficient != "asked":
            dispatcher.utter_message(text="For how many guests?")
        
        return []


