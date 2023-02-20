from rest_framework.decorators import api_view
from rest_framework.response import Response

from monitor.constants import STATUS_RUNNING
from monitor.models import Store, ReportStatus
from monitor.utils import generate_report_id

from .tasks import trigger_report_generation_for_each_store


@api_view(['POST'])
def trigger_report(request):
    all_store_info = get_all_stores()
    report_id = generate_report_id()

    report_status = ReportStatus(report_id=report_id, status=STATUS_RUNNING)
    report_status.save()

    trigger_report_generation_for_each_store.apply_async(report_id, all_store_info)

    return Response({"report_id": report_id})

def get_all_stores():
    stores = Store.objects.all().values('store_id', 'timezone_str')
    store_info = [(store['store_id'], store['timezone_str']) for store in stores]
    return store_info
