"""Collections route handler."""

from flask import Blueprint, jsonify
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import requests
from typing import List, Dict, Any

from backend.config import Config

collections_bp = Blueprint('collections', __name__)


@collections_bp.route('/collections', methods=['GET'])
def list_collections():
    """
    List all databases and their collections in MongoDB.
    
    Returns:
        JSON response with databases and their collections
    """
    try:
        # Configure MongoDB client with SSL/TLS support for Atlas
        connection_params = {
            'serverSelectionTimeoutMS': 30000,
            'connectTimeoutMS': 30000,
            'socketTimeoutMS': 30000,
        }
        
        # Handle connection string format
        if Config.MONGODB_URI and Config.MONGODB_URI.startswith('mongodb+srv://'):
            # For mongodb+srv://, TLS is automatic
            if 'retryWrites' not in Config.MONGODB_URI:
                separator = '&' if '?' in Config.MONGODB_URI else '?'
                uri_with_params = f"{Config.MONGODB_URI}{separator}retryWrites=true&w=majority"
            else:
                uri_with_params = Config.MONGODB_URI
        else:
            # For standard mongodb:// connections
            connection_params['tls'] = True
            connection_params['tlsAllowInvalidCertificates'] = False
            uri_with_params = Config.MONGODB_URI
        
        client = MongoClient(uri_with_params, **connection_params)
        # Test connection
        client.admin.command('ping')
        
        # Get all database names
        database_names = client.list_database_names()
        
        # Filter out system databases
        system_databases = {'admin', 'local', 'config'}
        filtered_databases = [
            name for name in database_names 
            if name not in system_databases
        ]
        
        # Get collections for each database
        databases = []
        for db_name in filtered_databases:
            db = client[db_name]
            collection_names = db.list_collection_names()
            
            # Filter out system collections
            filtered_collections = [
                name for name in collection_names 
                if not name.startswith('system.')
            ]
            
            if filtered_collections:  # Only include databases with collections
                databases.append({
                    'name': db_name,
                    'collections': filtered_collections
                })
        
        client.close()
        
        return jsonify({
            'databases': databases
        }), 200
        
    except ConnectionFailure as e:
        error_msg = str(e)
        # Provide helpful troubleshooting information for SSL errors
        if 'SSL' in error_msg or 'TLS' in error_msg or 'handshake' in error_msg:
            error_msg += (
                "\n\nSSL/TLS Troubleshooting:\n"
                "1. Verify your MONGODB_URI uses 'mongodb+srv://' format\n"
                "2. Check MongoDB Atlas IP whitelist includes your current IP\n"
                "3. Ensure your network allows SSL/TLS connections\n"
                "4. Try updating pymongo: pip install --upgrade pymongo\n"
                "5. Verify username and password in connection string are correct"
            )
        return jsonify({'error': error_msg}), 500
    except Exception as e:
        return jsonify({'error': f'Error listing collections: {str(e)}'}), 500


