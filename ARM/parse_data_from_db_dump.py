import re

import pymysql

import sys
import os

import django

sys.path.append('~/ARM/ARM_SHN')
os.environ['DJANGO_SETTINGS_MODULE'] = 'ARM_SHN.settings'
django.setup()

from django.db.models import Q

from ARM.models import Device, Stock, Station, Place, Tipe, Rack, AVZ


station_id_decode = {
    1: 1,
    2: 2,
    4: 3,
    5: 4,
    6: 5,
    8: 7,
    9: 8,
    10: 9,
    11: 10,
    12: 6,
    21: 11,
}

place_objects = []

print(Station.objects.all())
print(Station.objects.get(pk=1))
print(Rack.objects.all())
Place.objects.all().delete()
print(Place.objects.all())

with pymysql.connect(host='localhost', port='', user='test_user', passwd='1234', db='test_bd') as db:
    cursor = db.cursor()

    cursor.execute(f"""
        SELECT Stan_Id, Stativ, Mesto, Nazn, Zn, Dw, Du, Per, Dat_Sp, Tip_N FROM glav;
    """)

    data = cursor.fetchall()
    for station_id, rack_number, place, *_ in data:
        rack_number = rack_number.strip()
        if station_id == 20:
            continue
        if rack_number.strip() in ("АВЗ", "зап", "запас"):
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

        obj = Place(
            rack=rack,
            number=place.strip(),
        )

        print("Serialazed: ", rack.station.name, rack.number, obj.number)

        place_objects.append(obj)


Place.objects.bulk_create(place_objects)


