"""Health check route handler."""

from flask import Blueprint, jsonify
import requests

from backend.config import Config
from backend.services.vector_store import VectorStoreService

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON response with system health status
    """
    health_status = {
        'status': 'healthy',
        'mongodb': False,
        'llm_api': False
    }
    
    # Check MongoDB connection
    try:
        vector_store = VectorStoreService()
        health_status['mongodb'] = vector_store.test_connection()
        vector_store.close()
    except Exception as e:
        health_status['mongodb_error'] = str(e)
    
    # Check LLM API
    try:
        response = requests.get(
            Config.LLM_API_URL.replace('/completions', '/models'),
            headers={'Authorization': f'Bearer {Config.LLM_API_KEY}'},
            timeout=5
        )
        health_status['llm_api'] = response.status_code == 200
    except Exception as e:
        health_status['llm_api_error'] = str(e)
    
    # Overall status
    if not health_status['mongodb'] or not health_status['llm_api']:
        health_status['status'] = 'degraded'
    
    status_code = 200 if health_status['mongodb'] and health_status['llm_api'] else 503
    
    return jsonify(health_status), status_code

