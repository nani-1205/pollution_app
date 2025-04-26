from flask import render_template, request, redirect, url_for, flash, current_app, Blueprint
# VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
from decimal import Decimal # <-- ADD THIS IMPORT
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
from .utils import get_price, calculate_expiry_date, generate_pie_chart, get_utc_date_range
from . import IST, UTC, get_collection # Import IST/UTC from __init__ and get_collection helper
from datetime import datetime
from bson import ObjectId # If you need to query by _id later
import pytz
import logging

logger = logging.getLogger(__name__)
# UTC = pytz.utc # Already imported from __init__

# Using Blueprint for better organization (optional but good practice)
main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET', 'POST'])
def dashboard1():
    """Handles the data input form (Dashboard 1)."""
    submitted_data = request.form if request.method == 'POST' else {} # Keep submitted data on error

    if request.method == 'POST':
        vehicle_no = request.form.get('vehicle_no', '').strip().upper()
        vehicle_type = request.form.get('vehicle_type') # petrol/diesel
        wheels_str = request.form.get('wheels')
        duration_str = request.form.get('duration') # six_months/one_year

        # --- Basic Validation ---
        errors = []
        if not vehicle_no: errors.append("Vehicle Number is required.")
        # Add regex validation for vehicle_no if needed (e.g., using re module)
        if not vehicle_type or vehicle_type not in ['petrol', 'diesel']: errors.append("Invalid Vehicle Fuel Type selected.")
        if not wheels_str or not wheels_str.isdigit(): errors.append("Invalid Number of Wheels selected.")
        if not duration_str or duration_str not in ['six_months', 'one_year']: errors.append("Invalid Duration Period selected.")

        # Proceed with further checks only if basic types are okay
        wheels = 0
        if wheels_str and wheels_str.isdigit():
             wheels = int(wheels_str)
             if wheels not in [2, 3, 4]: errors.append("Wheels must be 2, 3, or 4.")
             # Check fuel type compatibility *after* confirming wheels is valid
             if wheels == 2 and vehicle_type == 'diesel': errors.append("2-Wheelers cannot be Diesel type.")
        elif wheels_str: # If it's not empty but not a digit
            errors.append("Number of Wheels must be a number (2, 3, or 4).")


        if errors:
            for error in errors:
                flash(error, 'danger')
            # Return form with submitted values to avoid re-typing everything
            return render_template('dashboard1.html', submitted_data=submitted_data)

        # --- Process Valid Data ---
        duration_months = 6 if duration_str == 'six_months' else 12

        price = get_price(wheels, duration_months)
        # Check if price calculation failed (get_price returns Decimal('0.0') on error)
        if price == Decimal('0.0'): # <--- THIS LINE CAUSED THE ERROR
             flash("Could not determine price. Check price configuration in .env file.", "danger")
             return render_template('dashboard1.html', submitted_data=submitted_data)


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
            "price": float(price), # Store as float/double in MongoDB for wider compatibility
            "check_date": check_time_utc, # Store as native BSON Date (UTC)
            "expiry_date": expiry_time_utc, # Store as native BSON Date (UTC)
            # Storing strings is optional, can format on retrieval if needed
            # "check_date_ist_str": check_time_ist.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
            # "expiry_date_ist_str": expiry_time_ist.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
        }

        # --- Insert into MongoDB ---
        collection = get_collection()
        if collection is not None:
            try:
                result = collection.insert_one(entry)
                flash(f"Pollution check added successfully! Record ID: {result.inserted_id}", 'success')
                logger.info(f"Inserted record for {vehicle_no} with ID: {result.inserted_id}")
                return redirect(url_for('main.dashboard1')) # Redirect to clear form on success
            except Exception as e:
                logger.error(f"Failed to insert data into MongoDB: {e}")
                flash(f"Database error: Could not save data. Details: {e}", 'danger')
        else:
             # This message now comes from get_collection check, but added explicit user feedback
             flash("Database connection is not available. Cannot save data. Please check server logs.", "danger")


        # If insertion failed or DB connection issue, show form again with data
        return render_template('dashboard1.html', submitted_data=submitted_data)

    # --- Handle GET Request ---
    # Pass empty dict for submitted_data on initial GET load
    return render_template('dashboard1.html', submitted_data={})


