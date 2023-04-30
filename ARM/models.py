from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone


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
        return (f"({self.rack.station.__str__()[:5]})"
               f"{self.rack.number}-{self.number}")


class Device(models.Model):
    READY = "ready"
    SEND = "send"
    OVERDUE = "overdue"
    NORMAL = "normal"
    IN_PROGRESS = "in_progress"
    DECOMMISIONED = "decommissioned"
    REPLACED = "replaced"

    CHOICES = [
        (READY, "нужна замена"),
        (SEND, "отправлен"),
        (OVERDUE, "просрочен"),
        (NORMAL, "сроки в норме"),
        (IN_PROGRESS, "готовится"),
        (DECOMMISIONED, "списан"),
        (REPLACED, "заменен"),
    ]

    CONTACT_TYPE_CHOICES = [
        ("contact", "контактная"),
        ("contactless", "бесконтактная"),
    ]

    station = models.ForeignKey(Station, null=True, blank=True, verbose_name="Станция", on_delete=models.SET_NULL)
    avz = models.ForeignKey(AVZ, null=True, blank=True, verbose_name="АВЗ", on_delete=models.SET_NULL)
    stock = models.ForeignKey(Stock, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Склад")
    status = models.CharField(verbose_name="Статус", max_length=20, choices=CHOICES, blank=True)
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
    name = models.CharField(verbose_name="Название", max_length=20, blank=True)
    inventory_number = models.CharField(max_length=30, verbose_name="Инв. номер", null=True, blank=True)
    mounting_address = models.ForeignKey(Place,
                                         on_delete=models.SET_NULL,
                                         null=True,
                                         blank=True,
                                         verbose_name="Монтажный адрес",
                                         help_text="Введите статив и выберите нужный адрес из списка")
    manufacture_date = models.DateField(verbose_name='дата производства', null=True)
    frequency_of_check = models.IntegerField(verbose_name='периодичность проверки', null=True, default=0)
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
    current_check_date = models.DateField(verbose_name='дата проверки')
    next_check_date = models.DateField(verbose_name='дата следующей проверки')

    class Meta:
        verbose_name = "Прибор"
        verbose_name_plural = "Приборы"

    def clean(self):
        if self.name:
            if not self.mounting_address:
                raise ValidationError("Укажите монтажный адрес или удалите название прибора")
            if self.avz:
                raise ValidationError("Обратите внимание, у приборов в АВЗ не должно быть названия")

        if self.mounting_address:
            devices_on_address = self.mounting_address.device_set.all()
            devices_on_place = self.mounting_address.device_set.count()

            if devices_on_place > 0 and self.status != "in_progress"\
                    and self not in devices_on_address:
                raise ValidationError("На данном адресе уже установлен прибор, "
                                      "выберите другой адрес или измените статус на 'готовится'")

            if devices_on_place > 1 and self not in devices_on_address:
                raise ValidationError("На данном адресе уже установлен прибор и один прибор уже готовится")

            if devices_on_place > 1 and self in devices_on_address:
                other_device_status = [device.status for device in devices_on_address if device != self][0]
                if self.status == other_device_status:
                    raise ValidationError("На этом адресе уже есть прибор с таким же статусом")
                if not self.status and other_device_status == "in_progress":
                    raise ValidationError("Вы убираете на склад прибор, но оставляете место на стативе\
                                          пустым, зайдите на страницу места и исправьте ситуацию")
                if self.status in ("normal", "overdue", "ready") and other_device_status not in ("send", "in_progress"):
                    raise ValidationError("Указан неверный статус, оба прибора на складе или на стативе одновременно")

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

        if self.device_type == "contact":
            if not self.inventory_number:
                raise ValidationError("Укажите инвентарный номер для реле")

        if self.status is None:
            if self.stock == "Склад":
                if self.mounting_address is not None:
                    raise ValidationError("Уберите монтажный адрес")

    def __str__(self):
        return f'{self.name}({self.device_type}){self.mounting_address}'


class MechanicReport(models.Model):
    MONTHES = {
        1: "Январь",
        2: "Февраль",
        3: "Март",
        4: "Апрель",
        5: "Май",
        6: "Июнь",
        7: "Август",
        8: "Сентябрь",
        9: "Октябрь",
        10: "Ноябрь",
        11: "Декабрь",
    }

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
