# Flask Pollution Check Web App 🚗💨📊

A simple web application built with Python (Flask) and MongoDB to record vehicle pollution check data and generate summary reports with visualizations.

## Features

*   **Data Entry:** Record pollution check details including:
    *   Vehicle Number (e.g., AP21AT7100)
    *   Vehicle Fuel Type (Petrol/Diesel - dynamically adjusted based on wheels)
    *   Number of Wheels (2, 3, 4)
    *   Duration Period (Six Months / One Year)
*   **Dynamic Pricing:** Calculates the price based on wheel type and duration. Prices are configurable via environment variables.
*   **IST Timezone:** Records check timestamps using the Indian Standard Time (IST) internet clock.
*   **Report Generation:** Generate reports for a selected date range, showing:
    *   Total count of 2, 3, and 4 wheelers checked.
    *   Total count of checks for 6-month and 1-year durations.
    *   Total count of Petrol vs. Diesel vehicles (for 3 & 4 wheelers).
    *   Total sales amount for the period.
*   **Data Visualization:** Displays reports using server-side generated Pie Charts (via Matplotlib) for:
    *   Wheels Distribution
    *   Duration Distribution
    *   Fuel Type Distribution (3/4 Wheelers)
*   **MongoDB Storage:** Uses MongoDB to store pollution check records persistently. Creates the database and collection if they don't exist.
*   **Environment Configuration:** Database credentials, pricing, and Flask settings are managed securely via a `.env` file.
*   **Enhanced UI:** Uses Bootstrap 5 with custom CSS and JavaScript for a modern, interactive, and responsive user interface.

## Technology Stack

*   **Backend:** Python 3, Flask
*   **Database:** MongoDB
*   **ODM/Driver:** PyMongo
*   **Frontend:** HTML, CSS (Bootstrap 5), JavaScript
*   **Charting:** Matplotlib (server-side generation)
*   **Environment Variables:** python-dotenv
*   **Timezone Handling:** pytz

## Prerequisites

Before you begin, ensure you have met the following requirements:

*   **Python:** Version 3.8 or higher installed.
*   **pip:** Python package installer (usually comes with Python).
*   **Git:** For cloning the repository.
*   **MongoDB:** A running MongoDB instance (local or remote like MongoDB Atlas) that is accessible from where you run the application. You'll need the connection details (IP/Hostname, Port, Username, Password, Authentication Database).

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/nani-1205/pollution_app.git
    cd pollution_app
    ```
    *(Replace `<your-repository-url>` with the actual URL if you host it on GitHub/GitLab etc.)*

2.  **Create a Virtual Environment:**
    It's highly recommended to use a virtual environment to manage project dependencies.
    ```bash
    python -m venv venv
    ```

3.  **Activate the Virtual Environment:**
    *   **On Windows:**
        ```bash
        .\venv\Scripts\activate
        ```
    *   **On macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```
    You should see `(venv)` prefixed to your command prompt.

4.  **Install Dependencies:**
    Install all the required Python packages listed in `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```

## Configuration (`.env` file)

The application uses a `.env` file in the project root to store configuration settings, especially sensitive ones like database credentials and adjustable pricing.

1.  **Create the `.env` file:**
    Copy the example file (`env.example` if you create one) or create a new file named `.env` in the `pollution_app` root directory.

2.  **Populate `.env`:**
    Add the following variables to your `.env` file and **replace the placeholder values** with your actual settings:

    ```dotenv
    # Flask Settings
    FLASK_APP=run.py
    FLASK_DEBUG=True # Set to False in production for security and performance
    SECRET_KEY='a_very_secret_random_key_change_me_please!' # Change this to a strong random string

    # MongoDB Settings
    MONGO_IP='127.0.0.1'          # Replace with your MongoDB IP/Hostname
    MONGO_PORT='27017'            # Replace with your MongoDB Port
    MONGO_USER='your_mongo_user'      # Replace with your MongoDB Username
    MONGO_PASS='your_mongo_password'  # Replace with your MongoDB Password
    MONGO_AUTH_DB='admin'         # Authentication Database (often 'admin', check your MongoDB setup)
    MONGO_DB_NAME='pollution_db'    # Your desired application database name

    # Pricing Configuration (INR) - User can change these
    PRICE_2W_6M=60
    PRICE_3W_6M=90
    PRICE_4W_6M=90
    PRICE_2W_12M=120
    PRICE_3W_12M=150
    PRICE_4W_12M=150
    ```

    *   **`SECRET_KEY`**: Crucial for session security. Generate a strong random key.
    *   **`MONGO_...`**: Fill in the correct details for your MongoDB instance.
    *   **`PRICE_...`**: Adjust these values as needed for current pollution check pricing.

## Running the Application

1.  **Ensure MongoDB is Running:** Make sure your MongoDB server instance is active and accessible with the credentials provided in `.env`.
2.  **Activate Virtual Environment:** If not already active, activate it (`source venv/bin/activate` or `.\venv\Scripts\activate`).
3.  **Start the Flask Development Server:**
    ```bash
    flask run
    ```
    *   By default, this usually runs on `http://127.0.0.1:5000/`.
    *   If you configured `host='0.0.0.0'` in `run.py` (as provided in the initial code), it will be accessible on your local network via your machine's IP address (e.g., `http://<your-local-ip>:5000`).
    *   If `FLASK_DEBUG=True` in `.env`, the server will automatically reload on code changes and provide detailed error pages. **Remember to set `FLASK_DEBUG=False` for production.**

4.  **Access the Application:** Open your web browser and navigate to `http://127.0.0.1:5000` (or the appropriate address).


## Notes

*   Ensure the `app/static/images` directory exists if you modify the chart generation to save files instead of using Base64.
*   The application automatically tries to create the MongoDB database and collection specified in `.env` if they don't exist upon the first data insertion.