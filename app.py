import json
import os
import re
import requests
import logging
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from requests.exceptions import RequestException, Timeout, ConnectionError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='frontend')

CORS(app, resources={r"/*": {"origins": "*"}})

# Default Rasa server URL
DEFAULT_RASA_URL = 'http://localhost:5005/webhooks/rest/webhook'

# Security: Check if message is hotel-related
def is_hotel_related(message):
    """
    Check if a message is hotel-related. Returns True if hotel-related, False otherwise.
    """
    if not message:
        return False
    
    message_lower = message.lower().strip()
    
    # Hotel-related keywords
    hotel_keywords = [
        # Booking related
        'book', 'booking', 'reserve', 'reservation', 'room', 'rooms', 'suite', 'standard',
        'guest', 'guests', 'stay', 'staying', 'check-in', 'check-in', 'checkout', 'check-out',
        # Payment related
        'pay', 'payment', 'online', 'desk', 'front desk', 'card', 'credit', 'debit',
        # Dates
        'arrival', 'departure', 'date', 'dates', 'night', 'nights', 'day', 'days',
        # Facilities
        'pool', 'parking', 'breakfast', 'lunch', 'dinner', 'gym', 'facility', 'facilities',
        'amenity', 'amenities', 'wifi', 'internet', 'elevator', 'lift', 'wheelchair',
        # Hotel services
        'cancel', 'cancellation', 'booking number', 'reference', 'hotel', 'stayassist',
        # Questions about hotel
        'price', 'cost', 'fee', 'fees', 'available', 'availability', 'open', 'hours',
        'time', 'times', 'when', 'what', 'which', 'how much', 'how many',
        # Greetings (allowed)
        'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings',
        # Continuation (allowed during booking)
        'continue', 'yes', 'ok', 'okay', 'proceed', 'go ahead', 'sure', 'yeah', 'yep',
        # Personal details (during booking)
        'name', 'first name', 'last name', 'email', 'address',
        # Numbers (likely booking related)
        'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
        '1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
    ]
    
    # Check if message contains hotel-related keywords
    if any(keyword in message_lower for keyword in hotel_keywords):
        return True
    
    # Blocked content patterns
    blocked_patterns = [
        # Programming
        'code', 'programming', 'python', 'javascript', 'function', 'variable', 'debug', 'error',
        'script', 'algorithm', 'api', 'json', 'html', 'css', 'sql', 'database',
        # Personal questions about bot
        'what are you', 'who are you', 'what is your', 'tell me about yourself',
        'what model', 'which model', 'what ai', 'what llm', 'what system',
        'how are you built', 'how do you work', 'what are your rules',
        # Discussions
        'discuss', 'debate', 'opinion', 'think about', 'what do you think',
        # Jokes
        'joke', 'funny', 'humor', 'laugh',
        # Insults
        'stupid', 'idiot', 'dumb', 'useless', 'bad', 'terrible', 'hate',
        # Threats
        'threat', 'harm', 'hurt', 'kill', 'destroy',
        # Test questions
        'test', 'testing', 'debug', 'trial',
        # Prompt injection
        'ignore', 'forget', 'disregard', 'override', 'change your', 'pretend you are',
        'act as', 'roleplay', 'role play', 'imagine', 'suppose', 'assume',
        'reveal', 'show me your', 'what are your instructions', 'what are your rules',
        'system prompt', 'initial prompt',
    ]
    
    # Check if message contains blocked patterns
    if any(pattern in message_lower for pattern in blocked_patterns):
        return False
    
    # Allow greetings (always allowed)
    greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings', 'greet']
    if any(greeting in message_lower for greeting in greeting_words):
        return True
    
    # Allow short responses that are likely booking-related
    if len(message_lower.split()) <= 2:
        # Allow if it's a number, common booking response, or continuation word
        allowed_short = ['yes', 'ok', 'okay', 'no', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
                        'standard', 'suite', 'online', 'desk', 'continue', 'proceed', 'go ahead', 'sure']
        if message_lower in allowed_short:
            return True
    
    # If message contains blocked patterns, definitely block
    # This check happens after allowing greetings and short responses
    if any(pattern in message_lower for pattern in blocked_patterns):
        return False
    
    # If no hotel keywords found and not clearly blocked, check if it's a simple question/statement
    # Allow if it's a very short message that might be a booking response
    # Otherwise, default to allowing (let Rasa/LLM handle it with the security prompt)
    # The LLM prompt will catch anything that slips through
    return True

