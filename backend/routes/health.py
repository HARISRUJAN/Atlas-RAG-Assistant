"""Health check route handler."""

from flask import Blueprint, jsonify
import requests

from backend.config import Config

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON response with system health status
    """
    try:
        health_status = {
            'status': 'healthy',
            'mongodb': False,
            'llm_api': False,
            'mongodb_configured': bool(Config.MONGODB_URI),
            'llm_configured': bool(Config.LLM_API_URL and Config.LLM_API_KEY)
        }
        
        # Check MongoDB connection
        try:
            if Config.MONGODB_URI:
                try:
                    from pymongo import MongoClient
                    from pymongo.errors import ConnectionFailure
                    # Simple connection test without VectorStoreService
                    client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)
                    client.admin.command('ping')
                    health_status['mongodb'] = True
                    client.close()
                except Exception as conn_error:
                    health_status['mongodb_error'] = str(conn_error)
                    health_status['mongodb'] = False
            else:
                health_status['mongodb_error'] = 'MongoDB URI not configured'
                health_status['mongodb'] = False
        except Exception as e:
            health_status['mongodb_error'] = str(e)
            health_status['mongodb'] = False
            import traceback
            if Config.FLASK_DEBUG:
                health_status['mongodb_traceback'] = traceback.format_exc()
        
        # Check LLM API
        try:
            if Config.LLM_API_URL and Config.LLM_API_KEY:
                # Try to construct models endpoint URL
                llm_url = Config.LLM_API_URL
                if '/completions' in llm_url:
                    models_url = llm_url.replace('/completions', '/models')
                elif '/v1/chat/completions' in llm_url:
                    models_url = llm_url.replace('/v1/chat/completions', '/v1/models')
                else:
                    models_url = llm_url.rstrip('/') + '/models'
                
                response = requests.get(
                    models_url,
                    headers={'Authorization': f'Bearer {Config.LLM_API_KEY}'},
                    timeout=5
                )
                health_status['llm_api'] = response.status_code == 200
            else:
                health_status['llm_api_error'] = 'LLM API URL or key not configured'
        except Exception as e:
            health_status['llm_api_error'] = str(e)
        
        # Overall status - be more lenient, just check if configured
        if not health_status['mongodb_configured']:
            health_status['status'] = 'unconfigured'
        elif not health_status['mongodb'] or not health_status['llm_api']:
            health_status['status'] = 'degraded'
        
        # Return 200 even if degraded, so frontend can still work
        status_code = 200
        
        return jsonify(health_status), status_code
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[Health Check] ERROR: {str(e)}")
        print(error_trace)
        # Return error but don't crash - return 200 with error info
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': error_trace if Config.FLASK_DEBUG else None
        }), 200

