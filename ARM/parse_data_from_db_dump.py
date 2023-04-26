import pymysql
import json

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

tipes_fixture = []
devices_fixture = []
racks_fixture = []
places_fixture = []

counter = 1

visited_station_ids = set()

with pymysql.connect(host='localhost', port='', user='test_user', passwd='1234', db='test_bd') as db:
    cursor = db.cursor()
    cursor.execute("""
        SELECT DISTINCT Tip_N, Tipe_Id FROM glav;
    """)
    data = cursor.fetchall()
    for type_, type_id in data:
        print(type_)
        if type_ != 'null':
            tipes_fixture.append({
                "model": "ARM.Tipe",
                "pk": type_id,
                "fields": {
                    "name": f"{type_}"
                }
            })

    for _id in station_id_decode.keys():
        cursor.execute(f"""
            SELECT Stan_id, Stativ FROM glav
            WHERE Stan_Id = {_id}
            GROUP BY Stativ;
        """)
        data = cursor.fetchall()
        print(data)
        for station_id, rack_number in data:
            station = station_id_decode.get(station_id)
            rack_number = rack_number.strip()

            if rack_number in ("зап",
                               "АВЗ",
                               "стр",
                               "Ш-Т",
                               "ш-т",
                               "СТР",
                               "тон",
                               "АВМ",
                               "БВС",
                               "ш-ф",
                               "кор",
                               "Стр",
                               "лам",
                               "стp"):
                if station == 10:
                    if station in visited_station_ids:
                        continue
                    racks_fixture.append(
                        {
                            "model": "ARM.Rack",
                            "pk": counter,
                            "fields": {
                                "station": station,
                                "number": "поле",
                            }
                        }
                    )
                    visited_station_ids.add(station)
                else:
                    if station in visited_station_ids:
                        continue
                    racks_fixture.append(
                        {
                            "model": "ARM.Rack",
                            "pk": counter,
                            "fields": {
                                "station": station,
                                "number": "тоннель",
                            }
                        }
                    )
                    visited_station_ids.add(station)
            else:
                racks_fixture.append(
                    {
                        "model": "ARM.Rack",
                        "pk": counter,
                        "fields": {
                            "station": station,
                            "number": rack_number,
                        }
                    }
                )

            counter += 1
    else:
        counter = 1

    # cursor.execute(f"""
    #     SELECT Stan_Id, Stativ, Mesto, Nazn, Zn, Dw, Du, Per, Dat_Sp, Tip_N FROM glav;
    # """)


with open("./fixtures/types.json", "w", encoding='utf-8') as types:
    json.dump(tipes_fixture, types)

with open("./fixtures/racks.json", "w", encoding="utf-8") as racks:
    json.dump(racks_fixture, racks)

