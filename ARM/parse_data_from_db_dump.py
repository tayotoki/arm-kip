import re

import pymysql

from pathlib import Path

import sys
import os

import django

from django.conf import settings

MAIN_MODULE_PATH = Path(__file__).resolve().parent.parent


sys.path.append(str(MAIN_MODULE_PATH))
os.environ['DJANGO_SETTINGS_MODULE'] = 'ARM_SHN.settings'

# if not settings.configured:
#     settings.configure()

django.setup()

from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from ARM.models import Device, Stock, Station, Place, Tipe, Rack, AVZ

station_id_decode = {
    1: 1,  # Ботаническая
    2: 2,  # Чкаловская
    4: 3,  # Геологическая
    5: 4,  # Площадь 1905
    6: 5,  # Динамо
    8: 7,  # Машиностроителей
    9: 8,  # Уралмаш
    10: 9,  # Пр. Космонавтов
    11: 10,  # Депо Калиновское
    12: 6,  # Уральская
    21: 11,  # Инж. Корпус
}

place_objects = []
device_objects = []

print(Station.objects.all())
print(Station.objects.get(pk=1))
print(Rack.objects.all())
Place.objects.all().delete()
Device.objects.all().delete()
print(Place.objects.all())

with pymysql.connect(host='localhost', port='', user='test_user', passwd='1234', db='test_bd') as db:
    cursor = db.cursor()

    cursor.execute(f"""
        SELECT
            Stan_Id,
            Stativ,
            Mesto,
            Nazn,
            Zn,
            Dw,
            Du,
            Per,
            Dat_Sp,
            Tipe_Id,
            Reg,
            Prow
        FROM glav;
    """)

    data = cursor.fetchall()
    for station_id, rack_number, place, *other_data in data:
        device_fields = {
            "name": other_data[0],  # if other_data[6] != 300 else None,
            "inventory_number": other_data[1],
            "manufacture_date": other_data[2],
            "current_check_date": other_data[3],
            "frequency_of_check": other_data[4],
            "next_check_date": other_data[5],
            "device_type_id": other_data[6],
            "old_information": f"Регулировал: {other_data[7]} "
                               f"Проверил: {other_data[8]}",
            "stock": None,
        }

        rack_number = rack_number.strip()
        if station_id == 20:

            device_fields |= {
                "name": None if other_data[6] != 300 else other_data[0],
                "current_check_date": None,
                "frequency_of_check": None,
                "next_check_date": None,
                "stock_id": 1
            }

        if rack_number.strip() in ("АВЗ", "зап", "запас", "авз", "Запас"):
            continue
        print(station_id, rack_number, place)

        if "стр" in rack_number.strip().lower() or "N" in place:
            place = "стрелка №" + re.search(r'(\d+)', place.strip().replace(" ", "")).group()

        try:
            rack = Rack.objects.get(
                station=Station.objects.get(pk=station_id_decode.get(station_id)),
                number=rack_number,
            )
        except Rack.DoesNotExist:
            rack = Rack.objects.get(
                Q(station=Station.objects.get(pk=station_id_decode.get(station_id))) &
                (Q(number="тоннель") | Q(number="поле")),
            )
        except Station.DoesNotExist:
            rack = None

        obj = Place(
            rack=rack,
            number=place.strip(),
        ) if rack else None

        device = Device(
            mounting_address=obj,
            station=obj.rack.station if rack else None,
            **device_fields,
        )

        try:
            print(device)
        except Tipe.DoesNotExist:
            unknown_type = Tipe.objects.get(pk=300)
            device.device_type = unknown_type

        print(
            "Serialazed: ", rack.station.name if rack else "Stock",
            rack.number if rack else "No rack",
            obj.number if obj else None
        )

        if obj:
            place_objects.append(obj)
        device_objects.append(device)

# for part in list(zip(*[iter(place_objects)] * 1000)):
#     Place.objects.bulk_create(part)

# for part in list(zip(*[iter(device_objects)] * 1000)):
#     Device.objects.bulk_create(part)

Place.objects.bulk_create(place_objects)
Device.objects.bulk_create(device_objects)
