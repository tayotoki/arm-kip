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


class Report:
    def __init__(self, model):
        self.model = model

    def __set_name__(self, owner, name):
        self.name = "_" + name

    def __get__(self, obj, objtype=None):
        return getattr(obj, self.name)

    def __set__(self, obj, value):
        setattr(
            obj,
            self.name,
            self.get_object_or_none(value),
        )

    def get_object_or_none(self, value):
        try:
            return self.model.objects.get(pk=value)
        except self.model.DoesNotExist:
            return None


class KipMechReportAdapter:
    """Класс для работы с объектами модели
    Device, которые присутствуют в MechanicReport
    и KipReport"""
    mech_report = Report(model=MechanicReport)
    kip_report = Report(model=KipReport)

    def __init__(self,
                 mech_report_id: int,
                 kip_report_id: int,
                 storage: DataStorage):
        self.mech_report = mech_report_id
        self.kip_report = kip_report_id
        self.storage = storage

    @staticmethod
    def _copy_fields(old_device: Device,
                     new_device: Device):
        new_device.name = old_device.name
        new_device.stock = None
        new_device.status = new_device.get_status()
        new_device.save(update_fields=[
            "name",
            "stock",
            "status",
        ])

    @staticmethod
    def _send_to_stock(device_id: int):
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

    def _defect_device_actions(self,
                               device: Device,
                               exchange_device: Device):
        self.storage.data.append(exchange_device)
        self._copy_fields(device, exchange_device)
        self._send_to_stock(exchange_device.id)
        self.mech_report.devices.remove(device)

    def find_avz_exchange_device(self, device: Device) -> Device | None:
        """Возвращает прибор для замены или None, в случае когда
        прибор находится в аварийно-восстановительном запасе"""

        avz_devices = self.kip_report.devices.filter(
            status=Device.send,
            avz=device.avz,
            device_type=device.device_type,
        ).order_by("-next_check_date").exclude(
            pk__in=[device.pk for device in self.storage.data]
        )

        exchange_device = avz_devices.last()

        return exchange_device if exchange_device else None

    def find_other_places_exchange_device(self, device: Device) -> Device | None:
        """Возвращает прибор для замены или None, в случае если
        монтажный адрес определен как ...-остальное"""

        kip_devices = self.kip_report.devices.filter(
            Q(mounting_address__rack__number="поле") |
            Q(mounting_address__rack__number="релейная") |
            Q(mounting_address__rack__number="тоннель") & Q(
                station=device.station,
                status=Device.send,
                mounting_address=device.mounting_address,
                device_type=device.device_type,
        )).order_by("-next_check_date").exclude(
            pk__in=[device.pk for device in self.storage.data]
        )

        exchange_device = kip_devices.last()

        return exchange_device if exchange_device else None

    def find_exact_mount_addr_exch_device(self, device: Device) -> Device:
        """Возвращает прибор для замены, в случае если
        монтажный адрес - точное место на стативе станции"""

        current_mounting_address = device.mounting_address
        devices = current_mounting_address.device_set

        if devices.count() > 2:
            raise ValueError(f"К адресу {current_mounting_address} относится"
                             "больше двух приборов, "
                             "проверьте данное место "
                             "в разделе Места")

        exchange_device = self.kip_report.devices.filter(
            station=device.station,
            mounting_address=device.mounting_address,
            device_type=device.device_type,
            status=Device.send,
        )[0]

        return exchange_device

    def swap_devices(self, device: Device, exchange_device: Device):
        self.storage.data.append(exchange_device)
        self._copy_fields(device, exchange_device)
        self._send_to_stock(device.id)

    def install_device(self, device: Device):
        device.stock = None
        device.status = device.get_status()
        device.save(update_fields=[
            "status",
            "stock",
        ])
        self.storage.data.append(device)


def update_device(request, device_id):
    if request.method == "POST":
        mechanic_report_id = int(
            re.search(r"(?<=mechanicreport/)(\d+)(?=/change)",
                      request.META.get("HTTP_REFERER")).group()
        )
        current_storage: DataStorage = DataStorage.find_or_create(mechanic_report_id)

        try:
            kip_report_id = int(request.POST.get("kip_report_id"))
        except TypeError:
            return
        else:
            adapter = KipMechReportAdapter(mech_report_id=mechanic_report_id,
                                           kip_report_id=kip_report_id,
                                           storage=current_storage)
            if not adapter.kip_report:
                return JsonResponse({"success": False,
                                     "message": f"Отчета КИП N {kip_report_id} не существует"})
            else:
                device = Device.objects.get(pk=device_id)
                if device.status == Device.send:
                    adapter.install_device(device)
                    message = f"{device} установлен на {device.mounting_address}"
                    return JsonResponse({"success": True,
                                         "message": message})
                else:
                    if device.avz:
                        exchange_device = adapter.find_avz_exchange_device(device)

                        if exchange_device:
                            adapter.swap_devices(device=device,
                                                 exchange_device=exchange_device)
                            message = f"Прибор {device} заменен на {exchange_device}"
                            return JsonResponse({"success": True,
                                                 "message": message})
                        else:
                            return JsonResponse({"success": False,
                                                 "message": "Нет приборов для замены"})

                    elif device.mounting_address.number == "остальное":
                        exchange_device = adapter.find_other_places_exchange_device(device)

                        if exchange_device:
                            adapter.swap_devices(device=device,
                                                 exchange_device=exchange_device)
                            message = f"Прибор {device} заменен на {exchange_device}"
                            return JsonResponse({"success": True,
                                                 "message": message})
                        else:
                            return JsonResponse({"success": False,
                                                 "message": "Нет приборов для замены"})
                    else:
                        try:
                            exchange_device = adapter.find_exact_mount_addr_exch_device(device)
                        except ValueError as e:
                            return JsonResponse({"success": False,
                                                 "message": f"{e}"})
                        else:
                            adapter.swap_devices(device=device,
                                                 exchange_device=exchange_device)

                            message = f"Прибор {device} заменен на {exchange_device}"
                            return JsonResponse({"success": True,
                                                 "message": message})
    return JsonResponse({"success": True})


def create_comment(request, mech_report_id):
    if request.method == "POST":
        if text := request.POST.get("text"):
            Comment.objects.create(
                author=request.user,
                text=text,
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
                mounting_address=instance.device.mounting_address,
                device_type=instance.device.device_type,
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
        kip_report.editable = False
        kip_report.save()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def mark_defect_device(request, device_id):
    if request.method == "POST":
        mechanic_report_id = int(
            re.search(r"(?<=mechanicreport/)(\d+)(?=/change)",
                      request.META.get("HTTP_REFERER")).group()
        )
        current_storage: DataStorage = DataStorage.find_or_create(mechanic_report_id)

        try:
            kip_report_id = int(request.POST.get("kip_report_id"))
        except TypeError:
            return
        else:
            adapter = KipMechReportAdapter(mech_report_id=mechanic_report_id,
                                           kip_report_id=kip_report_id,
                                           storage=current_storage)
            if not adapter.kip_report:
                return JsonResponse({"success": False,
                                     "message": f"Отчета КИП N {kip_report_id} не существует"})
            else:
                device = Device.objects.get(pk=device_id)
                if device.status == Device.send:
                    adapter._send_to_stock(device.id)
                else:
                    if device.avz:
                        exchange_device = adapter.find_avz_exchange_device(device)

                        if exchange_device:
                            adapter._defect_device_actions(device=device,
                                                           exchange_device=exchange_device)
                            message = f"Прибор {exchange_device} отправлен обратно на склад"
                            return JsonResponse({"success": True,
                                                 "message": message})
                        else:
                            return JsonResponse({"success": False,
                                                 "message": "Нет приборов, "
                                                            "у которых можно отметить дефект"})

                    elif device.mounting_address.number == "остальное":
                        exchange_device = adapter.find_other_places_exchange_device(device)

                        if exchange_device:
                            adapter._defect_device_actions(device=device,
                                                           exchange_device=exchange_device)
                            return JsonResponse({"success": True,
                                                 "message": f"Прибор {exchange_device} "
                                                            f"отправлен обратно на склад"})
                        else:
                            return JsonResponse({"success": False,
                                                 "message": "Нет приборов, у которых можно отметить дефект"})
                    else:
                        try:
                            exchange_device = adapter.find_exact_mount_addr_exch_device(device)
                        except ValueError as e:
                            return JsonResponse({"success": False,
                                                 "message": f"{e}"})
                        else:
                            adapter._defect_device_actions(device=device,
                                                           exchange_device=exchange_device)

                            return JsonResponse({"success": True,
                                                 "message": f"Прибор {exchange_device} "
                                                            f"отправлен обратно на склад"})
    return JsonResponse({"success": True})
