import re
from typing import Type

from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from .models import Device, Stock, Comment, MechanicReport, KipReport, DeviceKipReport, Place, Station
from django.db.utils import IntegrityError
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError



def copy_fields(old_device, new_device):
    new_device.name = old_device.name
    new_device.stock = None
    new_device.status = new_device.get_status()
    new_device.save(update_fields=["name", "stock", "status"])


def send_to_stock(device_id):
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
    print(device, "отправлен на склад")


def defect_device_action(mechanic_report_id: int,
                         device: Device,
                         exchange_device: Device,
                         current_storage):
    current_storage.data.append(exchange_device)
    copy_fields(device, exchange_device)
    send_to_stock(exchange_device.id)
    MechanicReport.objects.get(
        pk=mechanic_report_id
    ).devices.remove(device)


def update_device(request, device_id):
    if request.method == "POST":
        exchange_device = None
        device = Device.objects.get(pk=device_id)
        mounting_address = device.mounting_address
        devices_on_place = mounting_address.device_set.all()
        for device_ in devices_on_place:
            if device_ == device:
                continue
            exchange_device = device_
        if exchange_device:
            copy_fields(device, exchange_device)
            send_to_stock(device.id)
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

            instance.device.status = Device.send
            instance.device.who_checked = instance.who_checked
            instance.device.who_prepared = instance.who_prepared
            instance.device.current_check_date = instance.check_date
            instance.device.next_check_date = instance.device.get_next_check_date()
            instance.device.save()

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
                            stations.setdefault(
                                this_place_other_device.station.pk, []
                            ).append(this_place_other_device)

            elif len(other_device_on_place) == 1:
                mech_device = list(other_device_on_place)[0]
                added_devices.append(mech_device)
                stations.setdefault(mech_device.station.pk, []).append(mech_device)
            else:
                print("Отлов NoneType в station: ", instance.device)
                added_devices.append(instance.device)
                stations.setdefault(instance.device.station.pk, []).append(instance.device)
            
            print(instance.device, instance.__dict__, sep="\n")

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


class DataStorage:
    instances = []

    def __init__(self, id_: int):
        self.id_ = id_
        self.data: list[Device] = []

    @classmethod
    def find_or_create(cls, id_: int):
        for instance in cls.instances:
            if instance.id_ == id_:
                instance_ = instance
                break
        else:
            instance_ = cls(id_)
            cls.instances.append(instance_)

        return instance_


def mark_defect_device(request, device_id):
    if request.method == "POST":
        mechanic_report_id = int(re.search(r"(?<=mechanicreport/)(\d+)(?=/change)",
                                           request.META.get("HTTP_REFERER")).group())
        current_storage: DataStorage = DataStorage.find_or_create(mechanic_report_id)
        try:
            kip_report_id = int(request.POST.get("kip_report_id"))
        except TypeError:
            return
        else:
            try:
                kip_report = KipReport.objects.get(pk=kip_report_id)
            except KipReport.DoesNotExist:
                return JsonResponse({"success": False,
                                     "message": f"Отчета КИП N {kip_report_id} не существует"})
            else:
                device = Device.objects.get(pk=device_id)
                if device.status == Device.send:
                    send_to_stock(device.id)
                else:
                    if device.avz:
                        
                        avz_devices = kip_report.devices.filter(
                            status=Device.send,
                            avz=device.avz,
                            device_type=device.device_type,
                        ).order_by("-next_check_date").exclude(
                            pk__in=[device.pk for device in current_storage.data]
                        )

                        print(avz_devices)

                        exchange_device = avz_devices.last()

                        if exchange_device:
                            defect_device_action(mechanic_report_id=mechanic_report_id,
                                                 device=device,
                                                 exchange_device=exchange_device,
                                                 current_storage=current_storage)
                            message = f"Прибор {exchange_device} отправлен обратно на склад"
                            return JsonResponse({"success": True,
                                                 "message": message})
                            
                        else:
                            return JsonResponse({"success": False,
                                                 "message": "Нет приборов, у которых можно отметить дефект"})
                        
                    elif device.mounting_address.number == "остальное":
                        kip_devices = kip_report.devices.filter(
                            Q(mounting_address__rack__number="поле") |
                            Q(mounting_address__rack__number="релейная") |
                            Q(mounting_address__rack__number="тоннель"),
                            station=device.station,
                            status=Device.send,
                            mounting_address=device.mounting_address,
                            device_type=device.device_type,
                        ).order_by("-next_check_date").exclude(
                            pk__in=[device.pk for device in current_storage.data]
                        )

                        exchange_device = kip_devices.last()
                        
                        if exchange_device:
                            defect_device_action(mechanic_report_id=mechanic_report_id,
                                                 device=device,
                                                 exchange_device=exchange_device,
                                                 current_storage=current_storage)
                            return JsonResponse({"success": True,
                                                 "message": f"Прибор {exchange_device} "
                                                            f"отправлен обратно на склад"})
                        else:
                            return JsonResponse({"success": False,
                                                 "message": "Нет приборов, у которых можно отметить дефект"})
                    else:
                        current_mounting_address = device.mounting_address
                        devices = current_mounting_address.device_set
                        if devices.count() > 2:
                            return JsonResponse({"success": False,
                                                "message": f"На адресе {current_mounting_address}"
                                                "больше двух приборов, проверьте"})
                        exchange_device = kip_report.devices.filter(
                            station=device.station,
                            mounting_address=device.mounting_address,
                            device_type=device.device_type,
                            status=Device.send,
                        )[0]
                        defect_device_action(exchange_device=exchange_device,
                                             device=device,
                                             mechanic_report_id=mechanic_report_id,
                                             current_storage=current_storage)
                        return JsonResponse({"success": True,
                                             "message": f"Прибор {exchange_device} "
                                                        f"отправлен обратно на склад"})
                        

    return JsonResponse({"success": True})
