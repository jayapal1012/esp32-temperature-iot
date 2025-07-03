import os
from flask import Flask, request, render_template, send_file
import psycopg2
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
data_file = "data_log.csv"

# Ensure CSV exists
if not os.path.exists(data_file):
    with open(data_file, 'w') as f:
        f.write("Timestamp,Temperature\n")

# PostgreSQL connection
def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# Home Page
@app.route('/')
def index():
    return render_template("index.html")

# Receive temperature data from ESP32 (POST)
@app.route('/upload', methods=['POST'])
def upload():
    try:
        temp = float(request.form['temperature'])
        timestamp = datetime.now()
        print(f"✅ Received: {timestamp} | {temp}°C")

        # Save to PostgreSQL
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO temperature_log (timestamp, temperature) VALUES (%s, %s)",
                    (timestamp, temp))
        conn.commit()
        cur.close()
        conn.close()

        # Save to CSV
        with open(data_file, 'a') as f:
            f.write(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')},{temp}\n")

        return "Success", 200
    except Exception as e:
        print("❌ Upload error:", e)
        return "Error", 500

# Download CSV
@app.route('/download')
def download():
    return send_file(data_file, as_attachment=True)

# Show plot
@app.route('/plot')
def plot():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT timestamp, temperature FROM temperature_log ORDER BY timestamp DESC LIMIT 15")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        rows.reverse()  # So oldest is first
        times = [r[0].strftime('%H:%M:%S') for r in rows]
        temps = [r[1] for r in rows]

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
        return "Error", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