@collections_bp.route('/collections/<path:collection_path>/questions', methods=['GET'])
def generate_questions(collection_path: str):
    """
    Generate suggested questions based on collection content.
    
    Args:
        collection_path: Database and collection name in format "database.collection" or just "collection"
        
    Returns:
        JSON response with array of suggested questions
    """
    try:
        # Parse database and collection name
        # Format: "database.collection" or just "collection" (use default database)
        if '.' in collection_path:
            db_name, collection_name = collection_path.split('.', 1)
        else:
            db_name = Config.MONGODB_DATABASE_NAME
            collection_name = collection_path
        
        # Configure MongoDB client with SSL/TLS support for Atlas
        connection_params = {
            'serverSelectionTimeoutMS': 30000,
            'connectTimeoutMS': 30000,
            'socketTimeoutMS': 30000,
        }
        
        # Handle connection string format
        if Config.MONGODB_URI and Config.MONGODB_URI.startswith('mongodb+srv://'):
            # For mongodb+srv://, TLS is automatic
            if 'retryWrites' not in Config.MONGODB_URI:
                separator = '&' if '?' in Config.MONGODB_URI else '?'
                uri_with_params = f"{Config.MONGODB_URI}{separator}retryWrites=true&w=majority"
            else:
                uri_with_params = Config.MONGODB_URI
        else:
            # For standard mongodb:// connections
            connection_params['tls'] = True
            connection_params['tlsAllowInvalidCertificates'] = False
            uri_with_params = Config.MONGODB_URI
        
        client = MongoClient(uri_with_params, **connection_params)
        # Test connection
        client.admin.command('ping')
        db = client[db_name]
        
        # Check if collection exists
        if collection_name not in db.list_collection_names():
            client.close()
            return jsonify({'error': f'Collection "{collection_name}" not found in database "{db_name}"'}), 404
        
        collection = db[collection_name]
        
        # Sample documents from the collection (limit to 10)
        sample_docs = list(collection.find().limit(10))
        
        if not sample_docs:
            client.close()
            # Return default questions if collection is empty
            return jsonify({
                'questions': [
                    "What information is available in this collection?",
                    "What are the key details?",
                    "Summarize the main content"
                ]
            }), 200
        
        # Extract key information from sample documents
        # Get field names and sample content
        field_names = set()
        sample_content = []
        
        for doc in sample_docs:
            # Extract field names (excluding _id)
            field_names.update([k for k in doc.keys() if k != '_id'])
            
            # Extract text content from common fields
            content_fields = ['content', 'text', 'description', 'summary', 'title', 'name']
            for field in content_fields:
                if field in doc and isinstance(doc[field], str):
                    sample_content.append(doc[field][:500])  # Limit length
        
        # Create context for LLM
        context = f"Database: {db_name}\n"
        context += f"Collection: {collection_name}\n"
        context += f"Fields: {', '.join(sorted(field_names)[:20])}\n"  # Limit to 20 fields
        if sample_content:
            context += f"Sample content: {' '.join(sample_content[:3])[:1000]}\n"  # Limit total length
        
        # Generate questions using LLM
        questions = _generate_questions_with_llm(context, f"{db_name}.{collection_name}")
        
        client.close()
        
        return jsonify({
            'questions': questions
        }), 200
        
    except ConnectionFailure as e:
        error_msg = str(e)
        # Provide helpful troubleshooting information for SSL errors
        if 'SSL' in error_msg or 'TLS' in error_msg or 'handshake' in error_msg:
            error_msg += (
                "\n\nSSL/TLS Troubleshooting:\n"
                "1. Verify your MONGODB_URI uses 'mongodb+srv://' format\n"
                "2. Check MongoDB Atlas IP whitelist includes your current IP\n"
                "3. Ensure your network allows SSL/TLS connections\n"
                "4. Try updating pymongo: pip install --upgrade pymongo\n"
                "5. Verify username and password in connection string are correct"
            )
        return jsonify({'error': error_msg}), 500
    except Exception as e:
        return jsonify({'error': f'Error generating questions: {str(e)}'}), 500


def _generate_questions_with_llm(context: str, collection_name: str) -> List[str]:
    """
    Generate questions using LLM based on collection context.
    
    Args:
        context: Context about the collection
        collection_name: Name of the collection
        
    Returns:
        List of suggested questions
    """
    prompt = f"""Based on the following MongoDB collection information, generate 3-5 relevant questions that users might ask about this data.

Collection Information:
{context}

Generate questions that are:
1. Specific to the data in this collection
2. Useful for understanding the content
3. Varied in scope (some general, some specific)
4. Clear and concise

Return only the questions, one per line, without numbering or bullets."""

    try:
        # Call LLM API
        response = requests.post(
            Config.LLM_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Config.LLM_API_KEY}"
            },
            json={
                "model": Config.LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 200
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            # Extract answer from response
            answer = result.get('response', result.get('choices', [{}])[0].get('text', ''))
            
            # Parse questions (split by newlines and clean)
            questions = [
                q.strip() 
                for q in answer.strip().split('\n') 
                if q.strip() and not q.strip().startswith('#')
            ]
            
            # Filter out empty and ensure we have 3-5 questions
            questions = [q for q in questions if len(q) > 10][:5]
            
            # If we got valid questions, return them
            if questions:
                return questions
        
        # Fallback to default questions if LLM fails
        return _get_default_questions(collection_name)
        
    except Exception as e:
        print(f"Error generating questions with LLM: {e}")
        # Fallback to default questions
        return _get_default_questions(collection_name)


def _get_default_questions(collection_name: str) -> List[str]:
    """
    Get default questions when LLM generation fails.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        List of default questions
    """
    return [
        f"What information is available in {collection_name}?",
        "What are the key details in this collection?",
        "Summarize the main content",
        "What are the most important points?",
        "List the key information"
    ]

