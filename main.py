import logging
import os
from app import app, register_routes

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Register all routes
register_routes(app)

# Initialize the application directory structure if it doesn't exist
from storage import initialize_storage
initialize_storage()

if __name__ == "__main__":
    # Start the Flask application
    app.run(host="0.0.0.0", port=5000, debug=True)
