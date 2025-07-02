import os
import threading
import serial
import time
import pymysql
import pandas as pd
from flask import Flask, render_template, send_file, jsonify
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt

import psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL"))


app = Flask(__name__)
data_file = "data_log.csv"

# Ensure CSV file exists
if not os.path.exists(data_file):
    with open(data_file, 'w') as f:
        f.write('Timestamp,Temperature\n')

# Background thread: Read serial and store in DB + CSV
def serial_reader():
    last_saved = time.time()
    while True:
        try:
            ser = serial.Serial('COM4', 115200, timeout=1)
            print("✅ Serial port opened.")
            break
        except:
            print("⏳ Waiting for COM4...")
            time.sleep(2)

    while True:
        line = ser.readline().decode(errors='ignore').strip()
        if line:
            try:
                temp = float(line.split(',')[-1])
                timestamp = datetime.now()
                print(f"🗕 Inserting: {timestamp} ({type(timestamp)}), {temp}")

                # Save to CSV
                with open(data_file, 'a') as f:
                    f.write(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')},{temp}\n")

                # Save to DB only every 3 seconds
                if time.time() - last_saved >= 3:
                    try:
                        conn = pymysql.connect(
                            host='localhost',
                            user='root',
                            password='jayapal@1012',
                            database='iot_data',
                            cursorclass=pymysql.cursors.DictCursor
                        )
                        with conn:
                            with conn.cursor() as cursor:
                                query = "INSERT INTO temperature_log (timestamp, temperature) VALUES (%s, %s)"
                                params = (timestamp.strftime('%Y-%m-%d %H:%M:%S'), float(temp))
                                print("\u27a1\ufe0f Query:", query)
                                print("\u27a1\ufe0f Params:", params)
                                cursor.execute(query, params)
                            conn.commit()
                            last_saved = time.time()
                    except Exception as e:
                        print("❌ DB insert error:", e)
            except:
                pass
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
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='jayapal@1012',
            database='iot_data',
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT timestamp, temperature FROM temperature_log ORDER BY timestamp DESC LIMIT 15")
                rows = cursor.fetchall()
                rows.reverse()

        times = [row['timestamp'].strftime('%H:%M:%S') for row in rows]
        temps = [row['temperature'] for row in rows]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(times, temps, marker='o')
        ax.set_xlabel("Time")
        ax.set_ylabel("Temperature (°C)")
        ax.set_title("Temperature vs Time")
        ax.tick_params(axis='x', rotation=45)
        plt.tight_layout()

        img_path = os.path.join("static", "plot.png")
        fig.savefig(img_path)
        plt.close()
        return send_file(img_path, mimetype='image/png')
    except Exception as e:
        print("❌ Plot error:", e)
        return "Plot generation failed", 500

if __name__ == '__main__':
    threading.Thread(target=serial_reader, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
