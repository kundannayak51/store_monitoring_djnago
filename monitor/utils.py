import base64
import os
from datetime import datetime, timedelta

import pytz

CURRENT_TIME = "2023-01-25 18:13:22.47922 UTC"
LOCAL_TIME_START = "00:00:00"
LOCAL_TIME_END = "23:59:59"


def get_time_of_x_days_before(current_time, days):
    format_str = '%Y-%m-%d %H:%M:%S.%f %Z'
    given_time = datetime.strptime(current_time, format_str)

    x_days_ago = given_time - timedelta(days=days)

    return x_days_ago.strftime(format_str)

def generate_report_id():
    random_bytes = os.urandom(6)
    report_id = base64.urlsafe_b64encode(random_bytes).rstrip(b'=').decode('ascii')
    return report_id

def convert_utc_to_local(utc_time, timezone):
    try:
        # Load the specified timezone
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError as err:
        # Handle timezone loading errors
        return "", ""

    # Convert the UTC time to the specified timezone
    local_time = utc_time.astimezone(tz)

    # Determine the day of the week
    day = local_time.strftime("%A")

    return local_time.strftime("%H:%M:%S"), day