import pymysql

with pymysql.connect(host='localhost', port='', user='test_user', passwd='1234', db='test_bd') as db:
    cursor = db.cursor()
    cursor.execute("""
        SELECT DISTINCT Tip_N FROM glav;
    """)
    data = cursor.fetchall()
    print(data, len(data), sep='\n')