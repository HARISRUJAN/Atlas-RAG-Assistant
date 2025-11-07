"""Main Flask application."""

from flask import Flask
from flask_cors import CORS

from backend.config import Config
from backend.routes import upload_bp, query_bp, health_bp


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:5173", "http://localhost:3000"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please check your .env file")
        exit(1)
    
    # Register blueprints
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(query_bp, url_prefix='/api')
    app.register_blueprint(health_bp, url_prefix='/api')
    
    # Root endpoint
    @app.route('/')
    def index():
        return {
            'message': 'MongoDB RAG System API',
            'version': '1.0.0',
            'endpoints': {
                'upload': '/api/upload',
                'query': '/api/query',
                'health': '/api/health'
            }
        }
    
    return app


if __name__ == '__main__':
    app = create_app()
    print(f"Starting Flask server on port {Config.FLASK_PORT}...")
    print(f"API available at: http://localhost:{Config.FLASK_PORT}/api")
    app.run(
        host='0.0.0.0',
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )

