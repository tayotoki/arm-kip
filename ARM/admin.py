import re

from functools import reduce
from operator import or_, and_
from typing import Optional

from django.contrib import messages
from django.contrib.admin import AdminSite
from django.db.models import Q
from django.contrib import admin
from django.core.exceptions import ValidationError
from django import forms
from django.forms import TextInput, Textarea, models, widgets, HiddenInput
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from datetime import date
from django.utils.datetime_safe import strftime

from .models import (Station,
                     Device,
                     Rack,
                     Place,
                     Stock,
                     AVZ,
                     MechanicReport,
                     Tipe,
                     Comment,
                     KipReport,
                     DeviceKipReport)

from ARM.actions import export_as_xls, add_to_kipreport


AdminSite.site_url = ''
AdminSite.empty_value_display = '--'


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
    actions = [export_as_xls, add_to_kipreport]
    list_filter = ["station", "stock", "status", "contact_type", "next_check_date"]
    list_display = [
        "station",
        "name",
        "device_type",
        "inventory_number",
        "mounting_address",
        "avz",
        "next_check_date",
        "status",
    ]
    autocomplete_fields = ("mounting_address", "device_type")
    list_display_links = list_display
    search_fields = ("name", "inventory_number", "device_type__name")
    search_help_text = "Введите название прибора \
        или его инвентарный номер для поиска"

    def save_model(self, request, obj, form, change):
        check_date = form.cleaned_data["current_check_date"]
        if check_date:
            year = check_date.year + obj.frequency_of_check
            obj.next_check_date = date(year=year, month=check_date.month, day=check_date.day)
            obj.status = obj.get_status()
            print(obj.status, obj.get_status(), obj.next_check_date)
        change = True
        return super().save_model(request, obj, form, change)

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, search_term
        )
        if search_term:
            queryset |= self.model.objects.filter(
                Q(name__iregex=search_term) | Q(inventory_number__iregex=search_term) | Q(device_type__name__iregex=search_term)
            )
            
        return queryset, may_have_duplicates


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
    empty_value_display = "--"

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
    search_fields = ("rack__number", "number")
    autocomplete_fields = ("rack",)
    list_filter = ("rack__station",)

    def get_search_results(self, request, queryset, search_term):
        orig_queryset = queryset
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        search_words = search_term.split("-")
        if search_words:
            if len(search_words) == 2:
                q_objects = [
                    Q(**{field + "__exact": word})
                    for field, word in {self.search_fields[0]: search_words[0],
                                        self.search_fields[1]: search_words[1]}.items()
                ]
                queryset |= self.model.objects.filter(reduce(and_, q_objects))
            else:
                q_objects = [
                    Q(**{field + "__icontains": word})
                    for field in self.search_fields
                    for word in search_words
                ]
                queryset |= self.model.objects.filter(reduce(or_, q_objects))

        queryset = queryset & orig_queryset

        return queryset, use_distinct


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
        if devices:
            for device in devices:
                if not device.station:
                    raise ValidationError(f"Прибор {device.__str__()} скорее всего на складе.")
                if device.station != self.cleaned_data.get("station"):
                    raise ValidationError(f"Прибор {device.name} (тип: {device.device_type}) "
                                          f"(инв. номер: {device.inventory_number}) "
                                          f"не находится на станции " 
                                          f"{(self.cleaned_data.get('station') if self.cleaned_data.get('station') else '')}. "
                                          f"Возможно вы имели ввиду станцию {device.station}?")
        return super().clean()


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "get_short_text", "report_link", "published")
    readonly_fields = ("author", "get_short_text", "published")
    fields = ("text", readonly_fields[0], readonly_fields[2])

    def get_short_text(self, obj):
        return obj.text[:10]

    def report_link(self, obj):
        obj = obj.mech_report
        return format_html('<a href="{0}">{1}</a>'.format(
            reverse('admin:ARM_mechanicreport_change', args=(obj.pk,)),
            obj
        ))

    get_short_text.short_description = "Комментарий"
    report_link.short_description = "Ссылка на отчет"

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return request.user == obj.author
        return False

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        return super().save_model(request, obj, form, change)


