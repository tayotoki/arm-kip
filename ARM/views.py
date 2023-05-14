from django.http import HttpResponseRedirect
from django.shortcuts import render
from .models import Device, Stock, Comment, MechanicReport, KipReport, DeviceKipReport, Place, Station
from django.db.utils import IntegrityError
from django.db.models import Q
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
    print("Пришло с запроса - kip_report_id=", kip_report_id)
    stations = {}
    other_places = Place.objects.filter(
        Q(rack__number="релейная") | Q(rack__number="тоннель") | Q(rack__number="поле"),
        number="остальное",
    )
    if request.method == "POST":
        messages.add_message(request, messages.WARNING, "Hello world.")
        kip_report = KipReport.objects.get(id=kip_report_id)
        kip_report_devices = kip_report.devices.through.objects.filter(kip_report=kip_report)
        added_devices = []

        print(kip_report.id, kip_report_devices, sep='\n')
        print("NNNNNNNNNNNNNNNN")

        for instance in kip_report_devices:

            if instance.device.avz:
                station_avz_devices = instance.device.avz.device_set.order_by(
                    "-next_check_date"
                ).filter(
                    ~Q(status__in=[Device.send, Device.in_progress]),
                    device_type=instance.device.device_type
                ).exclude(pk__in=[device.pk for device in kip_report.devices.all()] + 
                                 [device.pk for device in added_devices])

                if station_avz_devices:
                    mech_device = station_avz_devices.last()
                    added_devices.append(mech_device)
                    stations.setdefault(instance.device.station.pk, []).append(mech_device)
                else:
                    added_devices.append(instance.device)
                    stations.setdefault(instance.device.station.pk, []).append(instance.device)
                
                instance.device.status = Device.send
                instance.device.save()
                continue

            other_device_on_place = [device for device in Device.objects.filter(
                ~Q(pk=instance.device.pk),
                station=instance.device.station,
                mounting_address=instance.device.mounting_address
            )]

            print("----------")
            print(instance)
            print("~~~~~~~~")
            print(other_device_on_place)
            print("----------")

            if len(other_device_on_place) > 1:
                for current_place in other_places:
                    if instance.device.mounting_address == current_place:
                        this_place_other_device = [device for device in Device.objects.filter(
                            ~Q(status=Device.send),
                            ~Q(pk=instance.device.pk),
                            station=instance.device.station,
                            avz=instance.device.avz,
                            device_type=instance.device.device_type,
                            mounting_address=current_place,
                        ) if device not in added_devices][0]

                        if this_place_other_device:
                            added_devices.append(other_device_on_place)
                            stations.setdefault(this_place_other_device.station.pk, []).append(this_place_other_device)
            elif len(other_device_on_place) == 1:
                mech_device = list(other_device_on_place)[0]
                added_devices.append(mech_device)
                stations.setdefault(mech_device.station.pk, []).append(mech_device)
            else:
                print("Отлов NoneType в station: ", instance.device)
                added_devices.append(instance.device)
                stations.setdefault(instance.device.station.pk, []).append(instance.device)
            
            instance.device.status = Device.send
            instance.device.save()
        for station, devices in stations.items():
            if devices:
                MechanicReport.objects.create(
                    title=f"КИП N {kip_report_id} ({Station.objects.get(pk=station).__str__()})",
                    user=request.user,
                    station=Station.objects.get(pk=station),
                    explanation=f"Отправленный ящик из отчета КИП №{kip_report_id}. "
                                f"Сформированно автоматически"
                ).devices.set(Device.objects.filter(pk__in=[device.pk for device in devices]))
        print((stations))

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
