"""Simple script to start the MongoDB RAG System."""

import subprocess
import sys
import os
import time

print("=" * 60)
print("MongoDB RAG System Startup")
print("=" * 60)
print()

# Check if we're in the project root
if not os.path.exists('backend/app.py'):
    print("ERROR: Please run this script from the project root directory")
    sys.exit(1)

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

print("Starting Backend Server...")
print("-" * 60)

# Start backend
try:
    from backend.app import create_app
    from backend.config import Config
    
    app = create_app()
    print(f"\n[OK] Backend starting on http://localhost:{Config.FLASK_PORT}")
    print(f"[OK] API endpoints available at http://localhost:{Config.FLASK_PORT}/api")
    print("\nBackend is running. Press Ctrl+C to stop.")
    print("="*60)
    print("\nIn another terminal, start the frontend with:")
    print("  cd frontend")
    print("  npm run dev")
    print("="*60)
    print()
    
    app.run(
        host='0.0.0.0',
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )
except KeyboardInterrupt:
    print("\n\nShutting down backend...")
    sys.exit(0)
except Exception as e:
    print(f"\n[ERROR] ERROR starting backend: {e}")
    print("\nPlease check:")
    print("1. .env file is configured with all required variables")
    print("2. MongoDB connection string is correct")
    print("3. All dependencies are installed (pip install -r requirements.txt)")
    sys.exit(1)

