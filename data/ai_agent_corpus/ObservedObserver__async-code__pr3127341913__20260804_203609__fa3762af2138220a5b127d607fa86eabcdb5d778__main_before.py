from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint"""
    return jsonify({
        'status': 'success',
        'message': 'pong',
        'timestamp': None
    })

@app.route('/', methods=['GET'])
def home():
    """Root endpoint"""
    return jsonify({
        'status': 'success',
        'message': 'Flask app is running',
        'endpoints': ['/ping']
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
