from django.urls import path
from . import views


urlpatterns = [
    path("device/update/<int:device_id>/", views.update_device, name="update_device"),
    path("comment/create/<int:mech_report_id>/", views.create_comment, name="create_comment")
]