class ReportCommentInline(admin.StackedInline):
    model = Comment
    extra = 1
    fields = ("text", "author", "published", "published_but")
    readonly_fields = ("published", "published_but")
    can_delete = False
    show_change_link = True
    widgets = {
        "text": Textarea(attrs={
            "cols": 80,
            "rows": 10,
            "id": "comment_text"
        })
    }

    def published_but(self, obj):
        if obj.id:
            return obj.author.username.upper()
        mech_report_id = obj.mech_report.id
        return mark_safe(
            f'<a class="button" href="javascript://" '
            f'onclick="create_comment_ajax({mech_report_id})">Опубликовать</a>'
        )

    published_but.short_description = ""
    published_but.allow_tags = True

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

    class Media:
        js = ["admin/js/create_comment_ajax.js"]


class DevicesReportInline(admin.TabularInline):
    model = MechanicReport.devices.through
    extra = 0
    readonly_fields = ("button", "defect_button", "get_status", "get_current_date", "get_next_date")
    verbose_name_plural = "Приборы в отчете"
    verbose_name = "Прибор"

    def button(self, obj):
        device = Device.objects.get(id=obj.device_id)
        print(device.status, device.stock)
        if (device.station or device.avz) and device.status not in (Device.send, Device.normal):
            return mark_safe(
                f'<a class="button" href="javascript://" '
                f'onclick="update_device_ajax({device.id})">Прибор заменен</a>'
            )
        elif device.status == Device.send:
            return mark_safe(
                f'<a class="button" href="javascript://" '
                f'onclick="update_device_ajax({device.id})">Прибор установлен</a>'
            )
        elif device.stock and not device.station:
            return "Прибор на складе"
        elif device.stock is None:
            return f"{device.status}"

    @admin.display(description="Отметить дефекты")
    def defect_button(self, obj):
        device = Device.objects.get(id=obj.device_id)
        return mark_safe(
            f'<a class="button" href="javascript://" '
            f'onclick="mark_defect_device_ajax({device.id})">Есть дефекты</a>'
        )

    def get_current_date(self, obj):
        date = Device.objects.get(id=obj.device_id).current_check_date.strftime("%d.%m.%Y")
        return date

    def get_next_date(self, obj):
        date = Device.objects.get(id=obj.device_id).next_check_date.strftime("%d.%m.%Y")
        return date

    def get_status(self, obj):
        status = Device.objects.get(id=obj.device_id).status
        if status:
            return status
        return AdminSite.empty_value_display

    button.short_description = "отметить замену прибора"
    get_status.short_description = "статус"
    get_current_date.short_description = "дата проверки"
    get_next_date.short_description = "дата замены"

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        js = ["admin/js/update_device_ajax.js",
              "admin/js/mark_defect_device_ajax.js"]


@admin.register(MechanicReport)
class MechanicReportAdmin(admin.ModelAdmin):
    inlines = [DevicesReportInline, ReportCommentInline]
    form = MechanicReportForm
    readonly_fields = ("user", "created", "modified")
    autocomplete_fields = ("devices",)
    list_display = ("__str__", "title", "station", *readonly_fields, "devices_l")
    list_display_links = list_display
    search_fields = ("user__username", "station__name")
    search_help_text = ("Введите имя пользователя или станцию для поиска")

    def devices_l(self, obj):
        device_changelist_url = reverse("admin:ARM_device_changelist")
        device_links = [f'<a href="{device_changelist_url}?id={d.id}">{d}</a>' for d in obj.devices.all()]
        return format_html(' || '.join(device_links))

    devices_l.short_description = "Приборы в отчете"

    def save_model(self, request, obj, form, change):
        if change:
            return super().save_model(request, obj, form, change)
        obj.user = request.user
        return super().save_model(request, obj, form, change)


@admin.register(Tipe)
class TipeAdmin(admin.ModelAdmin):
    search_fields = ("name",)

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, search_term
        )
        if search_term:
            queryset |= self.model.objects.filter(name__iregex=search_term)
        return queryset, may_have_duplicates


