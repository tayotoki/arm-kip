from django_cron import CronJobBase, Schedule
from django.db.models import Q
from .models import Device


class UpdateDeviceStatuses(CronJobBase):
    devices = []

    RUN_EVERY_MINS = 1

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'ARM.update_device_statuses'

    def do(self):
        devices = Device.objects.filter(
            ~(Q(status=Device.send) | Q(status=Device.in_progress)),
            stock__isnull=True,
            next_check_date__isnull=False,
        )

        for device in devices:
            if device.next_check_date:
                device.status = device.get_status()

        Device.objects.bulk_update(devices, fields=["status"])