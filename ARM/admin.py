from django.contrib import admin
from django.core.exceptions import ValidationError
from django import forms
from django.forms import TextInput, Textarea, models, widgets, HiddenInput
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from datetime import date
#
# from import_export import resources
# from import_export.admin import ImportExportModelAdmin

from .models import Station, Device, Rack, Place, Stock, AVZ, MechanicReport, Tipe, Comment
from ARM.actions import export_as_xls


@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    list_filter = ["station"]
    search_fields = ("number", )


class DeviceForm(forms.ModelForm):
    model = Device

    def clean_inventory_number(self):
        inventory_number = self.cleaned_data.get("inventory_number")
        if inventory_number:
            if not inventory_number.isnumeric():
                raise ValidationError("Инвентарный номер должен состоять из цифр."
                                      " Если у прибора нет инв. номера, оставьте поле пустым")
        return inventory_number


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    form = DeviceForm
    readonly_fields = ("next_check_date",)
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
    autocomplete_fields = ("mounting_address", "device_type")
    list_display_links = list_display
    search_fields = ("name", "inventory_number")
    search_help_text = "Введите название прибора \
        или его инвентарный номер для поиска"

    def save_model(self, request, obj, form, change):
        check_date = form.cleaned_data["current_check_date"]
        year = check_date.year + obj.frequency_of_check
        obj.next_check_date = date(year=year, month=check_date.month, day=check_date.day)
        return super().save_model(request, obj, form, change)


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
    search_fields = ("rack__number",)
    autocomplete_fields = ("rack",)


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
                                      f"не находится на станции " 
                                      f"{(self.cleaned_data.get('station') if self.cleaned_data.get('station') else '')}. "
                                      f"Возможно вы имели ввиду станцию {device.station}?")
        return super().clean()


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("__str__", "author", "mech_report", "published")
    readonly_fields = ("author", "published")
    fields = ("text", *readonly_fields)

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return request.user == obj.author
        return False

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        return super().save_model(request, obj, form, change)


class ReportCommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ("text", "author", "published")
    readonly_fields = ("published",)
    can_delete = False
    show_change_link = True

    def has_change_permission(self, request, obj=None):
        return False
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj=obj, **kwargs)
        form = formset.form

        class CommentForm(form):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields["author"].initial = request.user
                self.fields["author"].widget = widgets.HiddenInput()
                
        formset.form = CommentForm
        return formset


@admin.register(MechanicReport)
class MechanicReportAdmin(admin.ModelAdmin):
    inlines = [ReportCommentInline]
    form = MechanicReportForm
    readonly_fields = ("devices_links", "user", "created", "modified")
    autocomplete_fields = ("devices",)
    list_display = ("__str__", "title", "station", *readonly_fields)
    list_display_links = list_display
    search_fields = ("user__username", "station__name")
    search_help_text = ("Введите имя пользователя или станцию для поиска")

    def devices_links(self, obj):
        count = obj.devices.count()
        url = (
            reverse("admin:ARM_device_changelist")
            + "?"
            + urlencode({"devices": f"{obj.devices}"})
        )
        return format_html('<a href="{}">Приборы ({} шт.)</a>', url, count)

    devices_links.short_description = "Ссылка на приборы"

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        return super().save_model(request, obj, form, change)


@admin.register(Tipe)
class TipeAdmin(admin.ModelAdmin):
    search_fields = ("name",)
