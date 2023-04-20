import pymysql

station_id_decode = {
    1: "Ботаническая",
    2: "Чкаловская",
    4: "Геологическая",
    5: "Площадь 1905г.",
    6: "Динамо",
    8: "Машиностроителей",
    9: "Уралмаш",
    10: "Пр. Космонавтов",
    11: "Депо Калиновское",
    12: "Уральская",
    21: "Инженерный корпус",
}

tipes_fixture = {}
devices_fixture = {}
counter = 1

with pymysql.connect(host='localhost', port='', user='test_user', passwd='1234', db='test_bd') as db:
    cursor = db.cursor()
    cursor.execute("""
        SELECT DISTINCT Tip_N FROM glav;
    """)
    data = cursor.fetchall()
    for type_, *_ in data:
        if type_ != 'null':
            tipes_fixture.update({
                "model": "ARM.Tipe",
                "pk": counter,
                "fields": {
                    "name": f"{type_}"
                }
            })
            counter += 1
    else:
        counter = 1

    cursor.execute("""
        SELECT Stan_id, Stativ, Mesto, Nazn, Zn, Dw, Du, Per, Dat_Sp, Tip_N FROM glav;
    """)
    data = cursor.fetchall()
    print(data)


