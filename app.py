import json
import os
import requests
import logging
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from requests.exceptions import RequestException, Timeout, ConnectionError

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='frontend')

CORS(app, resources={r"/*": {"origins": "*"}})

# Default Rasa server URL
DEFAULT_RASA_URL = 'http://localhost:5005/webhooks/rest/webhook'

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

    try:
        for item in response:
            if item.get("text"):
                result["messages"].append({"text": item["text"]})
                
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"Chatbot server running on http://localhost:{port}")
    logger.info("To use with Rasa, make sure to start the Rasa server with:")
    logger.info("  - rasa run --enable-api --cors \"*\"")
    app.run(debug=True, port=port, host='0.0.0.0')