@main_bp.route('/reports', methods=['GET', 'POST'])
def dashboard2():
    """Handles the reports generation (Dashboard 2)."""
    report_data = None
    charts = {}
    start_date_str = request.form.get('start_date', "") # Default to empty string
    end_date_str = request.form.get('end_date', "")   # Default to empty string

    if request.method == 'POST':
        # start_date_str = request.form.get('start_date') # Already got above
        # end_date_str = request.form.get('end_date')

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
                                    # Count fuel types only for 3 and 4 wheelers
                                    'type_petrol_3_4': {'$sum': {'$cond': [{'$and': [
                                        {'$in': ['$wheels', [3, 4]]}, # Wheels is 3 or 4
                                        {'$eq': ['$vehicle_type', 'petrol']}
                                    ]}, 1, 0]}},
                                     'type_diesel_3_4': {'$sum': {'$cond': [{'$and': [
                                        {'$in': ['$wheels', [3, 4]]}, # Wheels is 3 or 4
                                        {'$eq': ['$vehicle_type', 'diesel']}
                                    ]}, 1, 0]}},
                                }
                            },
                            {
                                '$project': { # Reshape the output
                                    '_id': 0,
                                    # Use $ifNull to ensure fields exist even if no documents match
                                    'total_sales': {'$ifNull': ['$total_sales', 0]},
                                    'total_checks': {'$ifNull': ['$total_checks', 0]},
                                    'counts_by_wheel': {
                                        '2': {'$ifNull': ['$wheels_2', 0]},
                                        '3': {'$ifNull': ['$wheels_3', 0]},
                                        '4': {'$ifNull': ['$wheels_4', 0]}
                                    },
                                    'counts_by_duration': {
                                        '6': {'$ifNull': ['$duration_6m', 0]},
                                        '12': {'$ifNull': ['$duration_12m', 0]}
                                    },
                                     'counts_by_fuel_3_4': {
                                        'petrol': {'$ifNull': ['$type_petrol_3_4', 0]},
                                        'diesel': {'$ifNull': ['$type_diesel_3_4', 0]}
                                    }
                                }
                            }
                        ]

                        results = list(collection.aggregate(pipeline))

                        if results:
                            report_data = results[0] # Aggregation returns a list, get the first doc
                            logger.info(f"Report generated for {start_date_str} to {end_date_str}: {report_data}")

                            # --- Generate Charts ---
                            # Ensure data exists before generating charts
                            if report_data.get('total_checks', 0) > 0:
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
                                # Only generate fuel chart if there is data for 3/4 wheelers
                                if sum(fuel_data) > 0:
                                     charts['fuel'] = generate_pie_chart(fuel_data, fuel_labels, "Fuel Type (3 & 4 Wheelers)", fuel_colors)
                                else:
                                     logger.info("No data for 3/4 wheeler fuel types chart.")


                        else:
                            # No results found for the date range
                            flash(f"No records found for the selected date range ({start_date_str} to {end_date_str}).", "info")
                            report_data = {} # Set to empty dict to avoid errors in template, indicates no data

                    except Exception as e:
                        logger.error(f"Error generating report: {e}", exc_info=True) # Log traceback
                        flash(f"Error generating report: {e}", "danger")
                        report_data = None # Indicate an error occurred
                else:
                     # DB connection issue
                     flash("Database connection is not available. Cannot generate report.", "danger")
                     report_data = None # Indicate an error occurred

            else:
                # Invalid date range input
                flash("Invalid date range selected or format incorrect (use YYYY-MM-DD).", "warning")
                report_data = None # Indicate an error occurred

    # --- Render Template (GET or after POST) ---
    # Pass the date strings back to the template to repopulate the form
    return render_template('dashboard2.html',
                           report_data=report_data,
                           charts=charts,
                           start_date=start_date_str,
                           end_date=end_date_str)