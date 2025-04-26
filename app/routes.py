from flask import render_template, request, redirect, url_for, flash, current_app, Blueprint
from .utils import get_price, calculate_expiry_date, generate_pie_chart, get_utc_date_range
from . import IST, get_collection # Import IST from __init__ and get_collection helper
from datetime import datetime
from bson import ObjectId # If you need to query by _id later
import pytz
import logging

logger = logging.getLogger(__name__)
UTC = pytz.utc

# Using Blueprint for better organization (optional but good practice)
main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET', 'POST'])
def dashboard1():
    """Handles the data input form (Dashboard 1)."""
    if request.method == 'POST':
        vehicle_no = request.form.get('vehicle_no', '').strip().upper()
        vehicle_type = request.form.get('vehicle_type') # petrol/diesel
        wheels_str = request.form.get('wheels')
        duration_str = request.form.get('duration') # six_months/one_year

        # --- Basic Validation ---
        errors = []
        if not vehicle_no: errors.append("Vehicle Number is required.")
        # Add regex validation for vehicle_no if needed
        if not vehicle_type in ['petrol', 'diesel']: errors.append("Invalid Vehicle Type.")
        if not wheels_str or not wheels_str.isdigit(): errors.append("Invalid Number of Wheels.")
        if not duration_str in ['six_months', 'one_year']: errors.append("Invalid Duration.")

        wheels = int(wheels_str) if wheels_str and wheels_str.isdigit() else 0
        if wheels not in [2, 3, 4]: errors.append("Wheels must be 2, 3, or 4.")
        if wheels == 2 and vehicle_type == 'diesel': errors.append("2-Wheelers cannot be Diesel type.")

        if errors:
            for error in errors:
                flash(error, 'danger')
            # Return form with submitted values to avoid re-typing everything
            return render_template('dashboard1.html', submitted_data=request.form)

        # --- Process Valid Data ---
        duration_months = 6 if duration_str == 'six_months' else 12
        price = get_price(wheels, duration_months)
        if price == Decimal('0.0'): # Check if price calculation failed
             flash("Could not determine price. Check configuration.", "danger")
             return render_template('dashboard1.html', submitted_data=request.form)


        check_time_ist = datetime.now(IST)
        expiry_time_ist = calculate_expiry_date(check_time_ist, duration_months)

        # Convert dates to UTC for storage
        check_time_utc = check_time_ist.astimezone(UTC)
        expiry_time_utc = expiry_time_ist.astimezone(UTC)

        # --- Prepare Data for MongoDB ---
        entry = {
            "vehicle_no": vehicle_no,
            "vehicle_type": vehicle_type,
            "wheels": wheels,
            "duration_months": duration_months,
            "price": float(price), # Store as float/double in MongoDB
            "check_date": check_time_utc,
            "expiry_date": expiry_time_utc,
            "check_date_ist_str": check_time_ist.strftime('%Y-%m-%d %H:%M:%S %Z%z'), # Store IST string for easy display if needed
            "expiry_date_ist_str": expiry_time_ist.strftime('%Y-%m-%d %H:%M:%S %Z%z'),# Store IST string
        }

        # --- Insert into MongoDB ---
        collection = get_collection()
        if collection is not None:
            try:
                result = collection.insert_one(entry)
                flash(f"Pollution check added successfully! ID: {result.inserted_id}", 'success')
                logger.info(f"Inserted record for {vehicle_no} with ID: {result.inserted_id}")
                return redirect(url_for('main.dashboard1')) # Redirect to clear form
            except Exception as e:
                logger.error(f"Failed to insert data into MongoDB: {e}")
                flash(f"Database error: Could not save data. {e}", 'danger')
        else:
             flash("Database connection is not available. Cannot save data.", "danger")


        # If insertion failed or DB connection issue, show form again with data
        return render_template('dashboard1.html', submitted_data=request.form)

    # --- Handle GET Request ---
    return render_template('dashboard1.html')


