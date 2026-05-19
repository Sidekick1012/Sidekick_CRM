import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "database/railway.db"

def init_db():
    if not os.path.exists("database"):
        os.makedirs("database")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Trains Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            type TEXT,
            total_seats INTEGER,
            status TEXT DEFAULT 'Active'
        )
    ''')
    
    # Stations Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            city TEXT
        )
    ''')
    
    # Schedules Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_id INTEGER,
            origin_station_id INTEGER,
            destination_station_id INTEGER,
            departure_time TEXT,
            arrival_time TEXT,
            price REAL,
            FOREIGN KEY (train_id) REFERENCES trains (id),
            FOREIGN KEY (origin_station_id) REFERENCES stations (id),
            FOREIGN KEY (destination_station_id) REFERENCES stations (id)
        )
    ''')
    
    # Bookings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER,
            passenger_name TEXT NOT NULL,
            passenger_email TEXT,
            seat_number TEXT,
            booking_date TEXT,
            status TEXT DEFAULT 'Confirmed',
            FOREIGN KEY (schedule_id) REFERENCES schedules (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_trains():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trains")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_train(number, name, t_type, seats):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO trains (train_number, name, type, total_seats) VALUES (?, ?, ?, ?)",
                   (number, name, t_type, seats))
    conn.commit()
    conn.close()

def get_stations():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stations")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_station(code, name, city):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO stations (code, name, city) VALUES (?, ?, ?)",
                   (code, name, city))
    conn.commit()
    conn.close()

def get_schedules():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = '''
        SELECT s.*, t.name as train_name, t.train_number, 
               o.name as origin_name, d.name as destination_name
        FROM schedules s
        JOIN trains t ON s.train_id = t.id
        JOIN stations o ON s.origin_station_id = o.id
        JOIN stations d ON s.destination_station_id = d.id
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_schedule(train_id, origin_id, dest_id, dep, arr, price):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO schedules (train_id, origin_station_id, destination_station_id, departure_time, arrival_time, price) VALUES (?, ?, ?, ?, ?, ?)",
                   (train_id, origin_id, dest_id, dep, arr, price))
    conn.commit()
    conn.close()

def get_bookings():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = '''
        SELECT b.*, t.name as train_name, s.departure_time, o.name as origin, d.name as destination
        FROM bookings b
        JOIN schedules s ON b.schedule_id = s.id
        JOIN trains t ON s.train_id = t.id
        JOIN stations o ON s.origin_station_id = o.id
        JOIN stations d ON s.destination_station_id = d.id
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_booking(schedule_id, name, email, seat):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO bookings (schedule_id, passenger_name, passenger_email, seat_number, booking_date) VALUES (?, ?, ?, ?, ?)",
                   (schedule_id, name, email, seat, str(datetime.now())))
    conn.commit()
    conn.close()

def seed_data():
    # Only seed if empty
    if not get_trains():
        add_train("EXP-101", "Karakoram Express", "Express", 450)
        add_train("EXP-102", "Tezgam", "Express", 600)
        add_train("LOC-201", "Lahore Local", "Local", 300)
        
        add_station("LHR", "Lahore Junction", "Lahore")
        add_station("KHI", "Karachi City", "Karachi")
        add_station("ISL", "Rawalpindi Station", "Islamabad")
        
        stations = get_stations()
        trains = get_trains()
        
        if len(stations) >= 3 and len(trains) >= 2:
            add_schedule(trains[0]['id'], stations[0]['id'], stations[1]['id'], "08:00 PM", "09:00 AM", 4500.0)
            add_schedule(trains[1]['id'], stations[1]['id'], stations[2]['id'], "10:00 AM", "04:00 PM", 3200.0)
            
            schedules = get_schedules()
            if schedules:
                add_booking(schedules[0]['id'], "Ali Ahmed", "ali@example.com", "B-12")
                add_booking(schedules[0]['id'], "Sara Khan", "sara@example.com", "B-13")
                add_booking(schedules[1]['id'], "Zain Malik", "zain@example.com", "A-01")
