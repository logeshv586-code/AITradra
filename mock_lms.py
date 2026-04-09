from flask import Flask, request, jsonify
import threading
import time

app = Flask(__name__)

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.json
    print(f"Mock received: {data}")
    return jsonify({
        "choices": [{
            "message": {
                "content": '{"sentiment_score": 0.8, "label": "positive", "confidence": 0.9, "reasoning": "Mock success"}'
            }
        }]
    })

def run_server():
    app.run(port=1234)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    print("Mock LM Studio server running on port 1234...")
    time.sleep(10) # Keep alive for testing
