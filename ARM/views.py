from django.http import HttpResponseRedirect
from django.shortcuts import render
from .models import Device, Stock
from django.db.utils import IntegrityError


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
