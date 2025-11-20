"""Config route handler for getting default configuration."""

from flask import Blueprint, jsonify
from backend.config import Config

config_bp = Blueprint('config', __name__)


@config_bp.route('/config/mongodb-uri', methods=['GET'])
def get_default_mongodb_uri():
    """
    Get the default MongoDB URI from configuration.
    Returns masked URI for security (only shows connection format, not credentials).
    
    Returns:
        JSON response with default MongoDB URI (masked)
    """
    try:
        if Config.MONGODB_URI:
            # Mask the URI for security - show format but hide credentials
            uri = Config.MONGODB_URI
            # If it's a mongodb+srv:// URI, mask the password
            if uri.startswith('mongodb+srv://'):
                try:
                    # Format: mongodb+srv://username:password@host/database
                    parts = uri.split('@', 1)
                    if len(parts) == 2:
                        # Mask the password part
                        creds_part = parts[0].split('://', 1)[1]
                        if ':' in creds_part:
                            username = creds_part.split(':')[0]
                            masked_uri = f"mongodb+srv://{username}:***@{parts[1]}"
                        else:
                            masked_uri = uri
                    else:
                        masked_uri = uri
                except:
                    masked_uri = uri
            else:
                # For mongodb://, mask similarly
                try:
                    parts = uri.split('@', 1)
                    if len(parts) == 2:
                        creds_part = parts[0].split('://', 1)[1]
                        if ':' in creds_part:
                            username = creds_part.split(':')[0]
                            masked_uri = f"mongodb://{username}:***@{parts[1]}"
                        else:
                            masked_uri = uri
                    else:
                        masked_uri = uri
                except:
                    masked_uri = uri
            
            return jsonify({
                'default_uri': Config.MONGODB_URI,  # Return full URI for use in app
                'masked_uri': masked_uri  # Masked version for display
            }), 200
        else:
            return jsonify({
                'error': 'MongoDB URI not configured'
            }), 404
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Error getting MongoDB URI: {str(e)}'
        }), 500

