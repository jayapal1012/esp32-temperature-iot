import os
import threading
import serial
import time
import pandas as pd
import pymysql
from flask import Flask, render_template, send_file, jsonify
from datetime import datetime

app = Flask(__name__)
data_file = "data_log.csv"

# ---- Database config ----
db = pymysql.connect(
    host='localhost',
    user='root',
    password='jayapal@1012',
    database='iot_data',
    cursorclass=pymysql.cursors.DictCursor
)

# Ensure CSV file exists
if not os.path.exists(data_file):
    with open(data_file, 'w') as f:
        f.write('Timestamp,Temperature\n')

# ---- Serial reader thread ----
def serial_reader():
    while True:
        try:
            ser = serial.Serial('COM4', 115200, timeout=1)
            break
        except serial.SerialException:
            print("Retrying serial connection in 2s...")
            time.sleep(2)

    print("✅ Serial port opened.")

    while True:
        try:
            line = ser.readline().decode(errors='ignore').strip()
            if not line:
                continue

            parts = line.split(',')
            temp = float(parts[-1])  # Last part is temperature
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Append to CSV
            with open(data_file, 'a') as f:
                f.write(f"{timestamp},{temp}\n")

            # Insert into DB
            print(f"📅 Inserting: {timestamp} (<class 'str'>), {temp}")
            try:
                with db.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO temperature_log (timestamp, temperature) VALUES (%s, %s)",
                        (timestamp, temp)
                    )
                    db.commit()
            except Exception as e:
                print("❌ DB insert error:", e)

            time.sleep(1)
        except Exception as e:
            print("Serial read error:", e)
            time.sleep(1)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/data')
def data():
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT timestamp, temperature FROM temperature_log ORDER BY timestamp DESC LIMIT 100")
            rows = cursor.fetchall()
            rows.reverse()
            data_list = [
                {
                    'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'temperature': row['temperature']
                } for row in rows
            ]
            return jsonify(data_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download')
def download():
    if not os.path.exists(data_file):
        with open(data_file, 'w') as f:
            f.write('Timestamp,Temperature\n')
    return send_file(data_file, as_attachment=True)

if __name__ == '__main__':
    threading.Thread(target=serial_reader, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
