from django.contrib import admin
from django.core.exceptions import ValidationError
from django import forms
from django.forms import TextInput, Textarea, models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
#
# from import_export import resources
# from import_export.admin import ImportExportModelAdmin

from .models import Station, Device, Rack, Place, Stock, AVZ, MechanicReport
from ARM.actions import export_as_xls


admin.site.register(Rack)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    actions = [export_as_xls]
    list_filter = ["station", "stock", "contact_type", "next_check_date"]
    list_display = [
        "station",
        "name",
        "device_type",
        "inventory_number",
        "mounting_address",
        "avz",
        "status",
    ]
    list_display_links = list_display
    search_fields = ("name", "inventory_number")
    search_help_text = "Введите название прибора \
        или его инвентарный номер для поиска"


class AVZInlineAdmin(admin.StackedInline):
    model = AVZ
    fields = ('avz_link',)
    readonly_fields = fields
    can_delete = False
    extra = 0

    def avz_link(self, obj):
        return format_html('<a href="{0}">{1}</a>'.format(
            reverse('admin:ARM_avz_change', args=(obj.pk,)),
            obj.__str__()
        ))

    avz_link.short_description = "Ссылка"


class DevicesAdmin(admin.StackedInline):
    model = Device
    fields = ('device_link',)
    readonly_fields = fields
    can_delete = False
    extra = 0

    def device_link(self, obj):
        attr = f"{obj.name if obj.name else '--'} /"\
               f" {obj.inventory_number if obj.inventory_number else '--'} / "\
               f"{obj.get_status_display()}"

        return format_html('<a href="{0}">{1}</a>'.format(
            reverse('admin:ARM_device_change', args=(obj.pk,)),
            attr
        ))

    device_link.short_description = f"{Device._meta.get_field('name').verbose_name.title()}" \
                                    f"/{Device._meta.get_field('inventory_number').verbose_name.title()}" \
                                    f"/{Device._meta.get_field('status').verbose_name.title()}"
    device_link.admin_order_field = 'device_device_type'


@admin.register(AVZ)
class AVZAdmin(admin.ModelAdmin):
    inlines = [DevicesAdmin]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    inlines = [DevicesAdmin]


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    inlines = [AVZInlineAdmin, DevicesAdmin]
    readonly_fields = ('name',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    inlines = [DevicesAdmin]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

class MechanicReportForm(forms.ModelForm):
    def clean(self):
        devices = self.cleaned_data.get("devices")
        for device in devices:
            if device.station != self.cleaned_data.get("station"):
                raise ValidationError(f"Прибор {device.name} (тип: {device.device_type}) "
                                      f"(инв. номер: {device.inventory_number}) "
                                      f"не находится на станции {self.cleaned_data.get('station')}. "
                                      f"Возможно вы имели ввиду станцию {device.station.name}?")
        return super().clean()

@admin.register(MechanicReport)
class MechanicReportAdmin(admin.ModelAdmin):
    form = MechanicReportForm
    readonly_fields = ("created", "user", "modified")
    autocomplete_fields = ("devices",)
    list_display = (*readonly_fields, "title", "station")
    list_display_links = list_display
    search_fields = ("user__username", "station__name")
    search_help_text = ("Введите имя пользователя или станцию для поиска")

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        return super().save_model(request, obj, form, change)
