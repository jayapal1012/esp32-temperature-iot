import os
import threading
import serial
import time
import pandas as pd
import pymysql
from flask import Flask, render_template, send_file, jsonify, Response
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # for headless environments
import matplotlib.pyplot as plt
import io

app = Flask(__name__)
data_file = "data_log.csv"

# --- DB Config ---
db = pymysql.connect(
    host='localhost',
    user='root',
    password='jayapal@1012',
    database='iot_data',
    cursorclass=pymysql.cursors.DictCursor
)

# Ensure CSV exists with header
if not os.path.exists(data_file):
    with open(data_file, 'w') as f:
        f.write('Timestamp,Temperature\n')

# Clear DB on startup
try:
    cursor = db.cursor()
    cursor.execute("DELETE FROM temperature_log")
    db.commit()
    cursor.close()
except Exception as e:
    print("DB Clear Error:", e)

# Serial Reader
def serial_reader():
    while True:
        try:
            ser = serial.Serial('COM4', 115200, timeout=1)
            break
        except serial.SerialException:
            print("COM port not ready, retrying...")
            time.sleep(2)

    print("✅ Serial port opened.")
    while True:
        try:
            line = ser.readline().decode(errors='ignore').strip()
            if line:
                parts = line.split(',')
                temp = round(float(parts[-1]), 2)
                ts = datetime.now()

                print(f"📥 Inserting: {ts} ({type(ts)}), {temp}")

                query = "INSERT INTO temperature_log (timestamp, temperature) VALUES (%s, %s)"
                params = (ts.strftime('%Y-%m-%d %H:%M:%S'), temp)
                print(f"➡️ Query: {query}")
                print(f"➡️ Params: {params}")
                
                cursor = db.cursor()
                cursor.execute(query, params)
                db.commit()
                cursor.close()

                db.commit()
                cursor.close()
        except Exception as e:
            print("❌ DB insert error:", e)
        time.sleep(1)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/plot')
def plot():
    try:
        cursor = db.cursor()
        cursor.execute("SELECT timestamp, temperature FROM temperature_log ORDER BY timestamp DESC LIMIT 50")
        rows = cursor.fetchall()
        cursor.close()

        if not rows:
            return "No data"

        rows = rows[::-1]
        timestamps = [row['timestamp'].strftime('%H:%M:%S') for row in rows]
        temperatures = [row['temperature'] for row in rows]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(timestamps, temperatures, marker='o')
        ax.set_title("Live Temperature Plot")
        ax.set_xlabel("Time")
        ax.set_ylabel("Temperature (°C)")
        ax.grid(True)
        fig.tight_layout()

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        return Response(img.getvalue(), mimetype='image/png')
    except Exception as e:
        return f"Plot error: {e}"

@app.route('/download')
def download():
    if not os.path.exists(data_file):
        with open(data_file, 'w') as f:
            f.write('Timestamp,Temperature\n')
    return send_file(data_file, as_attachment=True)

if __name__ == '__main__':
    threading.Thread(target=serial_reader, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
