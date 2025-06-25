import os
import sys
import logging
import time
import threading
from flask import Flask, render_template, request, jsonify, session, Response, send_from_directory
from scraper import scrape_character_data, enhance_character_data
from model_handler import RoleplayModel
from emotion_detector import EmotionDetector
from prompts import create_character_prompt
import requests

# Get the absolute path to the current directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'

# Build absolute path to models
MODEL_PATH = os.path.join(BASE_DIR, "models", "pygmalion-2-7b")

# Model status monitoring
model_status = {
    "loaded": False,
    "loading": False,
    "last_inference_time": None,
    "inference_count": 0,
    "error": None
}

# Initialize models in background thread
def init_models():
    global model, emotion_detector, model_status
    try:
        model_status["loading"] = True
        model = RoleplayModel(MODEL_PATH)
        emotion_detector = EmotionDetector()
        model_status["loaded"] = True
        logger.info("Models loaded successfully")
    except Exception as e:
        logger.error(f"Failed to initialize models: {e}")
        model_status["error"] = str(e)
    finally:
        model_status["loading"] = False

# Start model loading in background
model_loader = threading.Thread(target=init_models)
model_loader.daemon = True
model_loader.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory(os.path.join(BASE_DIR, 'static'), path)

@app.route('/set_character', methods=['POST'])
def set_character():
    wiki_url = request.form['wiki_url']
    try:
        character_data = scrape_character_data(wiki_url)
        enhanced_data = enhance_character_data(character_data)
        session['character'] = enhanced_data
        session['chat_history'] = []
        session['character_name'] = enhanced_data.get('name', 'Character')
        return jsonify(
            success=True, 
            name=enhanced_data.get('name', 'Character'),
            image_url=enhanced_data.get('image_url', ''),
            speech_style=enhanced_data.get('speech_style', '')
        )
    except Exception as e:
        logger.error(f"Error setting character: {e}")
        return jsonify(success=False, error=str(e)), 400

@app.route('/chat', methods=['POST'])
def chat():
    if not model_status["loaded"]:
        return jsonify(response="AI model still loading", error=True)
    
    user_input = request.form['message']
    character = session.get('character', {})
    history = session.get('chat_history', [])
    
    # Detect emotion
    emotion = emotion_detector.detect_emotion(user_input) if emotion_detector else "neutral"
    
    # Format conversation history
    history_text = "\n".join(
        [f"User: {msg['user']}\n{character.get('name', 'Character')}: {msg['bot']}" 
         for msg in history[-10:]]
    )
    
    # Generate prompt
    prompt = create_character_prompt(character, user_input, emotion, history_text)
    
    # Update status
    model_status["last_inference_time"] = time.time()
    
    # Get AI response
    try:
        # For streaming
        if request.headers.get('Accept') == 'text/event-stream':
            def generate():
                full_response = ""
                start_time = time.time()
                for token in model.stream_response(prompt):
                    full_response += token
                    yield f"data: {token}\n\n"
                # Update history after completion
                history.append({'user': user_input, 'bot': full_response})
                session['chat_history'] = history[-15:]
                model_status["inference_count"] += 1
                model_status["last_inference_duration"] = time.time() - start_time
            return Response(generate(), mimetype='text/event-stream')
        
        # For regular response
        start_time = time.time()
        full_response = model.generate_response(prompt)
        history.append({'user': user_input, 'bot': full_response})
        session['chat_history'] = history[-15:]
        model_status["inference_count"] += 1
        model_status["last_inference_duration"] = time.time() - start_time
        return jsonify(response=full_response)
    
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return jsonify(response="I encountered an error. Please try again.", error=True)

@app.route('/clear_history', methods=['POST'])
def clear_history():
    session['chat_history'] = []
    return jsonify(success=True)

@app.route('/status')
def status():
    return jsonify({
        "model_loaded": model_status["loaded"],
        "model_loading": model_status["loading"],
        "last_inference_time": model_status.get("last_inference_time"),
        "inference_count": model_status["inference_count"],
        "last_inference_duration": model_status.get("last_inference_duration"),
        "error": model_status.get("error")
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)