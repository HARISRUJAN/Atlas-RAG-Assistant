"""MongoDB client utility for consistent connection handling."""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from backend.config import Config


def create_mongodb_client():
    """
    Create a MongoDB client with proper SSL/TLS configuration for Atlas.
    
    Returns:
        MongoClient instance configured for MongoDB Atlas
        
    Raises:
        ConnectionFailure: If connection fails
    """
    # Base connection parameters
    connection_params = {
        'serverSelectionTimeoutMS': 30000,
        'connectTimeoutMS': 30000,
        'socketTimeoutMS': 30000,
    }
    
    # For mongodb+srv:// connections, TLS is automatically enabled
    # For standard mongodb:// connections, we may need to explicitly enable TLS
    if Config.MONGODB_URI and not Config.MONGODB_URI.startswith('mongodb+srv://'):
        connection_params['tls'] = True
        connection_params['tlsAllowInvalidCertificates'] = False
    
    # If SSL handshake issues persist, you can temporarily set:
    # connection_params['tlsAllowInvalidCertificates'] = True
    # (NOT recommended for production - only for troubleshooting)
    
    try:
        client = MongoClient(Config.MONGODB_URI, **connection_params)
        # Test the connection
        client.admin.command('ping')
        return client
    except ConnectionFailure as e:
        raise ConnectionFailure(
            f"Failed to connect to MongoDB: {str(e)}\n"
            "Troubleshooting tips:\n"
            "1. Verify your MONGODB_URI in .env file is correct\n"
            "2. Check if your IP address is whitelisted in MongoDB Atlas\n"
            "3. Ensure your MongoDB Atlas cluster is running\n"
            "4. Verify username and password are correct\n"
            "5. Check network/firewall settings"
        )

