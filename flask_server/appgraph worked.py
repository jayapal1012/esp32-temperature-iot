import os
import threading
import serial
import time
import pandas as pd
import pymysql
from flask import Flask, render_template, send_file, jsonify, Response
from datetime import datetime
import matplotlib.pyplot as plt
import io

app = Flask(__name__)
data_file = "data_log.csv"

# ---- Database config: update password/db as needed ----
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

    print("✅ Serial port opened.")
    while True:
        line = ser.readline().decode(errors='ignore').strip()
        if line:
            parts = line.split(',')
            try:
                temp = float(parts[-1])
            except:
                continue
            timestamp = datetime.now()
            print(f"📥 Inserting: {timestamp} ({type(timestamp)}), {temp}")

            # Append to CSV
            with open(data_file, 'a') as f:
                f.write(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')},{temp}\n")

            # Insert into DB
            try:
                cursor = db.cursor()
                cursor.execute(
                    "INSERT INTO temperature_log (timestamp, temperature) VALUES (%s, %s)",
                    (timestamp, temp)
                )
                db.commit()
                cursor.close()
            except Exception as e:
                print(f"❌ DB insert error: {e}")
        time.sleep(0.1)

@app.route('/')
def index():
    return render_template("index_matplotlib.html")

@app.route('/download')
def download():
    if not os.path.exists(data_file):
        with open(data_file, 'w') as f:
            f.write('Timestamp,Temperature\n')
    return send_file(data_file, as_attachment=True)

@app.route('/plot')
def plot():
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT timestamp, temperature FROM temperature_log ORDER BY timestamp DESC LIMIT 100"
        )
        rows = cursor.fetchall()
        cursor.close()

        rows.reverse()
        timestamps = [row['timestamp'].strftime('%H:%M:%S') if isinstance(row['timestamp'], datetime) else str(row['timestamp']) for row in rows]
        temperatures = [row['temperature'] for row in rows]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(timestamps, temperatures, marker='o', linestyle='-')
        ax.set_title('Real-Time Temperature')
        ax.set_xlabel('Time')
        ax.set_ylabel('Temperature (°C)')
        ax.tick_params(axis='x', rotation=45)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        return Response(buf.getvalue(), mimetype='image/png')

    except Exception as e:
        return f"Error generating plot: {e}"

if __name__ == '__main__':
    threading.Thread(target=serial_reader, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
