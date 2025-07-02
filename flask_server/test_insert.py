from datetime import datetime
import pymysql

db = pymysql.connect(
    host='localhost',
    user='root',
    password='jayapal@1012',
    database='iot_data'
)

timestamp = datetime.now().replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
temperature = 25.5

print(f"Inserting: {timestamp}, {temperature}")

try:
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO temperature_log (timestamp, temperature) VALUES (%s, %s)",
        (timestamp, temperature)
    )
    db.commit()
    print("✅ Inserted successfully!")
except Exception as e:
    print("❌ DB insert error:", e)
