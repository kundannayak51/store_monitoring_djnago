from datetime import datetime
from random import random

import pytz
from celery import shared_task
from django.db.models import Q

from monitor.constants import STATUS_COMPLETE, STATUS_NONE, STATUS_ACTIVE, STATUS_INACTIVE
from monitor.models import ReportStatus, StoreBusinessHours, StoreStatus
from monitor.utils import CURRENT_TIME, get_time_of_x_days_before, LOCAL_TIME_START, LOCAL_TIME_END, \
    convert_utc_to_local, get_day_mapping, check_time_lies_between_two_time, get_chunk_number_from_end


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

    for store_status in store_statuses:
        timestamp_utc = store_status['timestamp_utc']
        status = store_status['status']

        local_time, day_str = convert_utc_to_local(timestamp_utc, timezone)

        day = get_day_mapping(day_str)

        lies_between, ex = check_time_lies_between_two_time(day_time_mapping[day][0], day_time_mapping[day][1], local_time)

        if ex is not None:
            #log error and return

        if not lies_between:
            continue

        chunk_number = get_chunk_number_from_end(day_time_mapping[day][1], local_time)
        if chunk_number is -1:
            #log error and return
        status_map[day][chunk_number] = status

    status_map = enrich_status_map_with_nearest_status(status_map)

    #get today's day
    current_time_str = CURRENT_TIME
    current_time_local, day_str = convert_utc_to_local(current_time_str, timezone)
    day = get_day_mapping(day_str)




def create_weekly_observation(store_id, status_map, current_day):
    weekly_observation = []
    is_last_hour_active = False

    for key, val in status_map.items():
        total_chunks = len(val)
        active_status = 0

        for chunk, status in val.items():
            if status == STATUS_ACTIVE:
                active_status += 1
                if key == current_day and chunk == 0:
                    is_last_hour_active = True

        day_observation = {
            'day': key,
            'total_chunks': total_chunks,
            'active_chunks': active_status
        }
        weekly_observation.append(day_observation)

    return {
        'store_id': store_id,
        'week_report': weekly_observation,
        'is_last_hour_active': is_last_hour_active
    }


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


def enrich_status_map_with_nearest_status(status_map):
    result_map = {}
    for key, val in status_map.items():
        last_status = STATUS_INACTIVE
        rand_val = random.random()
        if rand_val >= 0.5:
            last_status = STATUS_ACTIVE
        last_status_index = 0
        count_active = 0
        count_inactive = 0
        temp_map = {}
        for i in range(len(val)):
            if val.get(i) == STATUS_INACTIVE:
                count_inactive += 1
            elif val.get(i) == STATUS_ACTIVE:
                count_active += 1

        if count_active == 0 and count_inactive == 0:
            for i in range(len(val)):
                rand_val = random.random()
                if rand_val >= 0.5:
                    temp_map[i] = STATUS_ACTIVE
                else:
                    temp_map[i] = STATUS_INACTIVE

        for i in range(len(val)):
            if val.get(i) != STATUS_NONE:
                last_status = val.get(i)
                last_status_index = i
                temp_map[i] = val.get(i)
            else:
                for j in range(i + 1, len(val)):
                    if j - i > i - last_status_index:
                        temp_map[i] = last_status
                        break
                    else:
                        if val.get(j) != STATUS_NONE:
                            if j - i == i - last_status_index:
                                if count_inactive > count_active:
                                    temp_map[i] = STATUS_INACTIVE
                                else:
                                    temp_map[i] = STATUS_ACTIVE
                                break
                            temp_map[i] = val.get(j)
                            break
                else:
                    if count_inactive > count_active:
                        temp_map[i] = STATUS_INACTIVE
                    else:
                        temp_map[i] = STATUS_ACTIVE
        result_map[key] = temp_map
    return result_map


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