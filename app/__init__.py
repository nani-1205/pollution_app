import os
from flask import Flask, g
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
from dotenv import load_dotenv
import pytz
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define IST Timezone
IST = pytz.timezone('Asia/Kolkata')

# Global variable to hold the MongoDB collection reference
pollution_collection = None

def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev_secret_key'), # Default for safety
    )

    # --- MongoDB Connection ---
    mongo_ip = os.getenv('MONGO_IP')
    mongo_port = os.getenv('MONGO_PORT')
    mongo_user = os.getenv('MONGO_USER')
    mongo_pass = os.getenv('MONGO_PASS')
    mongo_auth_db = os.getenv('MONGO_AUTH_DB')
    mongo_db_name = os.getenv('MONGO_DB_NAME')

    if not all([mongo_ip, mongo_port, mongo_user, mongo_pass, mongo_auth_db, mongo_db_name]):
        logger.error("Missing MongoDB configuration in .env file!")
        # Optionally raise an exception or handle appropriately
        # raise ConfigurationError("Missing MongoDB environment variables")
        # For now, we'll proceed but database operations will fail.
        client = None
    else:
        try:
            # Construct the connection string components carefully
            uri = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_ip}:{mongo_port}/?authSource={mongo_auth_db}"
            logger.info(f"Attempting to connect to MongoDB at {mongo_ip}:{mongo_port} using auth DB {mongo_auth_db}")

            # Explicitly set the port as an integer
            client = MongoClient(host=mongo_ip, port=int(mongo_port),
                                 username=mongo_user, password=mongo_pass,
                                 authSource=mongo_auth_db,
                                 # Added timeouts for robustness
                                 serverSelectionTimeoutMS=5000, # 5 seconds timeout
                                 connectTimeoutMS=5000)

            # The ismaster command is cheap and does not require auth.
            client.admin.command('ismaster')
            logger.info("MongoDB connection successful (pre-auth check).")

            db = client[mongo_db_name]
            # Test if the collection exists, if not it will be created on first insert
            # No explicit creation needed beforehand with MongoDB usually.
            global pollution_collection
            pollution_collection = db['pollution_checks']
            app.config['POLLUTION_COLLECTION'] = pollution_collection # Make collection accessible
            logger.info(f"Using database '{mongo_db_name}' and collection 'pollution_checks'.")

        except ConnectionFailure as e:
            logger.error(f"MongoDB Connection Failed: {e}")
            client = None
            app.config['POLLUTION_COLLECTION'] = None
        except ConfigurationError as e:
            logger.error(f"MongoDB Configuration Error: {e}")
            client = None
            app.config['POLLUTION_COLLECTION'] = None
        except Exception as e: # Catch other potential errors like auth failures
             logger.error(f"An unexpected error occurred during MongoDB setup: {e}")
             client = None
             app.config['POLLUTION_COLLECTION'] = None


    # --- Register Blueprints/Routes ---
    with app.app_context():
        from . import routes # Import routes after app is created
        from . import utils # Import utils

    # Make IST available globally in templates if needed
    app.jinja_env.globals['IST'] = IST

    # Teardown context for database connection if managing per request
    # @app.teardown_appcontext
    # def teardown_db(exception):
    #     db = g.pop('mongo_client', None)
    #     if db is not None:
    #         db.close() # Close connection if managed per request

    return app

# Function to get the collection (ensure it handles the case where connection failed)
def get_collection():
    collection = current_app.config.get('POLLUTION_COLLECTION')
    if collection is None:
         # Maybe raise an error or return None and handle in routes
         logger.error("Pollution collection is not available.")
         flash("Database connection error. Please check server logs.", "danger")
    return collection

# Helper to get current IST time
def get_ist_time():
    return datetime.now(IST)