@main_bp.route('/reports', methods=['GET', 'POST'])
def dashboard2():
    """Handles the reports generation (Dashboard 2)."""
    report_data = None
    charts = {}
    start_date_str = ""
    end_date_str = ""

    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        if not start_date_str or not end_date_str:
            flash("Please select both Start Date and End Date.", "warning")
        else:
            start_dt_utc, end_dt_utc = get_utc_date_range(start_date_str, end_date_str)

            if start_dt_utc and end_dt_utc:
                collection = get_collection()
                if collection is not None:
                    try:
                        # --- MongoDB Aggregation Pipeline ---
                        pipeline = [
                            {
                                '$match': {
                                    'check_date': {
                                        '$gte': start_dt_utc,
                                        '$lt': end_dt_utc # Use $lt for end date (exclusive)
                                    }
                                }
                            },
                            {
                                '$group': {
                                    '_id': None, # Group all documents in the range
                                    'total_sales': {'$sum': '$price'},
                                    'total_checks': {'$sum': 1},
                                    'wheels_2': {'$sum': {'$cond': [{'$eq': ['$wheels', 2]}, 1, 0]}},
                                    'wheels_3': {'$sum': {'$cond': [{'$eq': ['$wheels', 3]}, 1, 0]}},
                                    'wheels_4': {'$sum': {'$cond': [{'$eq': ['$wheels', 4]}, 1, 0]}},
                                    'duration_6m': {'$sum': {'$cond': [{'$eq': ['$duration_months', 6]}, 1, 0]}},
                                    'duration_12m': {'$sum': {'$cond': [{'$eq': ['$duration_months', 12]}, 1, 0]}},
                                    'type_petrol_3_4': {'$sum': {'$cond': [{'$and': [
                                        {'$ne': ['$wheels', 2]}, # Not 2-wheeler
                                        {'$eq': ['$vehicle_type', 'petrol']}
                                    ]}, 1, 0]}},
                                     'type_diesel_3_4': {'$sum': {'$cond': [{'$and': [
                                        {'$ne': ['$wheels', 2]}, # Not 2-wheeler
                                        {'$eq': ['$vehicle_type', 'diesel']}
                                    ]}, 1, 0]}},
                                    # You could add counts for 2-wheeler petrol separately if needed
                                }
                            },
                            {
                                '$project': { # Reshape the output
                                    '_id': 0,
                                    'total_sales': {'$ifNull': ['$total_sales', 0]},
                                    'total_checks': {'$ifNull': ['$total_checks', 0]},
                                    'counts_by_wheel': {
                                        '2': '$wheels_2',
                                        '3': '$wheels_3',
                                        '4': '$wheels_4'
                                    },
                                    'counts_by_duration': {
                                        '6': '$duration_6m',
                                        '12': '$duration_12m'
                                    },
                                     'counts_by_fuel_3_4': {
                                        'petrol': '$type_petrol_3_4',
                                        'diesel': '$type_diesel_3_4'
                                    }
                                }
                            }
                        ]

                        results = list(collection.aggregate(pipeline))

                        if results:
                            report_data = results[0] # Aggregation returns a list
                            logger.info(f"Report generated for {start_date_str} to {end_date_str}: {report_data}")

                            # --- Generate Charts ---
                            # 1. Wheels Chart
                            wheel_labels = ['2 Wheeler', '3 Wheeler', '4 Wheeler']
                            wheel_data = [report_data['counts_by_wheel'].get('2', 0),
                                          report_data['counts_by_wheel'].get('3', 0),
                                          report_data['counts_by_wheel'].get('4', 0)]
                            wheel_colors = ['#66b3ff', '#ffcc99', '#99ff99'] # Example Colors
                            charts['wheels'] = generate_pie_chart(wheel_data, wheel_labels, "Checks by Vehicle Wheels", wheel_colors)

                            # 2. Duration Chart
                            duration_labels = ['6 Months', '1 Year']
                            duration_data = [report_data['counts_by_duration'].get('6', 0),
                                             report_data['counts_by_duration'].get('12', 0)]
                            duration_colors = ['#ff9999', '#c2c2f0']
                            charts['duration'] = generate_pie_chart(duration_data, duration_labels, "Checks by Duration", duration_colors)

                            # 3. Fuel Type Chart (3 & 4 Wheelers only)
                            fuel_labels = ['Petrol (3/4 W)', 'Diesel (3/4 W)']
                            fuel_data = [report_data['counts_by_fuel_3_4'].get('petrol', 0),
                                         report_data['counts_by_fuel_3_4'].get('diesel', 0)]
                            fuel_colors = ['#ffb3e6', '#ffb366']
                            charts['fuel'] = generate_pie_chart(fuel_data, fuel_labels, "Fuel Type (3 & 4 Wheelers)", fuel_colors)

                        else:
                            flash("No records found for the selected date range.", "info")
                            report_data = {} # Set to empty dict to avoid errors in template


                    except Exception as e:
                        logger.error(f"Error generating report: {e}")
                        flash(f"Error generating report: {e}", "danger")
                else:
                     flash("Database connection is not available. Cannot generate report.", "danger")

            else:
                flash("Invalid date range selected.", "warning")

    # --- Render Template (GET or after POST) ---
    return render_template('dashboard2.html',
                           report_data=report_data,
                           charts=charts,
                           start_date=start_date_str,
                           end_date=end_date_str)

# Register the blueprint in __init__.py:
# from . import routes
# app.register_blueprint(routes.main_bp)