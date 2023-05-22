from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html


class Stock(models.Model):
    name = models.CharField(verbose_name="Склад", default="Склад", editable=False, max_length=6, unique=True)

    class Meta:
        verbose_name = "Склад"
        verbose_name_plural = "Склад"

    def save(self, *args, **kwargs):
        if self.__class__.objects.count():
            self.pk = self.__class__.objects.first().pk
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tipe(models.Model):
    name = models.CharField(max_length=25, verbose_name="Тип прибора")

    class Meta:
        verbose_name = "Тип прибора"
        verbose_name_plural = "Типы приборов"

    def __str__(self):
        return self.name


class Station(models.Model):
    CHOICES = [
        ("БТ", "Ботаническая"),
        ("ЧК", "Чкаловская"),
        ("ГЕОЛ", "Геологическая"),
        ("ПЛ", "Площадь 1905г."),
        ("ДИН", "Динамо"),
        ("УРЛСК", "Уральская"),
        ("МАШ", "Машиностроителей"),
        ("УРЛМ", "Уралмаш"),
        ("ПР", "Проспект Космонавтов"),
        ("ДЕПО", "Депо Калиновское"),
        ("ИНЖ. КОРПУС", "Инж. Корпус"),
    ]
    name = models.CharField(max_length=50, choices=CHOICES, default="Склад", verbose_name="Станция")

    class Meta:
        verbose_name = "Станция"
        verbose_name_plural = "Станции"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.__class__.objects.count():
            self.pk = self.__class__.objects.first().pk
        super().save(*args, **kwargs)


class Rack(models.Model): # статив
    number = models.CharField(max_length=20, verbose_name='Статив', null=True)
    station = models.ForeignKey(Station,
                                on_delete=models.SET_NULL,
                                null=True,
                                verbose_name="Станция")

    class Meta:
        verbose_name = "Статив"
        verbose_name_plural = "Стативы"

    def __str__(self):
        return f"({self.station}){self.number}"


class AVZ(models.Model):
    station = models.OneToOneField(Station, on_delete=models.CASCADE, blank=True, verbose_name="Станция")

    class Meta:
        verbose_name = "АВЗ"
        verbose_name_plural = "АВЗ"

    def __str__(self):
        return f"АВЗ {self.station.__str__()}"


class Place(models.Model): # место прибора
    rack = models.ForeignKey(Rack,
                             on_delete=models.CASCADE, 
                             verbose_name="Статив",
                             help_text="Введите номер "
                                "статива и выберите значение "
                                "из списка результатов")
    number = models.CharField(max_length=20, verbose_name="Номер места")

    class Meta:
        verbose_name = "Место"
        verbose_name_plural = "Места"

    def __str__(self):
        station_name = self.rack.station.__str__()[:5]
        return (f"({station_name})"
               f"{self.rack.number}-{self.number}")


