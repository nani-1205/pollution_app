import os
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend suitable for web servers
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import pytz
import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.utc

# --- Price Calculation ---
def get_price(wheels: int, duration_months: int) -> Decimal:
    """Gets the price based on wheels and duration from environment variables."""
    price_key = f"PRICE_{wheels}W_{duration_months}M"
    price_str = os.getenv(price_key)
    try:
        if price_str is None:
            raise ValueError(f"Price configuration not found for key: {price_key}")
        price = Decimal(price_str)
        return price
    except (InvalidOperation, ValueError) as e:
        logger.error(f"Invalid price configuration for {price_key}: {price_str}. Error: {e}")
        # Return a default or raise a specific error
        return Decimal('0.0') # Or raise Exception("Invalid price configuration")

# --- Date Calculation ---
def calculate_expiry_date(check_date: datetime, duration_months: int) -> datetime:
    """Calculates the expiry date based on the check date and duration."""
    if not isinstance(check_date, datetime):
        raise TypeError("check_date must be a datetime object")
    # Adding months can be tricky with end-of-month dates, timedelta is safer for days
    # Approximate months as days (average 30.44 days/month) - More accurate libraries exist if needed
    # Or simply add months using relativedelta if library is added
    # For simplicity here, we add fixed days (6*30 or 12*30) - THIS IS NOT ACCURATE FOR EXACT MONTHS
    # A better approach for exact months:
    try:
        year = check_date.year + (check_date.month + duration_months - 1) // 12
        month = (check_date.month + duration_months - 1) % 12 + 1
        # Find the last day of the target month
        next_month_first_day = datetime(year, month + 1, 1, tzinfo=check_date.tzinfo) if month < 12 else datetime(year + 1, 1, 1, tzinfo=check_date.tzinfo)
        last_day_of_target_month = (next_month_first_day - timedelta(days=1)).day
        
        day = min(check_date.day, last_day_of_target_month)
        
        # Preserve original time and timezone
        expiry = datetime(year, month, day, 
                          check_date.hour, check_date.minute, check_date.second, check_date.microsecond,
                          tzinfo=check_date.tzinfo)
        return expiry
        
    except Exception as e:
         logger.error(f"Error calculating expiry date: {e}")
         # Fallback: simple days addition (less accurate)
         return check_date + timedelta(days=duration_months * 30)


# --- Chart Generation ---
def generate_pie_chart(data, labels, title, colors=None):
    """Generates a pie chart using Matplotlib and returns a base64 encoded image string."""
    if not data or not labels or len(data) != len(labels):
        logger.warning(f"Invalid data or labels for chart '{title}'. Skipping chart generation.")
        return None
    if sum(data) == 0:
        logger.info(f"No data to plot for chart '{title}'. Skipping chart generation.")
        return None # Don't generate chart if there's no data

    fig, ax = plt.subplots(figsize=(6, 4)) # Adjust size as needed

    # Use provided colors or default cycle
    if colors and len(colors) >= len(data):
        final_colors = colors[:len(data)]
    else:
        final_colors = plt.cm.Paired.colors # Default color map


    def autopct_format(values):
        def my_format(pct):
            total = sum(values)
            val = int(round(pct*total/100.0))
            return f'{pct:.1f}%\n({val:d})' if pct > 0 else '' # Show percentage and count
        return my_format

    wedges, texts, autotexts = ax.pie(data, labels=None, autopct=autopct_format(data), # Show percentage and count
                                      startangle=90, colors=final_colors,
                                      pctdistance=0.85) # Adjust distance of percentage text

    ax.set_title(title, pad=20)

    # Add a legend outside the pie chart
    ax.legend(wedges, labels,
              title="Categories",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1))

    plt.setp(autotexts, size=8, weight="bold", color="white") # Style percentage text
    fig.tight_layout()

    # Save to a BytesIO object
    img = BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight') # Use bbox_inches='tight'
    plt.close(fig) # Close the figure to free memory
    img.seek(0)

    # Encode in base64
    chart_base64 = base64.b64encode(img.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{chart_base64}"


# --- Date Range Handling for Queries ---
def get_utc_date_range(start_date_str, end_date_str):
    """Parses IST date strings and returns a UTC datetime range for querying."""
    try:
        # Parse date strings (assuming YYYY-MM-DD)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        # Localize to IST, assuming start of day for start_date and end of day for end_date
        start_dt_ist = IST.localize(datetime.combine(start_date, datetime.min.time()))
        # End of day is tricky, go to the *next* day and take the beginning
        end_dt_ist = IST.localize(datetime.combine(end_date + timedelta(days=1), datetime.min.time()))

        # Convert to UTC for MongoDB querying
        start_dt_utc = start_dt_ist.astimezone(UTC)
        end_dt_utc = end_dt_ist.astimezone(UTC)

        if start_dt_utc >= end_dt_utc:
            logger.warning("Start date is not before end date.")
            return None, None # Or raise error

        return start_dt_utc, end_dt_utc

    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Error processing date range: {e}")
        return None, None