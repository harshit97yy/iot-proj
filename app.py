from flask import Flask, request, render_template, jsonify
import sqlite3
from datetime import datetime
from datetime import datetime
import pytz
app = Flask(__name__)

def get_db():
    conn = sqlite3.connect('sensor_data.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            temp REAL,
            hum REAL,
            air REAL,
            dust REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Store latest values
latest_data = {
    "temp": "--",
    "hum": "--",
    "air": "--",
    "dust": "--"
}

@app.route('/data', methods=['POST'])
def receive():
    temp = request.form.get('temp')
    hum = request.form.get('hum')
    air = request.form.get('air')
    dust = request.form.get('dust')

    # Update latest
    latest_data["temp"] = temp
    latest_data["hum"] = hum
    latest_data["air"] = air
    latest_data["dust"] = dust

    # Add to db with timestamp
    if all(x is not None for x in [temp, hum, air, dust]):
        ist = pytz.timezone('Asia/Kolkata')
        timestamp = datetime.now(ist).strftime('%H:%M:%S')
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO sensor_readings (timestamp, temp, hum, air, dust) VALUES (?, ?, ?, ?, ?)",
                      (timestamp, float(temp), float(hum), float(air), float(dust)))
            conn.commit()
        except Exception as e:
            print("DB Insert Error:", e)
        finally:
            conn.close()

    print("------ DATA FROM NODEMCU ------")
    print("Temp:", temp)
    print("Humidity:", hum)
    print("Air Quality:", air)
    print("Dust Level:", dust)

    return "OK"


@app.route('/api/data', methods=['GET'])
def get_data():
    period = request.args.get('period', 'latest') # 'latest', 'day', 'month', 'year'
    val = request.args.get('val', '') 

    conn = get_db()
    c = conn.cursor()
    
    history = []
    
    if period == 'month' and val:
        # Average by day
        query = """
        SELECT date(timestamp) as group_date, 
               AVG(temp) as temp, AVG(hum) as hum, AVG(air) as air, AVG(dust) as dust
        FROM sensor_readings
        WHERE strftime('%Y-%m', timestamp) = ?
        GROUP BY date(timestamp)
        ORDER BY group_date ASC
        """
        c.execute(query, (val,))
        rows = c.fetchall()
        for row in rows:
            history.append({
                "time": row['group_date'],
                "temp": round(row['temp'], 2) if row['temp'] is dict else (round(row['temp'], 2) if row['temp'] else 0),
                "hum": round(row['hum'], 2) if row['hum'] else 0,
                "air": round(row['air'], 2) if row['air'] else 0,
                "dust": round(row['dust'], 2) if row['dust'] else 0
            })
            
    elif period == 'year' and val:
        # Average by month
        query = """
        SELECT strftime('%Y-%m', timestamp) as group_date, 
               AVG(temp) as temp, AVG(hum) as hum, AVG(air) as air, AVG(dust) as dust
        FROM sensor_readings
        WHERE strftime('%Y', timestamp) = ?
        GROUP BY strftime('%Y-%m', timestamp)
        ORDER BY group_date ASC
        """
        c.execute(query, (val,))
        rows = c.fetchall()
        for row in rows:
            history.append({
                "time": row['group_date'],
                "temp": round(row['temp'], 2) if row['temp'] else 0,
                "hum": round(row['hum'], 2) if row['hum'] else 0,
                "air": round(row['air'], 2) if row['air'] else 0,
                "dust": round(row['dust'], 2) if row['dust'] else 0
            })
            
    elif period == 'day' and val:
        # All points for a specific day
        query = "SELECT timestamp, temp, hum, air, dust FROM sensor_readings WHERE date(timestamp) = ? ORDER BY timestamp ASC"
        c.execute(query, (val,))
        rows = c.fetchall()
        for row in rows:
            dt_str = row['timestamp'][-8:] # get HH:MM:SS
            history.append({
                "time": dt_str,
                "temp": row['temp'],
                "hum": row['hum'],
                "air": row['air'],
                "dust": row['dust']
            })
            
    else:
        # Latest 50 points
        query = "SELECT timestamp, temp, hum, air, dust FROM sensor_readings ORDER BY id DESC LIMIT 50"
        c.execute(query)
        rows = list(c.fetchall())[::-1]
        for row in rows:
            dt_str = row['timestamp'][-8:] # get HH:MM:SS
            history.append({
                "time": dt_str,
                "temp": row['temp'],
                "hum": row['hum'],
                "air": row['air'],
                "dust": row['dust']
            })

    conn.close()

    return jsonify({
        "latest": latest_data,
        "history": history
    })

# 🌐 Web page
@app.route('/')
def home():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