class Device(models.Model):
    ready = "нужна замена"
    send = "отправлен"
    overdue = "просрочен"
    normal = "сроки в норме"
    in_progress = "готовится"
    decommissioned = "списан"
    replaced = "заменен"

    contact = "контактная"
    contactless = "бесконтактная"

    CHOICES = [
        (ready, "нужна замена"),
        (send, "отправлен"),
        (overdue, "просрочен"),
        (normal, "сроки в норме"),
        (in_progress, "готовится"),
        (decommissioned, "списан"),
        (replaced, "заменен"),
    ]

    CONTACT_TYPE_CHOICES = [
        (contact, "контактная"),
        (contactless, "бесконтактная"),
    ]

    station = models.ForeignKey(Station, null=True, blank=True, verbose_name="Станция", on_delete=models.SET_NULL)
    avz = models.ForeignKey(AVZ, null=True, blank=True, verbose_name="АВЗ", on_delete=models.SET_NULL)
    stock = models.ForeignKey(Stock, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Склад")
    status = models.CharField(verbose_name="Статус", max_length=20, choices=CHOICES, blank=True, null=True)
    device_type = models.ForeignKey(Tipe,
                                    null=True,
                                    on_delete=models.SET_NULL,
                                    verbose_name="Тип прибора",
                                    max_length=20,
                                    help_text="Начните вводить тип прибора "
                                              "и выберите нужное значение "
                                              "из списка")
    contact_type = models.CharField(null=True,
                                    verbose_name="Наличие контактов",
                                    max_length=20,
                                    choices=CONTACT_TYPE_CHOICES)
    name = models.CharField(verbose_name="Название", max_length=20, blank=True, null=True)
    inventory_number = models.CharField(max_length=30, verbose_name="Инв. номер", null=True, blank=True)
    mounting_address = models.ForeignKey(Place,
                                         on_delete=models.SET_NULL,
                                         null=True,
                                         blank=True,
                                         verbose_name="Монтажный адрес",
                                         help_text="Введите статив и выберите нужный адрес из списка")
    manufacture_date = models.DateField(verbose_name='дата производства', null=True)
    frequency_of_check = models.PositiveIntegerField(verbose_name='периодичность проверки', null=True, default=0)
    who_prepared = models.ForeignKey(User,
                                     verbose_name='кто готовил',
                                     on_delete=models.SET_NULL,
                                     null=True,
                                     blank=True,
                                     related_name='preparer')
    who_checked = models.ForeignKey(User,
                                    verbose_name='кто проверил',
                                    on_delete=models.SET_NULL,
                                    null=True,
                                    blank=True,
                                    related_name='checker')
    current_check_date = models.DateField(verbose_name='дата проверки', null=True, blank=True)
    next_check_date = models.DateField(verbose_name='дата следующей проверки', null=True)
    old_information = models.CharField(max_length=60, null=True, blank=True, verbose_name="Старая информация")

    class Meta:
        verbose_name = "Прибор"
        verbose_name_plural = "Приборы"

    def clean(self):
        other_places = Place.objects.filter(
            Q(rack__number="релейная") | Q(rack__number="тоннель") | Q(rack__number="поле"),
            number="остальное",
        )
        if self.name:
            if not self.mounting_address:
                raise ValidationError("Укажите монтажный адрес или удалите название прибора")
            if self.avz:
                raise ValidationError("Обратите внимание, у приборов в АВЗ не должно быть названия")

        if self.mounting_address:
            devices_on_address = self.mounting_address.device_set.all()
            devices_on_place = self.mounting_address.device_set.count()

            if self.mounting_address not in other_places:

                if devices_on_place > 0 and self.status != self.in_progress or self.status != self.send\
                        and self not in devices_on_address:
                    raise ValidationError("На данном адресе уже установлен прибор, "
                                          "выберите другой адрес или измените статус на 'готовится', 'отправлен'")

                if devices_on_place > 1 and self not in devices_on_address:
                    raise ValidationError("На данном адресе уже установлен прибор и один прибор уже готовится")

                if devices_on_place > 1 and self in devices_on_address:
                    other_device_status = [device.status for device in devices_on_address if device != self][0]
                    if self.status == other_device_status:
                        raise ValidationError("На этом адресе уже есть прибор с таким же статусом")
                    if not self.status and other_device_status == "in_progress":
                        raise ValidationError("Вы убираете на склад прибор, но оставляете место на стативе\
                                              пустым, зайдите на страницу места и исправьте ситуацию")
                    if (self.status in (
                        self.normal, self.overdue, self.ready
                    ) and other_device_status not in (
                        self.send, self.in_progress
                    )) or (other_device_status in (
                        self.normal, self.overdue, self.ready
                    ) and self.status not in (
                        self.send, self.in_progress
                    )):
                        raise ValidationError("Указан неверный статус, оба прибора на "
                                              "складе или на стативе одновременно")

        if self.station:
            if self.avz:
                if self.mounting_address:
                    raise ValidationError("Обратите внимание, если прибор в АВЗ, то у него не может быть адреса")

        if self.stock:
            if any(
                    (self.station, self.avz, self.mounting_address)
            ):
                raise ValidationError("Если прибор на складе, то он не имеет отношения к какой-либо станции")
            if self.status:
                raise ValidationError("Сделайте статус пустым, если хотите изменить статус - укажите станцию")

        if self.contact_type == self.contact:
            if not self.inventory_number:
                raise ValidationError("Укажите инвентарный номер для реле")

        if self.status is None:
            if self.stock == "Склад":
                if self.mounting_address is not None:
                    raise ValidationError("Уберите монтажный адрес")

    def __str__(self):
        if self.avz:
            return f'({self.device_type})({self.inventory_number if self.inventory_number else "--"})({self.avz.__str__()})'
        return (f'{self.name}({self.device_type}){self.mounting_address}'
                if self.mounting_address else f'{self.name}({self.device_type})'
                if self.name else f'({self.device_type})({self.inventory_number if self.inventory_number else "--"})')

    def get_admin_change_url(self):
        return reverse("admin:ARM_device_change", args=(self.id,))

    def get_next_check_date(self):
        if self.current_check_date:
            year = self.current_check_date.year + self.frequency_of_check
            self.next_check_date = date(
                year=year,
                month=self.current_check_date.month,
                day=self.current_check_date.day,
            )
            return self.next_check_date

    def get_status(self):
        if self.next_check_date:
            if self.next_check_date > timezone.localdate():
                year = self.next_check_date.year
                month = self.next_check_date.month
                day = self.next_check_date.day
                if any(
                        (
                            year > timezone.localdate().year,
                            all((
                                year == timezone.localdate().year,
                                month > timezone.localdate().month,
                            )),
                        )
                ):
                    return self.normal
                elif all((
                    year == timezone.localdate().year,
                    month < timezone.localdate().month,
                )):
                    return self.ready
                else:
                    return self.overdue

    
class MechanicReport(models.Model):
    title = models.CharField(max_length=30, verbose_name="Заголовок", blank=True, help_text="Краткое пояснение, "
                                                            "например 'просрок', 'заменить в этом месяце' и т.д. "
                                                            "Не более 30 символов")
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, verbose_name="Работник")
    station = models.ForeignKey(Station, on_delete=models.CASCADE, verbose_name="Станция")
    devices = models.ManyToManyField(Device, related_name="marked_devices", verbose_name="Помеченные приборы", help_text=(
        "Поиск по названию, но лучше по инвентарному номеру для точности"
    ))
    explanation = models.TextField(max_length=300, verbose_name="Пояснение", blank=True)
    created = models.DateTimeField(auto_now_add=True, editable=False, verbose_name="Создан")
    modified = models.DateTimeField(auto_now=True, editable=False, verbose_name="Изменен")

    class Meta:
        verbose_name = "Отчет механика"
        verbose_name_plural = "Отчеты механиков"

    def __str__(self):
        return f"ст. {self.station.name} - отчет N {self.pk}"


