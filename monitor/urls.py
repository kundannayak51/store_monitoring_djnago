from django.urls import path

from .views import *
urlpatterns = [
    path('trigger_report', trigger_report),
    path('/get_report/:report_id', generate_csv_report)
]