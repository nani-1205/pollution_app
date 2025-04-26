import os
from flask import Flask, g, current_app, flash # Added current_app, flash
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
from dotenv import load_dotenv
import pytz
import logging
from datetime import datetime # Added datetime

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define IST Timezone
IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.utc # Added UTC for clarity

# Global variable placeholder - managed within app context now
# pollution_collection = None # Removed global variable

def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev_secret_key'), # Default for safety
        DEBUG=os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't') # Read debug flag from env
    )

    # --- MongoDB Connection ---
    mongo_ip = os.getenv('MONGO_IP')
    mongo_port = os.getenv('MONGO_PORT')
    mongo_user = os.getenv('MONGO_USER')
    mongo_pass = os.getenv('MONGO_PASS')
    mongo_auth_db = os.getenv('MONGO_AUTH_DB')
    mongo_db_name = os.getenv('MONGO_DB_NAME')

    # Store connection details in app config for access later
    app.config['MONGO_IP'] = mongo_ip
    app.config['MONGO_PORT'] = mongo_port
    app.config['MONGO_USER'] = mongo_user
    app.config['MONGO_PASS'] = mongo_pass
    app.config['MONGO_AUTH_DB'] = mongo_auth_db
    app.config['MONGO_DB_NAME'] = mongo_db_name
    app.config['POLLUTION_COLLECTION'] = None # Initialize as None

    if not all([mongo_ip, mongo_port, mongo_user, mongo_pass, mongo_auth_db, mongo_db_name]):
        logger.error("Missing MongoDB configuration in .env file!")
        # The application will continue, but DB operations will fail gracefully in routes
    else:
        try:
            # Construct the connection string components carefully (optional, direct connection used below)
            # uri = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_ip}:{mongo_port}/?authSource={mongo_auth_db}"
            logger.info(f"Attempting to connect to MongoDB at {mongo_ip}:{mongo_port} using auth DB {mongo_auth_db}")

            # Explicitly set the port as an integer
            client = MongoClient(host=mongo_ip, port=int(mongo_port),
                                 username=mongo_user, password=mongo_pass,
                                 authSource=mongo_auth_db,
                                 # Added timeouts for robustness
                                 serverSelectionTimeoutMS=5000, # 5 seconds timeout
                                 connectTimeoutMS=5000,
                                 # Consider adding retryWrites=True for resilience if supported
                                 )

            # The ismaster command is cheap and does not require auth. Checks network connectivity.
            client.admin.command('ismaster')
            logger.info("MongoDB connection successful (pre-auth check).")

            # Select database and collection
            db = client[mongo_db_name]
            pollution_collection = db['pollution_checks']

            # Store the collection object in app config for easy access in routes
            app.config['POLLUTION_COLLECTION'] = pollution_collection
            logger.info(f"Using database '{mongo_db_name}' and collection 'pollution_checks'.")

            # Optionally store the client itself if needed for teardown or advanced operations
            app.config['MONGO_CLIENT'] = client


        except ConnectionFailure as e:
            logger.error(f"MongoDB Connection Failed: {e}")
            # app.config['POLLUTION_COLLECTION'] remains None
        except ConfigurationError as e:
            logger.error(f"MongoDB Configuration Error: {e}")
            # app.config['POLLUTION_COLLECTION'] remains None
        except Exception as e: # Catch other potential errors like auth failures, DNS issues
             logger.error(f"An unexpected error occurred during MongoDB setup: {e}")
             # app.config['POLLUTION_COLLECTION'] remains None


    # --- Register Blueprints/Routes ---
    # Use app_context to ensure imports happen after app is configured
    with app.app_context():
        from . import routes # Import routes module where main_bp is defined
        from . import utils  # Import utils module

        # !!! REGISTER THE BLUEPRINT HERE !!!
        app.register_blueprint(routes.main_bp)
        # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    # Make IST available globally in templates if needed
    app.jinja_env.globals['IST'] = IST

    # Teardown context for database connection (optional, good practice)
    # This ensures the client connection is closed when the app context ends
    @app.teardown_appcontext
    def teardown_db(exception=None):
        client = app.config.pop('MONGO_CLIENT', None) # Use pop to remove it
        if client is not None:
            client.close()
            logger.info("MongoDB connection closed.")

    return app

# Helper function to get the collection safely from app config
def get_collection():
    """Gets the MongoDB collection from the application context."""
    collection = current_app.config.get('POLLUTION_COLLECTION')
    if collection is None:
         # Routes should handle this by checking the return value
         logger.warning("Attempted to access MongoDB collection, but it's not available (connection likely failed).")
         # Avoid flashing here, let the route handle user feedback
         # flash("Database connection error. Please check server logs.", "danger")
    return collection

# Helper to get current IST time
def get_ist_time():
    """Returns the current time in IST timezone."""
    return datetime.now(IST)