class Comment(models.Model):
    author = models.ForeignKey(User,
                               null=True,
                               on_delete=models.SET_NULL,
                               related_name="author",
                               verbose_name="Автор")
                               
    mech_report = models.ForeignKey(MechanicReport, on_delete=models.CASCADE, verbose_name="Отчет")
    text = models.TextField(max_length=150, verbose_name="Комментарий")
    published = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"

    def __str__(self):
        return f"{self.author}"


class KipReport(models.Model):
    title = models.CharField(max_length=100,
                             verbose_name="Заголовок",
                             null=True,
                             blank=True)
    author = models.ForeignKey(User,
                               null=True,
                               on_delete=models.SET_NULL,
                               related_name="creator",
                               verbose_name="Автор")
    devices = models.ManyToManyField(Device,
                                     related_name="kip_devices",
                                     verbose_name="Виртуальный ящик",
                                     help_text="Поиск по инвентарному номеру прибора или по типу",
                                     through="DeviceKipReport")
    explanation = models.TextField(max_length=300, verbose_name="Пояснение", blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False, verbose_name="Создан")
    modified = models.DateTimeField(auto_now=True, editable=False, verbose_name="Изменен")

    class Meta:
        verbose_name = "Отчет КИП"
        verbose_name_plural = "Отчеты КИП"

    def __str__(self):
        return f"Отчет КИП N {self.pk}"

    def get_devices(self):
        return Device.objects.filter(stock=Stock.objects.get(pk=1))


class DeviceKipReport(models.Model):
    kip_report = models.ForeignKey(KipReport, on_delete=models.CASCADE, verbose_name="Текущий отчет")
    device = models.ForeignKey(Device, on_delete=models.CASCADE, verbose_name="Прибор")
    station = models.ForeignKey(Station, on_delete=models.CASCADE, verbose_name="Станция", null=True)
    mounting_address = models.CharField(max_length=18,
                                        verbose_name="Монтажный адрес или АВЗ",
                                        help_text="Если прибор готовится в АВЗ какой-то станции, "
                                                  "укажите станцию и впишите в это поле 'авз'."
                                                  "Если готовите много бесконтактной аппаратуры, "
                                                  "например, предохранителей, укажите количество "
                                                  "ввиде 'n шт.'")
    check_date = models.DateField(null=True, blank=True, verbose_name="дата регулировки")
    who_prepared = models.ForeignKey(User,
                                     related_name="kip_preparer",
                                     verbose_name="Регулировал",
                                     on_delete=models.SET_NULL,
                                     null=True,
                                     blank=True)
    who_checked = models.ForeignKey(User,
                                    related_name="kip_checker",
                                    verbose_name="Проверил",
                                    on_delete=models.SET_NULL,
                                    null=True,
                                    blank=True)

    class Meta:
        verbose_name = "Прибор"
        verbose_name_plural = "Ящик"

    def __str__(self):
        return f"{self.device} на {self.station}({self.mounting_address})"