# Serve frontend files
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/check_rasa', methods=['GET'])
def check_rasa():
    rasa_url = os.environ.get('RASA_URL', 'http://localhost:5005')
    try:
        # Try to connect to the server's health endpoint
        response = requests.get(f"{rasa_url}/version", timeout=3)
        if response.ok:
            return jsonify({"status": "available", "version": response.json()})
        else:
            return jsonify({"status": "unavailable", "reason": "API responded with error"}), 503
    except RequestException as e:
        logger.error(f"Failed to connect to Rasa server: {str(e)}")
        return jsonify({"status": "unavailable", "reason": str(e)}), 503


# Handle Rasa messages
@app.route('/api/send_message', methods=['POST'])
def send_message():
    data = request.json
    message = data.get('message')
    context = data.get('context', {})
    
    logger.info(f"🔵 Received message: '{message}', context sender_id: {context.get('sender_id', 'user')}")
    
    # SECURITY: Check if message is hotel-related
    if message and not is_hotel_related(message):
        logger.warning(f"🚫 SECURITY BLOCK: Non-hotel related message blocked: '{message}'")
        return jsonify({
            "messages": [{"text": "I can only help with hotel related matters."}],
            "context": context,
            "actions": []
        })
    
    # CRITICAL: Handle "continue" response when information_sufficient == "asked"
    # This MUST happen BEFORE calling Rasa to prevent fallback from being triggered
    continue_words = ["continue", "yes", "ok", "okay", "proceed", "go ahead", "let's go", "lets go", "sure", "yeah", "yep", "ja", "jep", "oké", "doorgaan", "i dont need anymore", "i don't need anymore", "no more", "no more questions"]
    is_continue_message = message and any(word in message.lower().strip() for word in continue_words)
    logger.info(f"🔵 Is continue message? {is_continue_message}, message: '{message}'")
    
    if is_continue_message:
        # Get current conversation state from Rasa
        sender_id = context.get('sender_id', 'user')
        logger.info(f"🔵 Checking tracker for sender_id: {sender_id}")
        
        try:
            # Make a request to get current tracker state
            tracker_url = f"{os.environ.get('RASA_URL', DEFAULT_RASA_URL).rstrip('/')}/conversations/{sender_id}/tracker"
            logger.info(f"🔵 Fetching tracker from: {tracker_url}")
            tracker_response = requests.get(tracker_url, timeout=5)
            logger.info(f"🔵 Tracker response status: {tracker_response.status_code}")
            
            if tracker_response.status_code == 200:
                tracker_data = tracker_response.json()
                slots = tracker_data.get('slots', {})
                information_sufficient = slots.get('information_sufficient')
                logger.info(f"🔵 CRITICAL CHECK: message='{message}', information_sufficient={information_sufficient}, all slots: {slots}")
                
                if information_sufficient == "asked":
                    logger.info(f"✅✅✅ Detected 'continue' when information_sufficient == 'asked', responding directly WITHOUT calling Rasa")
                    # Determine which slot is currently being collected
                    guests = slots.get('guests')
                    room_type = slots.get('room_type')
                    arrival_date = slots.get('arrival_date')
                    departure_date = slots.get('departure_date')
                    payment_option = slots.get('payment_option')
                    
                    logger.info(f"🔵 Current slots: guests={guests}, room_type={room_type}, arrival_date={arrival_date}, departure_date={departure_date}, payment_option={payment_option}")
                    
                    # Respond directly without going through Rasa to avoid fallback
                    messages = [{"text": "Great! Let's continue with your booking."}]
                    
                    if not guests:
                        messages.append({"text": "For how many guests?"})
                    elif not room_type:
                        messages.append({"text": "Which room would you like? (standard or suite)"})
                    elif not arrival_date:
                        messages.append({"text": "Please select your arrival and departure date:"})
                    elif not departure_date:
                        messages.append({"text": "Please select your departure date:"})
                    elif not payment_option:
                        messages.append({"text": "Would you like to pay at the front desk or complete the payment online now?"})
                    
                    # Update slots in Rasa tracker for consistency
                    events_url = f"{os.environ.get('RASA_URL', DEFAULT_RASA_URL).rstrip('/')}/conversations/{sender_id}/tracker/events"
                    slot_events = [
                        {"event": "slot", "name": "information_sufficient", "value": None}
                    ]
                    # Also clear the slot that we're asking for
                    if not guests:
                        slot_events.append({"event": "slot", "name": "guests", "value": None})
                    elif not room_type:
                        slot_events.append({"event": "slot", "name": "room_type", "value": None})
                    elif not arrival_date:
                        slot_events.append({"event": "slot", "name": "arrival_date", "value": None})
                    elif not departure_date:
                        slot_events.append({"event": "slot", "name": "departure_date", "value": None})
                    elif not payment_option:
                        slot_events.append({"event": "slot", "name": "payment_option", "value": None})
                    
                    try:
                        for event in slot_events:
                            requests.post(events_url, json=event, timeout=5)
                        logger.info(f"🔵 Updated slots in Rasa tracker")
                    except Exception as e:
                        logger.warning(f"Could not update slots in Rasa: {e}")
                    
                    # Update context
                    if 'slots' not in context:
                        context['slots'] = {}
                    context['slots']['information_sufficient'] = None
                    
                    # Return response directly without calling Rasa - THIS PREVENTS FALLBACK
                    logger.info(f"✅✅✅ Returning direct response for 'continue': {messages}")
                    return jsonify({
                        "messages": messages,
                        "context": context,
                        "actions": []
                    })
                else:
                    logger.info(f"🔵 information_sufficient is '{information_sufficient}', not 'asked', will proceed with normal Rasa flow")
            else:
                logger.warning(f"🔵 Tracker response not 200: {tracker_response.status_code}, {tracker_response.text}")
        except Exception as e:
            logger.error(f"🔵 ERROR checking tracker state: {e}", exc_info=True)
    
    # Store last message in context for fallback filtering (only if we didn't return early)
    if message:
        context['last_message'] = message
    
    # Reset booking slots when starting a new booking
    booking_phrases = ["book a room", "book room", "i want to book", "reserve a room", "make a reservation", "reserve", "booking"]
    if message and any(phrase in message.lower() for phrase in booking_phrases):
        logger.info("Detected new booking request, resetting booking slots")
        # Clear booking-related slots in context
        if 'slots' not in context:
            context['slots'] = {}
        # Reset booking slots - explicitly set to None to clear them
        context['slots']['guests'] = None
        context['slots']['room_type'] = None
        context['slots']['arrival_date'] = None
        context['slots']['departure_date'] = None
        context['slots']['nights'] = None
        context['slots']['rooms'] = None
        context['slots']['payment_option'] = None
        logger.info(f"Reset booking slots: {context['slots']}")

    rasa_url = os.environ.get('RASA_URL', DEFAULT_RASA_URL)
    
    # Use a unique sender ID for each new booking to ensure slots are reset
    sender_id = context.get('sender_id', 'user')
    if message and any(phrase in message.lower() for phrase in booking_phrases):
        # Generate a new sender ID for this booking to ensure a fresh conversation
        import uuid
        sender_id = f"user_{uuid.uuid4().hex[:8]}"
        context['sender_id'] = sender_id
        logger.info(f"Generated new sender ID for booking: {sender_id}")
    
    payload = {
        "sender": sender_id,
        "message": message,
        "metadata": context
    }

    try:
        response = requests.post(rasa_url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Raw Rasa response: {json.dumps(data, indent=2)}")
        
        # Update context with last message for fallback filtering
        if message:
            context['last_message'] = message
            # Also get current slots from Rasa to check information_sufficient
            sender_id = context.get('sender_id', 'user')
            try:
                tracker_url = f"{os.environ.get('RASA_URL', DEFAULT_RASA_URL).rstrip('/')}/conversations/{sender_id}/tracker"
                tracker_response = requests.get(tracker_url, timeout=5)
                if tracker_response.status_code == 200:
                    tracker_data = tracker_response.json()
                    slots = tracker_data.get('slots', {})
                    if 'slots' not in context:
                        context['slots'] = {}
                    context['slots']['information_sufficient'] = slots.get('information_sufficient')
                    logger.info(f"Retrieved information_sufficient from tracker: {slots.get('information_sufficient')}")
            except Exception as e:
                logger.warning(f"Could not get tracker state: {e}")
        
        processed = process_rasa_response(data, context)
        logger.info(f"Processed response: {json.dumps(processed, indent=2)}")
        return jsonify(processed)
    except RequestException as e:
        error_message = f"Error communicating with Rasa server: {str(e)}"
        logger.error(error_message)
        return jsonify({
            "error": error_message,
            "context": context,
            "messages": [{"text": "I'm sorry, I encountered an error processing your request. Please try again later."}]
        }), 500
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logger.error(error_message, exc_info=True)
        return jsonify({
            "error": error_message,
            "context": context,
            "messages": [{"text": "I apologize, but I encountered an issue processing your request. Please try again."}]
        }), 500


def process_rasa_response(response, original_context):
    result = {
        "messages": [],
        "context": {**original_context},
        "actions": []
    }

    logger.info(f"Processing Rasa response: {json.dumps(response, indent=2)}")

    if not response or len(response) == 0:
        # Don't add error message if this is a date confirmation (user already saw the confirmation)
        # Just return empty result - the frontend will handle it gracefully
        logger.warning("Empty response from Rasa, but this might be expected for date confirmations")
        return result

    # CRITICAL: Check if user said "continue" - if so, ALWAYS filter fallback
    last_message = original_context.get('last_message', '').lower().strip() if original_context.get('last_message') else ''
    continue_words = ["continue", "yes", "ok", "okay", "proceed", "go ahead", "let's go", "lets go", "sure", "yeah", "yep", "ja", "jep", "oké", "doorgaan"]
    # Use word boundaries to match whole words only, not substrings (prevents "book room" from matching "go" in "go ahead")
    is_continue = any(re.search(r'\b' + re.escape(word) + r'\b', last_message) for word in continue_words) if last_message else False
    
    # Get information_sufficient from context
    information_sufficient = original_context.get('slots', {}).get('information_sufficient') if original_context.get('slots') else None
    
    # Check if response contains the info question
    response_text = ' '.join([item.get("text", "") for item in response if item.get("text")])
    has_info_question = "i hope i've provided you with sufficient information" in response_text.lower()
    
    logger.info(f"🚨 FALLBACK FILTERING: last_message='{last_message}', is_continue={is_continue}, information_sufficient={information_sufficient}, has_info_question={has_info_question}")
    
    # Filter out fallback messages - ALWAYS filter if user said "continue"
    fallback_phrases = [
        "i'm sorry i am unable to understand you",
        "could you please rephrase",
        "i'm sorry",
        "unable to understand",
        "please rephrase",
        "utter_ask_rephrase"
    ]
    
    # Track seen messages to prevent duplicates
    seen_messages = set()

    try:
        for item in response:
            text = item.get("text", "")
            if text:
                text_lower = text.lower()
                text_normalized = text.strip().lower()
                
                # ALWAYS filter "placeholder" messages - these are internal Rasa messages
                # Check both exact match and if it contains "placeholder"
                if text_normalized == "placeholder" or "placeholder" in text_normalized:
                    logger.info(f"🚫 FILTERING PLACEHOLDER: {text}")
                    continue
                
                # ALWAYS filter fallback if user said "continue"
                is_fallback = any(phrase in text_lower for phrase in fallback_phrases)
                if is_fallback and is_continue:
                    logger.info(f"🚫 ALWAYS FILTERING FALLBACK (user said continue): {text}")
                    continue
                
                # Also filter fallback if information_sufficient == "asked"
                if is_fallback and information_sufficient == "asked":
                    logger.info(f"🚫 FILTERING FALLBACK (information_sufficient == asked): {text}")
                    continue
                
                # Filter "What else can I help you with?" after booking summaries
                if "what else can i help" in text_lower or "how can i assist" in text_lower:
                    # Check if previous messages contain booking summary indicators
                    previous_messages = ' '.join([msg.get("text", "") for msg in result["messages"]])
                    if "booking reference" in previous_messages.lower() or "booking summary" in previous_messages.lower():
                        logger.info(f"🚫 FILTERING 'What else can I help' after booking summary: {text}")
                        continue
                
                # Filter duplicate messages (exact match)
                if text_normalized in seen_messages:
                    logger.info(f"🚫 FILTERING DUPLICATE: {text}")
                    continue
                
                # Check for duplicate "For how many guests?" BEFORE adding to seen_messages
                # This prevents the first one from being filtered
                if "for how many guests" in text_lower:
                    # Check if we already have this message in the result (not just seen_messages)
                    if any("for how many guests" in msg.get("text", "").lower() for msg in result["messages"]):
                        logger.info(f"🚫 FILTERING DUPLICATE 'For how many guests?': {text}")
                        continue
                
                # Add to seen_messages AFTER all checks
                seen_messages.add(text_normalized)
            
            if text:
                result["messages"].append({"text": text})
            
            # Check for json_message format which is used by newer Rasa SDK
            if item.get("json_message"):
                json_data = item["json_message"]
                
                # Extract action information
                if json_data.get("action"):
                    action = json_data["action"]
                    result["actions"].append(action)
                
                    # Handle calendar widget
                    if json_data.get("type") == "calendar":
                        result["messages"].append({
                            "text": json_data.get("message", "Please select your arrival date:"),
                            "json_message": json_data
                        })
                    
                # Update context with any new information
                if json_data.get("context"):
                    result["context"].update(json_data["context"])
                    
                # Continue processing other parts of the message
                continue

            # Handle legacy custom format
            if item.get("custom"):
                custom_data = item["custom"]
                if isinstance(custom_data, str):
                    try:
                        custom_data = json.loads(custom_data)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to decode custom JSON: {custom_data}")
                        continue

                    # Handle calendar widget
                    if custom_data.get("type") == "calendar":
                        logger.info(f"Found calendar widget in custom data: {custom_data}")
                        # Only add text message if it's not empty and not a duplicate
                        text = item.get("text", "")
                        if text and text.strip() and text.strip() != custom_data.get("message", ""):
                            result["messages"].append({
                                "text": text,
                                "json_message": custom_data
                            })
                        else:
                            # Just add the calendar widget without text (or with empty text)
                            result["messages"].append({
                                "text": "",
                                "json_message": custom_data
                            })

                if custom_data.get("action"):
                    result["actions"].append(custom_data["action"])
                    
                if custom_data.get("context"):
                    result["context"].update(custom_data["context"])

            if item.get("image"):
                result["messages"].append({"type": "image", "url": item["image"]})

            if item.get("buttons"):
                last_message = result["messages"][-1] if result["messages"] else {
                    "text": ""}
                last_message["buttons"] = item["buttons"]
                if not result["messages"] or result["messages"][-1] != last_message:
                    result["messages"].append(last_message)
    except Exception as e:
        logger.error(f"Error processing Rasa response item: {e}", exc_info=True)
        result["messages"].append({
            "text": "I apologize, but I encountered an issue processing your request. Please try again."
        })

    logger.info(f"Processed result: {json.dumps(result, indent=2)}")
    return result

@app.route('/api/text-to-speech', methods=['POST'])
def text_to_speech():
    """
    Convert text to speech using ElevenLabs API (or fallback to browser TTS).
    Returns audio data or instructions for browser TTS.
    """
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Clean text of HTML tags
        import re
        clean_text = re.sub(r'<[^>]*>?', '', text)
        
        # Get ElevenLabs API key from environment variable
        elevenlabs_api_key = os.environ.get('ELEVENLABS_API_KEY')
        elevenlabs_voice_id = os.environ.get('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')  # Default: natural female voice "Rachel"
        
        if elevenlabs_api_key:
            # Use ElevenLabs API for natural voice
            try:
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{elevenlabs_voice_id}"
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": elevenlabs_api_key
                }
                data = {
                    "text": clean_text,
                    "model_id": "eleven_multilingual_v2",  # Natural, multilingual model
                    "voice_settings": {
                        "stability": 0.4,      # Lower for more natural variation (0.0-1.0)
                        "similarity_boost": 0.8,  # Higher for more voice similarity (0.0-1.0)
                        "style": 0.2,          # Slight style for more natural expression (0.0-1.0)
                        "use_speaker_boost": True  # Enhanced clarity and naturalness
                    }
                }
                
                response = requests.post(url, json=data, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    # Return audio data as base64
                    import base64
                    audio_base64 = base64.b64encode(response.content).decode('utf-8')
                    return jsonify({
                        'audio': audio_base64,
                        'format': 'mp3',
                        'provider': 'elevenlabs'
                    })
                else:
                    logger.warning(f"ElevenLabs API error: {response.status_code} - {response.text}")
                    # Fallback to browser TTS
                    return jsonify({
                        'text': clean_text,
                        'provider': 'browser',
                        'fallback': True
                    })
            except Exception as e:
                logger.error(f"ElevenLabs API error: {e}")
                # Fallback to browser TTS
                return jsonify({
                    'text': clean_text,
                    'provider': 'browser',
                    'fallback': True
                })
        else:
            # No API key, use browser TTS
            return jsonify({
                'text': clean_text,
                'provider': 'browser',
                'fallback': True
            })
            
    except Exception as e:
        logger.error(f"Error in text-to-speech: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"Chatbot server running on http://localhost:{port}")
    logger.info("To use with Rasa, make sure to start the Rasa server with:")
    logger.info("  - rasa run --enable-api --cors \"*\"")
    logger.info("To use ElevenLabs for natural voices, set ELEVENLABS_API_KEY environment variable")
    app.run(debug=True, port=port, host='0.0.0.0')
