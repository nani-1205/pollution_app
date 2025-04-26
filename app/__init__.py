import os
from flask import Flask, g, current_app, flash
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
from dotenv import load_dotenv
import pytz
import logging
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define IST Timezone
IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.utc

def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev_secret_key'),
        DEBUG=os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    )

    # --- MongoDB Connection ---
    mongo_ip = os.getenv('MONGO_IP')
    mongo_port = os.getenv('MONGO_PORT')
    mongo_user = os.getenv('MONGO_USER')
    mongo_pass = os.getenv('MONGO_PASS')
    mongo_auth_db = os.getenv('MONGO_AUTH_DB')
    mongo_db_name = os.getenv('MONGO_DB_NAME')

    # Store connection details in app config
    app.config['MONGO_IP'] = mongo_ip
    app.config['MONGO_PORT'] = mongo_port
    app.config['MONGO_USER'] = mongo_user
    app.config['MONGO_PASS'] = mongo_pass
    app.config['MONGO_AUTH_DB'] = mongo_auth_db
    app.config['MONGO_DB_NAME'] = mongo_db_name
    app.config['POLLUTION_COLLECTION'] = None
    app.config['MONGO_CLIENT'] = None # Initialize client config key

    if not all([mongo_ip, mongo_port, mongo_user, mongo_pass, mongo_auth_db, mongo_db_name]):
        logger.error("Missing MongoDB configuration in .env file!")
    else:
        try:
            logger.info(f"Attempting to connect to MongoDB at {mongo_ip}:{mongo_port} using auth DB {mongo_auth_db}")
            client = MongoClient(host=mongo_ip, port=int(mongo_port),
                                 username=mongo_user, password=mongo_pass,
                                 authSource=mongo_auth_db,
                                 serverSelectionTimeoutMS=5000,
                                 connectTimeoutMS=5000)

            # Check connection
            client.admin.command('ismaster')
            logger.info("MongoDB connection successful.")

            db = client[mongo_db_name]
            pollution_collection = db['pollution_checks']

            # Store collection and client in app config
            app.config['POLLUTION_COLLECTION'] = pollution_collection
            app.config['MONGO_CLIENT'] = client # Store the client instance
            logger.info(f"Using database '{mongo_db_name}' and collection 'pollution_checks'.")

        except (ConnectionFailure, ConfigurationError, Exception) as e:
             logger.error(f"MongoDB setup failed: {e}")
             # Ensure config keys reflect failure state if client wasn't created
             if 'client' in locals() and client:
                 client.close() # Attempt to close if partially created
             app.config['POLLUTION_COLLECTION'] = None
             app.config['MONGO_CLIENT'] = None


    # --- Register Blueprints/Routes ---
    with app.app_context():
        from . import routes
        from . import utils

        app.register_blueprint(routes.main_bp)

    # Make IST available globally in templates
    app.jinja_env.globals['IST'] = IST

    # --- REMOVE OR COMMENT OUT TEARDOWN ---
    # @app.teardown_appcontext
    # def teardown_db(exception=None):
    #     client = app.config.pop('MONGO_CLIENT', None) # Use pop to remove it
    #     if client is not None:
    #         client.close()
    #         logger.info("MongoDB connection closed.")
    # --- END OF REMOVAL ---

    return app

# Helper function to get the collection safely from app config
def get_collection():
    """Gets the MongoDB collection from the application context."""
    # Ensure we are in an app context
    if not current_app:
        logger.error("Attempted to get collection outside of application context.")
        return None

    # Check if client connection failed during startup
    if not current_app.config.get('MONGO_CLIENT'):
         logger.warning("Attempted to access MongoDB collection, but client connection failed during startup.")
         return None

    collection = current_app.config.get('POLLUTION_COLLECTION')
    if collection is None:
         # This case might happen if DB/Collection access failed even if client connected
         logger.warning("Attempted to access MongoDB collection, but it's not available in config.")
    return collection

# Helper to get current IST time
def get_ist_time():
    """Returns the current time in IST timezone."""
    return datetime.now(IST)