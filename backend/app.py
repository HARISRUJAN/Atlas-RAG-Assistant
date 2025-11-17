"""Main Flask application."""

from flask import Flask
from flask_cors import CORS

from backend.config import Config
from backend.routes import upload_bp, query_bp, health_bp, collections_bp, config_bp, connections_bp


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173", 
                "http://localhost:5174", 
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174",
                "http://localhost:3000"
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-MongoDB-URI", "X-Connection-ID"],
            "supports_credentials": True
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
    app.register_blueprint(collections_bp, url_prefix='/api')
    app.register_blueprint(config_bp, url_prefix='/api')
    app.register_blueprint(connections_bp, url_prefix='/api')
    
    # Root endpoint
    @app.route('/')
    def index():
        return {
            'message': 'MongoDB RAG System API',
            'version': '1.0.0',
            'endpoints': {
                'upload': '/api/upload',
                'query': '/api/query',
                'health': '/api/health',
                'collections': '/api/collections',
                'collection_questions': '/api/collections/<name>/questions',
                'connections': '/api/connections',
                'config': '/api/config/mongodb-uri'
            }
        }
    
    # API info endpoint
    @app.route('/api', methods=['GET'])
    def api_info():
        """API information endpoint."""
        from flask import jsonify
        return jsonify({
            'message': 'MongoDB RAG System API',
            'version': '1.0.0',
            'endpoints': {
                'upload': 'POST /api/upload',
                'query': 'POST /api/query',
                'health': 'GET /api/health',
                'collections': 'GET /api/collections',
                'collection_questions': 'GET /api/collections/<name>/questions',
                'connections': {
                    'list': 'GET /api/connections',
                    'create': 'POST /api/connections',
                    'get': 'GET /api/connections/<id>',
                    'test': 'POST /api/connections/<id>/test',
                    'consent': 'POST /api/connections/<id>/consent',
                    'delete': 'DELETE /api/connections/<id>',
                    'collections': 'GET /api/connections/<id>/collections'
                },
                'config': 'GET /api/config/mongodb-uri'
            }
        }), 200
    
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

