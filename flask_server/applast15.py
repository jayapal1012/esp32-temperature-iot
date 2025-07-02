import os
import io
import threading
import serial
import time
import pandas as pd
import pymysql
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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

# Ensure CSV exists with header
if not os.path.exists(data_file):
    with open(data_file, 'w') as f:
        f.write('Timestamp,Temperature\n')

# Serial reading thread
def serial_reader():
    while True:
        try:
            ser = serial.Serial('COM4', 115200, timeout=1)
            break
        except serial.SerialException:
            print("COM port busy/unavailable; retrying in 2s...")
            time.sleep(2)

    print("\u2705 Serial port opened.")
    while True:
        line = ser.readline().decode(errors='ignore').strip()
        if line:
            parts = line.split(',')
            try:
                temp = float(parts[-1])
                if temp < -50 or temp > 150:  # Sanity filter
                    continue
            except:
                continue
            ts = datetime.now()

            # Append to CSV
            with open(data_file, 'a') as f:
                f.write(f"{ts.strftime('%Y-%m-%d %H:%M:%S')},{temp}\n")

            # Insert into DB
            try:
                print(f"📅 Inserting: {ts} ({type(ts)}), {temp}")
                query = "INSERT INTO temperature_log (timestamp, temperature) VALUES (%s, %s)"
                params = (ts.strftime('%Y-%m-%d %H:%M:%S'), temp)
                print("\u27a1️ Query:", query)
                print("\u27a1️ Params:", params)
                cursor = db.cursor()
                cursor.execute(query, params)
                db.commit()
                cursor.close()
            except Exception as e:
                print("\u274c DB insert error:", e)

        time.sleep(0.1)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/download')
def download():
    return send_file(data_file, as_attachment=True)

@app.route('/plot')
def plot():
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT timestamp, temperature FROM temperature_log ORDER BY timestamp DESC LIMIT 15"
        )
        rows = cursor.fetchall()
        cursor.close()

        rows = rows[::-1]
        timestamps = [row['timestamp'].strftime('%H:%M:%S') for row in rows]
        temperatures = [float(row['temperature']) for row in rows]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(timestamps, temperatures, marker='o', color='orange')
        ax.set_title('Last 15 Temperature Readings')
        ax.set_xlabel('Time')
        ax.set_ylabel('Temperature (\u00b0C)')
        ax.grid(True)
        plt.xticks(rotation=45)

        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format='png')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')

    except Exception as e:
        print("\u274c Plot error:", e)
        return "Plot error", 500

if __name__ == '__main__':
    threading.Thread(target=serial_reader, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
