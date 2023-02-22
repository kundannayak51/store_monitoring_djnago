import base64
import os
from datetime import datetime, timedelta, time

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

def get_day_mapping(day):
    if day == "Monday":
        return 0
    elif day == "Tuesday":
        return 1
    elif day == "Wednesday":
        return 2
    elif day == "Thursday":
        return 3
    elif day == "Friday":
        return 4
    elif day == "Saturday":
        return 5
    elif day == "Sunday":
        return 6
    else:
        return -1

def check_time_lies_between_two_time(start_time_str, end_time_str, local_time_str, timezone):
    try:
        # Load the timezone
        loc = time.timezone(timezone)
    except Exception as e:
        # Log error
        return False, e

    # Parse the start, end, and local time
    start_time = time.strptime(start_time_str, "%H:%M:%S")
    end_time = time.strptime(end_time_str, "%H:%M:%S")
    local_time = time.strptime(local_time_str, "%H:%M:%S")

    # Extract the hour, minute, and second from the times
    local_hour, local_minute, local_second = local_time.tm_hour, local_time.tm_min, local_time.tm_sec
    start_hour, start_minute, start_second = start_time.tm_hour, start_time.tm_min, start_time.tm_sec
    end_hour, end_minute, end_second = end_time.tm_hour, end_time.tm_min, end_time.tm_sec

    if local_hour >= start_hour and local_hour <= end_hour and \
            ((local_hour > start_hour or (local_hour == start_hour and local_minute >= start_minute and local_second >= start_second)) and
             (local_hour < end_hour or (local_hour == end_hour and local_minute <= end_minute and local_second <= end_second))):
        return True, None

    return False, None

def get_chunk_number_from_end(end_time_str, input_time_str):
    try:
        input_time = datetime.datetime.strptime(input_time_str, '%H:%M:%S')
        end_time = datetime.datetime.strptime(end_time_str, '%H:%M:%S')
        minutes = int((end_time - input_time).total_seconds() / 60)
        chunk = minutes // 60
        return chunk
    except ValueError:
        return -1