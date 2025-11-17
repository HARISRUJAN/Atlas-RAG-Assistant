"""Route handlers for the Flask application."""

from .upload import upload_bp
from .query import query_bp
from .health import health_bp
from .collections import collections_bp
from .config import config_bp
from .connections import connections_bp

__all__ = ['upload_bp', 'query_bp', 'health_bp', 'collections_bp', 'config_bp', 'connections_bp']

