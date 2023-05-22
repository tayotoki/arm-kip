from django.urls import path
from . import views


urlpatterns = [
    path("device/update/<int:device_id>/", views.update_device, name="update_device"),
    path("comment/create/<int:mech_report_id>/", views.create_comment, name="create_comment"),
    path("mechanicreport/create/<int:kip_report_id>/", views.create_mech_reports, name="create_mech_reports"),
    path("device/defect/<int:device_id>/", views.mark_defect_device, name="mark_defect_device"),
]