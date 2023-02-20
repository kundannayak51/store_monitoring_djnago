from datetime import datetime

import pytz
from celery import shared_task
from django.db.models import Q

from monitor.constants import STATUS_COMPLETE, STATUS_NONE
from monitor.models import ReportStatus, StoreBusinessHours, StoreStatus
from monitor.utils import CURRENT_TIME, get_time_of_x_days_before, LOCAL_TIME_START, LOCAL_TIME_END


@shared_task
def trigger_report_generation_for_each_store(report_id, stores_info):
    for store_id, timezone_str in stores_info:
        generate_and_store_report_for_store(report_id, store_id, timezone_str)

    err = update_report_status(report_id, STATUS_COMPLETE)
    if err is 1:
        #log error
        print("Error in updating report status to Completed")


def generate_and_store_report_for_store(report_id, store_id, timezone):
    end_time = CURRENT_TIME
    start_time = get_time_of_x_days_before(end_time, 7)

    business_hours = get_store_business_hours(store_id)

    business_hours, day_time_mapping = enrich_business_hour_and_return_day_time_mapping(store_id, business_hours)

    store_statuses = get_store_status_in_time_range(store_id, start_time, end_time)

def calculate_weekly_observation_and_generate_report(report_id, store_id, store_statuses, store_business_hours, timezone, day_time_mapping):
    status_map = {}

    for bh in store_business_hours:
        day_of_week = bh['day_of_week']
        start_time_local = bh['start_time_local']
        end_time_local = bh['end_time_local']

        total_hour_chunks = calculate_total_chunks(start_time_local, end_time_local)

        hour_status = {}
        for i in range(total_hour_chunks):
            hour_status[i] = STATUS_NONE
        status_map[day_of_week] = hour_status


def enrich_business_hour_and_return_day_time_mapping(store_id, business_hours):
    day_time_mapping = {}
    days_present = {}

    for bh in business_hours:
        day_of_week = bh['day_of_week']
        start_time_local = bh['start_time_local']
        end_time_local = bh['end_time_local']

        days_present[day_of_week] = True
        day_time_mapping[day_of_week] = (start_time_local, end_time_local)

    for i in range(7):
        if i not in days_present:
            new_business_hour = {
                'store_id': store_id,
                'day_of_week': i,
                'start_time_local': LOCAL_TIME_START,
                'end_time_local': LOCAL_TIME_END
            }
            business_hours.append(new_business_hour)
            day_time_mapping[i] = (LOCAL_TIME_START, LOCAL_TIME_END)

    return business_hours, day_time_mapping

def get_store_business_hours(store_id):
    business_hours = StoreBusinessHours.objects.filter(store_id=store_id)

    return list(business_hours.values('store_id', 'day_of_week', 'start_time_local', 'end_time_local'))

def calculate_total_chunks(start_time_str, end_time_str):
    start_time = datetime.strptime(start_time_str, '%H:%M:%S')
    end_time = datetime.strptime(end_time_str, '%H:%M:%S')

    duration = end_time - start_time
    total_minutes = int(duration.total_seconds() // 60)

    if total_minutes % 60 == 0:
        return total_minutes // 60
    else:
        return total_minutes // 60 + 1

def get_store_status_in_time_range(store_id, start_time_str, end_time_str):
    start_time = datetime.fromisoformat(start_time_str).astimezone(pytz.UTC)
    end_time = datetime.fromisoformat(end_time_str).astimezone(pytz.UTC)

    store_statuses = StoreStatus.objects.filter(
        Q(store_id=store_id),
        Q(timestamp_utc__gte=start_time),
        Q(timestamp_utc__lt=end_time)
    ).values('id', 'store_id', 'timestamp_utc', 'status')

    return list(store_statuses)

def update_report_status(report_id, status):
    try:
        report_status = ReportStatus.objects.get(report_id=report_id)
        report_status.status = status
        report_status.save()
        return 0
    except ReportStatus.DoesNotExist:
        return 1