class DeviceKipReportForm(forms.ModelForm):
    devices_ids = set()

    def __new__(cls, *args, **kwargs):
        cls.devices_ids.clear()
        return super().__new__(cls)

    def clean_device(self):
        device = self.cleaned_data.get("device")

        if device:
            if device.id in self.devices_ids:
                raise ValidationError("Этот прибор уже добавлен выше")
            self.devices_ids.add(device.id)

            if device.stock is None:
                raise ValidationError("Вы выбрали прибор со станции, а не со склада, "
                                      "У приборов на складе нет названия и монтажного адреса")
        return device

    def clean_mounting_address(self):
        mounting_address = self.cleaned_data.get("mounting_address")
        
        if mounting_address:
            if "шт" in mounting_address.lower():
                if re.search(r"(\d+)", mounting_address) is None:
                    raise ValidationError("Укажите корректное количество аппаратуры")
            elif "-" not in mounting_address and not mounting_address.lower() == "авз":
                raise ValidationError("Вы ввели некорректный монтажный адрес, "
                                    "принимаются данные ввиде ссс-ммм"
                                    ", где ссс - номер статива, ммм - номер места на стативе"
                                    ". Например 27-712, 110-811, ПВ1-51, тоннель-стрелка №1")
        return mounting_address

    def clean(self):
        if not all((
            self.cleaned_data.get("device"),
            self.cleaned_data.get("mounting_address"),
            self.cleaned_data.get("station"),
        )):
            raise ValidationError("Не все обязательные поля заполнены")
        
        other_places = Place.objects.filter(
            Q(rack__number="релейная") | Q(rack__number="тоннель") | Q(rack__number="поле"),
            number="остальное",
        )
        
        device = self.cleaned_data.get("device")
        station = self.cleaned_data.get("station")
        mounting_address = self.cleaned_data.get("mounting_address")
        kip_report = self.cleaned_data["kip_report"]
        
        if all((
            (duplicate_devices := DeviceKipReport.objects.filter(
                ~Q(device=device),
                station=station,
                mounting_address=mounting_address,
            )).count() >= 1,
            mounting_address not in (f"{place.rack.number}-{place.number}" for place in other_places),
            mounting_address.lower() != "авз",
        )):
            raise ValidationError(f"На это место уже готовится прибор "
                                  f"{duplicate_devices.first().device.inventory_number} "
                                  f"({duplicate_devices.first().device.device_type})"
                                  f" в отчете {duplicate_devices.first().kip_report}")

        if station and mounting_address:
            if mounting_address.lower() == "авз":
                try:
                    devices_in_avz = AVZ.objects.get(station=station).device_set.all()
                except AVZ.DoesNotExist:
                    raise ValidationError("Такого АВЗ не существует")
                else:
                    for avz_device in devices_in_avz:
                        if device.device_type == avz_device.device_type:
                            break
                    else:
                        raise ValidationError(f"Приборов типа {device.device_type} нет в АВЗ "
                                              f"станции {station.__str__()}")
            elif re.fullmatch(r"(\d+)-(\d+)", mounting_address):
                rack, number = mounting_address.strip().split("-")

                try:
                    existing_rack = Rack.objects.get(station=station, number=rack)
                except Rack.DoesNotExist:
                    raise ValidationError(f"Статива {rack} нет на станции {station}. "
                                          f"Возможные стативы "
                                          f"{sorted([rack.number for rack in station.rack_set.all()])}")
                else:
                    try:
                        existing_place = Place.objects.get(rack=existing_rack, number=number)
                    except Place.DoesNotExist:
                        raise ValidationError(f"Места {number} нет на стативе {rack} станции {station}\n."
                                              f" Возможные места "
                                              f"{sorted([obj.number for obj in list(existing_rack.place_set.all())])}")
                    else:
                        try:
                            device_on_this_place = Device.objects.get(mounting_address=existing_place)
                        except Device.DoesNotExist:
                            pass
                        except Device.MultipleObjectsReturned:
                            if existing_place in other_places:
                                pass
                            else:
                                raise ValidationError(f"К месту {existing_place} "
                                                      f"станции {station} "
                                                      f" уже относятся 2 прибора")
                        else:
                            if device.device_type != device_on_this_place.device_type:
                                raise ValidationError(f"Прибор на месте {existing_place.__str__()} "
                                                      f"{device_on_this_place.name} имеет тип " 
                                                      f"{device_on_this_place.device_type}. "
                                                      f"Прибор в ящике - {device.device_type}")
        return super().clean()


class DeviceKipReportInline(admin.StackedInline):
    model = DeviceKipReport
    form = DeviceKipReportForm
    extra = 0
    autocomplete_fields = ["device"]
    readonly_fields = ("get_status",)
    fields = (("device", "station", "mounting_address"), "check_date", ("who_prepared", "who_checked"), "get_status")
    verbose_name = "прибор в ящик"
    verbose_name_plural = "Собрать виртуальный ящик"

    @admin.display(description="Статус")
    def get_status(self, obj):
        status = Device.objects.get(id=obj.device_id).status
        if status:
            return status
        return AdminSite.empty_value_display


