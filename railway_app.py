import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os
from modules import railway_db as db

# Initialize Database
db.init_db()
db.seed_data()

# === CONFIG ===================================================================
st.set_page_config(
    page_title="RailFlow Intelligence",
    page_icon="🚄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === CUSTOM CSS (Premium Dark Theme) =========================================
def local_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');

        :root {
            --primary: #f59e0b;
            --bg-dark: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --text-main: #f8fafc;
            --accent: #38bdf8;
        }

        .stApp {
            background: radial-gradient(circle at top right, #1e293b, #0f172a);
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: rgba(15, 23, 42, 0.95) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }

        /* Glass Cards */
        .glass-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }
        .glass-card:hover {
            border-color: var(--primary);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            transform: translateY(-5px);
        }

        /* Metrics */
        .metric-card {
            text-align: center;
        }
        .metric-value {
            font-size: 2.5rem;
            font-weight: 800;
            color: var(--primary);
            margin-bottom: 5px;
        }
        .metric-label {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: #94a3b8;
        }

        /* Headers */
        .header-title {
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, #fff 0%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        .header-subtitle {
            color: var(--accent);
            letter-spacing: 3px;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9rem;
        }

        /* Tables */
        .stDataFrame {
            border-radius: 15px;
            overflow: hidden;
        }

        /* Buttons */
        .stButton>button {
            border-radius: 12px !important;
            padding: 10px 24px !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            transition: all 0.3s !important;
        }
        .stButton>button:hover {
            background-color: var(--primary) !important;
            color: white !important;
            border-color: var(--primary) !important;
        }
        </style>
    """, unsafe_allow_html=True)

local_css()

# === SIDEBAR NAVIGATION ===
with st.sidebar:
    st.markdown("""
        <div style='text-align: center; padding: 20px 0;'>
            <h1 style='color: #f59e0b; font-size: 2.2rem; margin:0;'>RAILFLOW</h1>
            <p style='color: #38bdf8; font-size: 0.7rem; letter-spacing: 3px;'>INTELLIGENCE SYSTEM</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    menu = st.radio("OPERATIONAL MENU", ["📊 Dashboard", "🚆 Train Fleet", "📅 Traffic Control", "🎫 Ticket Terminal", "📍 Station Network"])
    
    st.markdown("---")
    st.info("System Status: **OPERATIONAL**")
    st.caption("Version 4.0.2-LTS")

# === DASHBOARD PAGE ===
if menu == "📊 Dashboard":
    st.markdown("<p class='header-subtitle'>Operational Overview</p>", unsafe_allow_html=True)
    st.markdown("<h1 class='header-title'>Executive Command</h1>", unsafe_allow_html=True)
    
    # Quick Stats
    trains = db.get_trains()
    bookings = db.get_bookings()
    schedules = db.get_schedules()
    
    total_rev = sum([b['price'] for b in bookings if 'price' in b]) # Simplified
    # In my DB schema, price is in schedules. Let's fix that calculation.
    total_rev = 0
    for b in bookings:
        for s in schedules:
            if b['schedule_id'] == s['id']:
                total_rev += s['price']
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='glass-card metric-card'><div class='metric-value'>{len(trains)}</div><div class='metric-label'>Active Fleet</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='glass-card metric-card'><div class='metric-value'>{len(bookings)}</div><div class='metric-label'>Today's Bookings</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='glass-card metric-card'><div class='metric-value'>Rs.{total_rev:,.0f}</div><div class='metric-label'>Revenue (PKR)</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='glass-card metric-card'><div class='metric-value'>98%</div><div class='metric-label'>On-Time Rate</div></div>", unsafe_allow_html=True)

    # Charts
    col_l, col_r = st.columns([2, 1])
    
    with col_l:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Passenger Volume Dynamics")
        # Dummy data for chart
        chart_data = pd.DataFrame({
            'Time': ['06:00', '09:00', '12:00', '15:00', '18:00', '21:00', '00:00'],
            'Volume': [120, 450, 310, 280, 520, 390, 80]
        })
        fig = px.area(chart_data, x='Time', y='Volume', color_discrete_sequence=['#f59e0b'])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_r:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Fleet Distribution")
        types = [t['type'] for t in trains]
        type_counts = pd.Series(types).value_counts()
        fig_pie = px.pie(values=type_counts.values, names=type_counts.index, hole=0.6, color_discrete_sequence=px.colors.sequential.YlOrBr)
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# === TRAIN FLEET PAGE ===
elif menu == "🚆 Train Fleet":
    st.markdown("<p class='header-subtitle'>Asset Management</p>", unsafe_allow_html=True)
    st.markdown("<h1 class='header-title'>Fleet Inventory</h1>", unsafe_allow_html=True)
    
    with st.expander("➕ Register New Locomotive"):
        with st.form("add_train_form"):
            t_num = st.text_input("Train Number (e.g. EXP-500)")
            t_name = st.text_input("Train Name")
            t_type = st.selectbox("Type", ["Express", "Local", "Freight", "Luxury"])
            t_seats = st.number_input("Total Capacity", min_value=10, max_value=1000, value=300)
            if st.form_submit_button("DEPLOY ASSET"):
                db.add_train(t_num, t_name, t_type, t_seats)
                st.success(f"Train {t_name} deployed successfully!")
                st.rerun()

    trains = db.get_trains()
    if trains:
        df_trains = pd.DataFrame(trains)
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.dataframe(df_trains, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("No locomotive assets found in database.")

# === TRAFFIC CONTROL ===
elif menu == "📅 Traffic Control":
    st.markdown("<p class='header-subtitle'>Logistics & Schedules</p>", unsafe_allow_html=True)
    st.markdown("<h1 class='header-title'>Live Schedules</h1>", unsafe_allow_html=True)
    
    with st.expander("📅 Create New Schedule"):
        trains = db.get_trains()
        stations = db.get_stations()
        if trains and stations:
            with st.form("add_sched_form"):
                t_id = st.selectbox("Select Train", options=[t['id'] for t in trains], format_func=lambda x: next(t['name'] for t in trains if t['id']==x))
                o_id = st.selectbox("Origin Station", options=[s['id'] for s in stations], format_func=lambda x: next(s['name'] for s in stations if s['id']==x))
                d_id = st.selectbox("Destination Station", options=[s['id'] for s in stations], format_func=lambda x: next(s['name'] for s in stations if s['id']==x))
                dep = st.text_input("Departure Time (e.g. 10:00 AM)")
                arr = st.text_input("Arrival Time (e.g. 04:00 PM)")
                price = st.number_input("Ticket Price (PKR)", min_value=0.0, value=1500.0)
                if st.form_submit_button("CONFIRM SCHEDULE"):
                    db.add_schedule(t_id, o_id, d_id, dep, arr, price)
                    st.success("Schedule confirmed and broadcasted.")
                    st.rerun()
        else:
            st.error("Please add Trains and Stations first.")

    schedules = db.get_schedules()
    if schedules:
        for s in schedules:
            st.markdown(f"""
                <div class='glass-card' style='border-left: 5px solid #f59e0b;'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <div>
                            <span style='font-size:0.8rem; color:#38bdf8; font-weight:700;'>{s['train_number']}</span>
                            <h3 style='margin:0; color:#fff;'>{s['train_name']}</h3>
                        </div>
                        <div style='text-align:right;'>
                            <div style='font-size:1.2rem; font-weight:800; color:#f59e0b;'>Rs.{s['price']:,.0f}</div>
                            <span style='font-size:0.7rem; opacity:0.6;'>STANDARD FARE</span>
                        </div>
                    </div>
                    <div style='margin-top:15px; display:flex; gap:30px; font-family:"JetBrains Mono";'>
                        <div>
                            <div style='font-size:0.7rem; color:#94a3b8;'>ORIGIN</div>
                            <div style='font-weight:700;'>{s['origin_name']}</div>
                            <div style='color:#38bdf8;'>{s['departure_time']}</div>
                        </div>
                        <div style='display:flex; align-items:center; opacity:0.3;'> ➔ </div>
                        <div>
                            <div style='font-size:0.7rem; color:#94a3b8;'>DESTINATION</div>
                            <div style='font-weight:700;'>{s['destination_name']}</div>
                            <div style='color:#38bdf8;'>{s['arrival_time']}</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No active schedules found.")

# === TICKET TERMINAL ===
elif menu == "🎫 Ticket Terminal":
    st.markdown("<p class='header-subtitle'>Passenger Interface</p>", unsafe_allow_html=True)
    st.markdown("<h1 class='header-title'>Booking Terminal</h1>", unsafe_allow_html=True)
    
    col_a, col_b = st.columns([1, 1.5])
    
    with col_a:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("New Booking")
        schedules = db.get_schedules()
        if schedules:
            with st.form("booking_form"):
                s_id = st.selectbox("Select Route", options=[s['id'] for s in schedules], 
                                   format_func=lambda x: next(f"{s['train_name']} ({s['origin_name']} -> {s['destination_name']})" for s in schedules if s['id']==x))
                p_name = st.text_input("Passenger Name")
                p_email = st.text_input("Passenger Email")
                p_seat = st.text_input("Seat Preference (e.g. B-45)")
                if st.form_submit_button("ISSUE TICKET"):
                    db.add_booking(s_id, p_name, p_email, p_seat)
                    st.balloons()
                    st.success(f"Ticket Issued for {p_name}")
                    st.rerun()
        else:
            st.warning("No routes available for booking.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Manifest (Recent Bookings)")
        bookings = db.get_bookings()
        if bookings:
            df_b = pd.DataFrame(bookings)
            st.dataframe(df_b[['passenger_name', 'train_name', 'origin', 'destination', 'seat_number', 'status']], use_container_width=True)
        else:
            st.caption("No bookings on record.")
        st.markdown("</div>", unsafe_allow_html=True)

# === STATION NETWORK ===
elif menu == "📍 Station Network":
    st.markdown("<p class='header-subtitle'>Infrastructure</p>", unsafe_allow_html=True)
    st.markdown("<h1 class='header-title'>Station Grid</h1>", unsafe_allow_html=True)
    
    with st.expander("➕ Register New Station"):
        with st.form("add_station_form"):
            s_code = st.text_input("Station Code (e.g. GJP)")
            s_name = st.text_input("Station Name")
            s_city = st.text_input("City")
            if st.form_submit_button("ACTIVATE STATION"):
                db.add_station(s_code, s_name, s_city)
                st.success(f"Station {s_name} added to grid.")
                st.rerun()
                
    stations = db.get_stations()
    if stations:
        cols = st.columns(3)
        for i, s in enumerate(stations):
            with cols[i % 3]:
                st.markdown(f"""
                    <div class='glass-card' style='text-align:center; padding:15px;'>
                        <div style='font-size:2rem;'>🚉</div>
                        <div style='font-weight:800; color:#f59e0b; font-size:1.2rem;'>{s['code']}</div>
                        <div style='font-weight:600;'>{s['name']}</div>
                        <div style='font-size:0.7rem; opacity:0.6;'>{s['city']}</div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Station grid is currently empty.")

# === FOOTER ===
st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)
st.markdown("""
    <div style='text-align:center; opacity:0.3; font-size:0.7rem; letter-spacing:2px;'>
        POWERED BY RAILFLOW INTELLIGENCE UNIT &copy; 2026
    </div>
""", unsafe_allow_html=True)
