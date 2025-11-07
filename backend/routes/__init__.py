"""Route handlers for the Flask application."""

from .upload import upload_bp
from .query import query_bp
from .health import health_bp

__all__ = ['upload_bp', 'query_bp', 'health_bp']