@admin.register(KipReport)
class KipReportAdmin(admin.ModelAdmin):
    inlines = [DeviceKipReportInline]
    readonly_fields = ("author", "button", "created")
    exclude = ("editable",)

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        if obj:
            return obj.editable

    @admin.display(description="Действия")
    def button(self, obj):
        kip_report = KipReport.objects.get(id=obj.id)
        if all([device.status == Device.in_progress for device in kip_report.devices.all()]):
            return mark_safe(
                f'<a class="button" href="javascript://" '
                f'onclick="send_devices_ajax({kip_report.id})">Отправить приборы</a>'
            )
        elif all(
            [device.status == Device.send for device in kip_report.devices.all()]
        ) or not obj.editable:
            return "Приборы отправлены"
        else:
            return "Приборы еще не подготовлены к отправке"
        
    class Media:
        js = ["admin/js/send_devices_ajax.js"]

    def save_model(self, request, obj, form, change):
        if change:
            return super().save_model(request, obj, form, change)
        obj.author = request.user
        return super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        other_places = Place.objects.filter(
            Q(rack__number="релейная") | Q(rack__number="тоннель") | Q(rack__number="поле"),
            number="остальное",
        )
        instances = formset.save(commit=False)
        kip_report = form.instance
        for instance in instances:
            print(instance.mounting_address)
            form_device = Device.objects.get(pk=instance.device.pk)
            avz = AVZ.objects.get(station=instance.station)
            avz_true = False

            if instance.mounting_address.lower() == "авз":
                avz_true = True
                form_device.avz = avz
                form_device.status = form_device.in_progress
                form_device.station = instance.station
                print(form_device.name, form_device.avz)

            elif "шт" in instance.mounting_address.lower():
                devices_number = int(
                    re.search(
                        r"(\d+)",
                        instance.mounting_address,
                    ).group()
                )

                this_type_devices = Device.objects.filter(
                    ~Q(pk=form_device.pk),
                    device_type=form_device.device_type,
                    stock__id=1,
                )[:devices_number - 1]

                update_devices = Device.objects.filter(pk__in=[device.pk for device in this_type_devices]).update(
                        station=form_device.station,
                        avz=form_device.avz,
                        current_check_date=instance.check_date,
                        who_prepared=instance.who_prepared,
                        who_checked=instance.who_checked,
                    )
                print(update_devices)
                if update_devices.__class__ is not int:
                    update_devices.save()
                for device in this_type_devices:
                    kip_report.devices.add(
                        device.id,
                        through_defaults={"station": instance.station,
                                          "mounting_address": '',
                                          "check_date": instance.check_date,
                                          "who_prepared": instance.who_prepared,
                                          "who_checked": instance.who_checked}
                    )

                instance.mounting_address = ""

            elif re.fullmatch(r"((\d+)|(релейная)|(тоннель)|(поле))-((\d+)|(остальное))", instance.mounting_address):
                rack, number = instance.mounting_address.strip().split("-")
                try:
                    place = Place.objects.get(
                        rack__station=instance.station,
                        rack__number=rack,
                        number=number,
                    )
                except Place.DoesNotExist:
                    print(rack, "-", number, " Не существует")
                    pass
                else:
                    try:
                        device_on_place = Device.objects.get(mounting_address=place)
                    except Device.MultipleObjectsReturned:
                        form_device.status = Device.in_progress
                        form_device.station = instance.station

                        if place:
                            form_device.mounting_address = place
                            form_device.name = "Без названия"

                        for avz_device in avz.device_set.all():
                            if avz_device.device_type == form_device.device_type:
                                form_device.frequency_of_check = avz_device.frequency_of_check
                            else:
                                form_device.frequency_of_check = 1
                    except Device.DoesNotExist:
                        messages.warning(
                            request,
                            f"На месте {place.__str__()} "
                            "сейчас нет прибора"
                            ". Вы уверены, что готовите прибор на нужное место? Уточните у механиков"
                        )
                        form_device.status = Device.in_progress
                        form_device.station = instance.station

                        if place:
                            form_device.mounting_address = place
                            form_device.name = "Без названия"

                        for avz_device in avz.device_set.all():
                            if avz_device.device_type == form_device.device_type:
                                form_device.frequency_of_check = avz_device.frequency_of_check
                            else:
                                form_device.frequency_of_check = 1
                    else:
                        form_device.name = device_on_place.name
                        form_device.status = Device.in_progress
                        form_device.station = device_on_place.station
                        form_device.avz = device_on_place.avz
                        form_device.frequency_of_check = device_on_place.frequency_of_check
                        form_device.mounting_address = device_on_place.mounting_address
            form_device.save()
        formset.save()
        return super().save_formset(request, form, formset, change)



