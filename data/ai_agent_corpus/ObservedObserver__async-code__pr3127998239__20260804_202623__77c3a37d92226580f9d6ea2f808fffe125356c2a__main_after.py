from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Import blueprints
from health import health_bp
from tasks import tasks_bp
from git_operations import git_bp
from github_integration import github_bp

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Register blueprints
app.register_blueprint(health_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(git_bp)
app.register_blueprint(github_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
