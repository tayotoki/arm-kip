from django.http import HttpResponseRedirect
from django.shortcuts import render
from .models import Device, Stock, Comment, MechanicReport, KipReport, DeviceKipReport
from django.db.utils import IntegrityError
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


def update_device(request, device_id):
    if request.method == "POST":
        device_id = device_id
        device = Device.objects.get(id=device_id)
        device.name = None
        device.current_check_date = None
        device.next_check_date = None
        device.status = None
        device.station = None
        device.avz = None
        device.who_prepared = None
        device.who_checked = None
        device.stock = Stock.objects.get(pk=1)
        device.mounting_address = None
        device.save(update_fields=[
            "name",
            "current_check_date",
            "next_check_date",
            "status",
            "station",
            "avz",
            "who_prepared",
            "who_checked",
            "stock",
            "mounting_address",
        ])
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def create_comment(request, mech_report_id):
    if request.method == "POST":
        if request.POST.get("text"):
            Comment.objects.create(
                author=request.user,
                text=request.POST.get("text"),
                mech_report=MechanicReport.objects.get(id=mech_report_id),
            )
        else:
            raise ValidationError("Пустой комментарий")
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def create_mech_reports(request, kip_report_id):
    if request.method == "POST":
        messages.add_message(request, messages.WARNING, "Hello world.")
        kip_report = KipReport.objects.get(id=kip_report_id)
        for field in kip_report.devices.through.objects.all():
            print(field)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))