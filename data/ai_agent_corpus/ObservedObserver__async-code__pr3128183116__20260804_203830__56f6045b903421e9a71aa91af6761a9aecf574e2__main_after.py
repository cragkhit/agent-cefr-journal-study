from flask import Flask, jsonify
from flask_cors import CORS
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import blueprints
from tasks import tasks_bp
from projects import projects_bp
from health import health_bp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS
CORS(app, origins=['http://localhost:3000', 'https://*.vercel.app'])

# Register blueprints
app.register_blueprint(health_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(projects_bp)

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Flask server on port {port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
