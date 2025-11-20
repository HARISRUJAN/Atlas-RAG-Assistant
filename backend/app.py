"""Main Flask application."""

from flask import Flask
from flask_cors import CORS

from backend.config import Config
from backend.routes import upload_bp, query_bp, health_bp, collections_bp, config_bp, connections_bp
from backend.routes.ingestion import ingestion_bp
from backend.routes.origin import origin_bp


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173", 
                "http://localhost:5174",
                "http://localhost:5175",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174",
                "http://127.0.0.1:5175",
                "http://localhost:3000"
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-MongoDB-URI", "X-Connection-ID"],
            "supports_credentials": True
        }
    })
    
    # Validate configuration (warn but don't exit)
    try:
        Config.validate()
    except ValueError as e:
        print(f"[App] Configuration warning: {e}")
        print("[App] The app will start but some features may not work until configuration is complete.")
        print("[App] Please check your .env file")
        # Don't exit - let the app start so user can configure via UI
    
    # Register blueprints
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(query_bp, url_prefix='/api')
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(collections_bp, url_prefix='/api')
    app.register_blueprint(config_bp, url_prefix='/api')
    app.register_blueprint(connections_bp, url_prefix='/api')
    app.register_blueprint(ingestion_bp, url_prefix='/api')
    app.register_blueprint(origin_bp, url_prefix='/api')
    
    # Initialize real-time ingestion service (optional, can be enabled via config)
    # Uncomment and configure if you want real-time ingestion on startup
    # try:
    #     from backend.services.realtime_ingestion import initialize_realtime_service
    #     if Config.ENABLE_REALTIME_INGESTION:
    #         initialize_realtime_service(
    #             db_name='sample_mflix',
    #             origin_collection='movies',
    #             target_vector_collection='srugenai_db.movies',
    #             mongodb_uri=Config.MONGODB_URI,
    #             auto_start=True
    #         )
    #         print("[App] Real-time ingestion service started")
    # except Exception as e:
    #     print(f"[App] Warning: Could not start real-time ingestion service: {e}")
    
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

