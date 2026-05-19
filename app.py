import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
from modules import db

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Sidekick CRM", page_icon="🤝", layout="wide",
                   initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

:root {
    --bg-color: #030303;
    --surface-color: #0A0A0B;
    --border-color: rgba(255, 255, 255, 0.08);
    --text-primary: #F4F4F5;
    --text-secondary: #A1A1AA;
    --accent-solid: #FFFFFF;
}

/* Global modifications */
html, body, .stApp {
    background-color: var(--bg-color) !important;
    background-image: 
        radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.04) 0%, transparent 70%),
        radial-gradient(circle at 50% 100%, rgba(255, 255, 255, 0.02) 0%, transparent 50%) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: #050505 !important;
    border-right: 1px solid var(--border-color) !important;
}

section[data-testid="stSidebar"] .stRadio > label {
    display: none !important;
}

/* Sidebar active indicators */
section[data-testid="stSidebar"] div[role="radiogroup"] {
    gap: 4px;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label {
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 6px !important;
    padding: 12px 16px !important;
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    color: var(--text-primary) !important;
    background: rgba(255, 255, 255, 0.03) !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
    color: #000000 !important;
    background: var(--accent-solid) !important;
    font-weight: 600 !important;
}

/* Premium cards */
.card {
    background: var(--surface-color) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 12px !important;
    padding: 32px !important;
    margin-bottom: 24px !important;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5) !important;
    transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.4s ease !important;
}

.card:hover {
    border-color: rgba(255, 255, 255, 0.15) !important;
    transform: translateY(-2px) !important;
}

.metric-val {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 3.2rem !important;
    font-weight: 700 !important;
    letter-spacing: -1.5px !important;
    color: var(--text-primary) !important;
    line-height: 1.1 !important;
}

.metric-lbl {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    color: var(--text-secondary) !important;
    margin-top: 8px !important;
}

.page-title {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 2.5rem !important;
    font-weight: 700 !important;
    letter-spacing: -1px !important;
    color: var(--text-primary) !important;
    margin-bottom: 40px !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 16px;
}

/* Badges */
.badge {
    display: inline-block !important;
    padding: 6px 14px !important;
    border-radius: 4px !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    border: 1px solid var(--border-color) !important;
    background: #111111 !important;
    color: var(--text-primary) !important;
}

.badge-hot, .badge-warm, .badge-cold, .badge-new, .badge-progress, .badge-closed {
    /* Unifying badges for a sleek, serious monochrome look */
    background: #0A0A0B !important; 
    color: #E4E4E7 !important; 
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
}

.badge-hot { border-color: rgba(244, 63, 94, 0.5) !important; color: #f43f5e !important; }
.badge-progress { border-color: rgba(16, 185, 129, 0.5) !important; color: #10b981 !important; }

/* Buttons */
.stButton>button {
    background: var(--accent-solid) !important;
    color: #000000 !important;
    border: none !important;
    padding: 14px 28px !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
}

.stButton>button:hover {
    background: #E4E4E7 !important;
    transform: scale(1.02) !important;
}

/* Forms and containers */
div[data-testid="stForm"], .stExpander {
    background: var(--surface-color) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 12px !important;
    padding: 24px !important;
}

/* Inputs, Selectboxes, Textareas */
.stTextInput>div>div>input, .stSelectbox>div>div, .stTextArea>div>div>textarea {
    background: #000000 !important;
    border: 1px solid var(--border-color) !important;
    color: var(--text-primary) !important;
    border-radius: 6px !important;
    padding: 12px 16px !important;
    transition: all 0.3s !important;
}

.stTextInput>div>div>input:focus, .stSelectbox>div>div:focus-within, .stTextArea>div>div>textarea:focus {
    border-color: rgba(255, 255, 255, 0.3) !important;
    box-shadow: none !important;
    background: #050505 !important;
}

/* Dataframe & Tables */
.stDataFrame, div[data-testid="stTable"] {
    border-radius: 8px !important;
    overflow: hidden !important;
    border: 1px solid var(--border-color) !important;
}

hr {
    border-color: var(--border-color) !important;
}
</style>
""", unsafe_allow_html=True)

# ── DB Init ───────────────────────────────────────────────────────────────────
db.init_db()

DEFAULTS = {
    "smtp_host": "smtp.gmail.com", "smtp_port": 587,
    "smtp_user": "", "smtp_pass": "", "notify_email": "",
    "gemini_api_key": "", "auto_reminders": False, "last_auto_run": ""
}

# ── Auth ──────────────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None

def logout():
    st.session_state.user = None
    st.rerun()

if not st.session_state.user:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center;margin-bottom:32px;'>
            <div style='font-size:3.5rem;font-weight:700;letter-spacing:-2px;font-family:"Space Grotesk", sans-serif;color:#FFFFFF;'>S.</div>
            <h1 style='font-size:2rem;font-weight:700;color:#F4F4F5;margin:8px 0 0 0;font-family:"Space Grotesk", sans-serif;letter-spacing:-1px;'>Sidekick CRM</h1>
            <p style='color:#A1A1AA;font-size:.75rem;letter-spacing:3px;text-transform:uppercase;margin-top:8px;'>Secure Access</p>
        </div>
        """, unsafe_allow_html=True)
        with st.form("login"):
            username = st.text_input("Username", placeholder="admin")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            if st.form_submit_button("Sign In →", use_container_width=True):
                user = db.verify_user(username, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
user = st.session_state.user
role = user.get("role", "User")

with st.sidebar:
    st.markdown(f"""
    <div style='text-align:center;padding:16px 0 32px;'>
        <div style='font-size:2.5rem;font-weight:700;letter-spacing:-2px;font-family:"Space Grotesk", sans-serif;color:#FFFFFF;'>S.</div>
        <h2 style='color:#F4F4F5;margin:4px 0;font-size:1.2rem;font-family:"Space Grotesk", sans-serif;letter-spacing:-0.5px;'>Sidekick</h2>
        <p style='color:#A1A1AA;font-size:.65rem;letter-spacing:3px;text-transform:uppercase;'>System Core</p>
    </div>
    <div class='card' style='text-align:center;padding:16px;margin-bottom:24px;border-radius:8px;'>
        <div style='font-weight:600;font-size:.9rem;color:#F4F4F5;letter-spacing:0.5px;'>{user['username']}</div>
        <div style='color:#A1A1AA;font-size:.7rem;text-transform:uppercase;letter-spacing:1px;margin-top:4px;'>{role}</div>
    </div>
    """, unsafe_allow_html=True)

    pages = ["📊 Dashboard", "👥 Leads", "✅ Tasks", "💰 Sales", "📧 Campaigns", "⚙️ Settings"]
    if role == "Admin":
        pages.append("🔑 Users")
    menu = st.radio("Navigation", pages, label_visibility="collapsed")
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        logout()

# ── Dashboard ─────────────────────────────────────────────────────────────────
if menu == "📊 Dashboard":
    st.markdown("<p class='page-title'>Dashboard</p>", unsafe_allow_html=True)
    leads = db.get_all_leads()
    tasks = db.get_all_tasks()
    sales = db.get_all_sales()

    total_rev = sum(s.get("amount", 0) for s in sales)
    open_leads = [l for l in leads if l.get("status") != "Closed"]
    pending_tasks = [t for t in tasks if not t.get("done")]

    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl in [
        (c1, len(leads), "Total Leads"),
        (c2, len(open_leads), "Active Leads"),
        (c3, len(pending_tasks), "Pending Tasks"),
        (c4, f"${total_rev:,.0f}", "Total Revenue"),
    ]:
        with col:
            st.markdown(f"<div class='card' style='text-align:center;'><div class='metric-val'>{val}</div><div class='metric-lbl'>{lbl}</div></div>", unsafe_allow_html=True)

    col_l, col_r = st.columns([2, 1])
    with col_l:
        if sales:
            df_s = pd.DataFrame(sales)
            df_s["amount"] = pd.to_numeric(df_s["amount"], errors="coerce")
            monthly = df_s.groupby("month_year")["amount"].sum().reset_index().sort_values("month_year")
            fig = px.area(monthly, x="month_year", y="amount", title="Revenue Over Time",
                          color_discrete_sequence=["#FFFFFF"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font_color="white", title_font_color="white")
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        if leads:
            df_l = pd.DataFrame(leads)
            status_counts = df_l["status"].value_counts()
            fig2 = px.pie(values=status_counts.values, names=status_counts.index,
                          hole=0.6, title="Lead Status",
                          color_discrete_sequence=["#FFFFFF", "#A1A1AA", "#52525B", "#27272A"])
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                               title_font_color="white", showlegend=True)
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # Recent leads table
    if leads:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Recent Leads")
        df = pd.DataFrame(leads[:10])[["name", "company", "status", "temperature", "source", "followup_date"]]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ── Leads ─────────────────────────────────────────────────────────────────────
elif menu == "👥 Leads":
    st.markdown("<p class='page-title'>Leads Pipeline</p>", unsafe_allow_html=True)

    with st.expander("➕ Add New Lead"):
        with st.form("add_lead"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Full Name *")
            company = c2.text_input("Company")
            c3, c4 = st.columns(2)
            email = c3.text_input("Email")
            phone = c4.text_input("Phone")
            c5, c6, c7 = st.columns(3)
            status = c5.selectbox("Status", ["New", "In Progress", "Closed"])
            temp = c6.selectbox("Temperature", ["Hot", "Warm", "Cold"])
            source = c7.selectbox("Source", ["Manual Entry", "Website", "Referral", "Ads", "Other"])
            followup = st.date_input("Follow-up Date", value=date.today())
            notes = st.text_area("Notes")
            if st.form_submit_button("Add Lead", use_container_width=True):
                if name:
                    db.add_lead({"name": name, "company": company, "email": email,
                                 "phone": phone, "status": status, "temperature": temp,
                                 "source": source, "followup_date": str(followup),
                                 "notes": notes, "created_at": str(datetime.now())})
                    st.success(f"✅ Lead '{name}' added!")
                    st.rerun()
                else:
                    st.error("Name is required.")

    # Filters
    leads = db.get_all_leads()
    col_f1, col_f2, col_f3 = st.columns(3)
    search = col_f1.text_input("🔍 Search", placeholder="Name or company...")
    filter_status = col_f2.selectbox("Status Filter", ["All", "New", "In Progress", "Closed"])
    filter_temp = col_f3.selectbox("Temperature Filter", ["All", "Hot", "Warm", "Cold"])

    filtered = leads
    if search:
        filtered = [l for l in filtered if search.lower() in (l.get("name","") + l.get("company","")).lower()]
    if filter_status != "All":
        filtered = [l for l in filtered if l.get("status") == filter_status]
    if filter_temp != "All":
        filtered = [l for l in filtered if l.get("temperature") == filter_temp]

    st.markdown(f"**{len(filtered)} leads found**")

    for lead in filtered:
        temp_badge = {"Hot": "badge-hot", "Warm": "badge-warm", "Cold": "badge-cold"}.get(lead.get("temperature",""), "badge-new")
        stat_badge = {"New": "badge-new", "In Progress": "badge-progress", "Closed": "badge-closed"}.get(lead.get("status",""), "badge-new")
        with st.expander(f"🧑 {lead['name']} — {lead.get('company','N/A')} | {lead.get('status','')} | {lead.get('temperature','')}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"""
                <span class='badge {stat_badge}'>{lead.get('status','')}</span>
                <span class='badge {temp_badge}'>{lead.get('temperature','')}</span>
                <br><br>
                📧 {lead.get('email','—')} &nbsp; 📞 {lead.get('phone','—')} &nbsp; 🌐 {lead.get('source','—')}<br>
                📅 Follow-up: <b>{lead.get('followup_date','—')}</b><br>
                📝 {lead.get('notes','—')}
                """, unsafe_allow_html=True)
            with c2:
                with st.form(f"edit_{lead['id']}"):
                    new_status = st.selectbox("Update Status", ["New", "In Progress", "Closed"],
                                              index=["New", "In Progress", "Closed"].index(lead.get("status", "New")))
                    new_temp = st.selectbox("Temperature", ["Hot", "Warm", "Cold"],
                                            index=["Hot", "Warm", "Cold"].index(lead.get("temperature", "Warm")))
                    new_notes = st.text_area("Notes", value=lead.get("notes", ""))
                    if st.form_submit_button("Save"):
                        db.update_lead(lead["id"], {"status": new_status, "temperature": new_temp, "notes": new_notes})
                        st.success("Updated!")
                        st.rerun()
                if st.button("🗑 Delete", key=f"del_lead_{lead['id']}"):
                    db.delete_lead(lead["id"])
                    st.rerun()

# ── Tasks ─────────────────────────────────────────────────────────────────────
elif menu == "✅ Tasks":
    st.markdown("<p class='page-title'>Tasks</p>", unsafe_allow_html=True)
    leads = db.get_all_leads()
    lead_map = {l["id"]: l["name"] for l in leads}

    with st.expander("➕ Add New Task"):
        with st.form("add_task"):
            c1, c2 = st.columns(2)
            title = c1.text_input("Task Title *")
            priority = c2.selectbox("Priority", ["High", "Medium", "Low"])
            lead_id = st.selectbox("Linked Lead", [None] + [l["id"] for l in leads],
                                   format_func=lambda x: "None" if x is None else lead_map.get(x, str(x)))
            due = st.date_input("Due Date", value=date.today())
            desc = st.text_area("Description")
            if st.form_submit_button("Add Task", use_container_width=True):
                if title:
                    db.add_task({"title": title, "priority": priority, "lead_id": lead_id,
                                 "due_date": str(due), "description": desc,
                                 "done": False, "status": "Pending", "created_at": str(datetime.now())})
                    st.success("✅ Task added!")
                    st.rerun()

    tasks = db.get_all_tasks()
    t_filter = st.radio("Filter", ["All", "Pending", "Completed"], horizontal=True)
    if t_filter == "Pending":
        tasks = [t for t in tasks if not t.get("done")]
    elif t_filter == "Completed":
        tasks = [t for t in tasks if t.get("done")]

    for task in tasks:
        pri_color = {"High": "#f87171", "Medium": "#fb923c", "Low": "#4ade80"}.get(task.get("priority", "Medium"), "#94a3b8")
        done = task.get("done", False)
        icon = "✅" if done else "🔲"
        linked = lead_map.get(task.get("lead_id"), "—")
        with st.expander(f"{icon} [{task.get('priority','')}] {task['title']} | Due: {task.get('due_date','—')} | Lead: {linked}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"<span style='color:{pri_color};font-weight:700;'>{task.get('priority','')} Priority</span>", unsafe_allow_html=True)
                st.write(task.get("description", "No description."))
            with c2:
                if not done:
                    if st.button("Mark Done ✅", key=f"done_{task['id']}"):
                        db.update_task(task["id"], {"done": True, "status": "Completed"})
                        st.rerun()
                if st.button("🗑 Delete", key=f"del_task_{task['id']}"):
                    db.delete_task(task["id"])
                    st.rerun()

# ── Sales ─────────────────────────────────────────────────────────────────────
elif menu == "💰 Sales":
    st.markdown("<p class='page-title'>Sales Report</p>", unsafe_allow_html=True)
    sales = db.get_all_sales()

    with st.expander("➕ Add Sale Entry"):
        with st.form("add_sale"):
            c1, c2, c3 = st.columns(3)
            month = c1.text_input("Month (YYYY-MM)", value=datetime.now().strftime("%Y-%m"))
            category = c2.selectbox("Category", ["Software License", "Professional Services",
                                                   "System Integration", "Cloud Hosting", "Training & Support", "Other"])
            client = c3.text_input("Client Name")
            amount = st.number_input("Amount ($)", min_value=0.0, value=0.0)
            notes = st.text_area("Notes")
            if st.form_submit_button("Add Entry", use_container_width=True):
                if client:
                    db.add_sale({"month_year": month, "category": category, "client": client,
                                 "amount": amount, "notes": notes, "created_at": str(datetime.now())})
                    st.success("✅ Sale entry added!")
                    st.rerun()

    if sales:
        df = pd.DataFrame(sales)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

        total = df["amount"].sum()
        best_client = df.groupby("client")["amount"].sum().idxmax() if not df.empty else "—"

        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='card' style='text-align:center;'><div class='metric-val'>${total:,.0f}</div><div class='metric-lbl'>Total Revenue</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='card' style='text-align:center;'><div class='metric-val'>{len(sales)}</div><div class='metric-lbl'>Total Entries</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='card' style='text-align:center;'><div class='metric-val' style='font-size:1.2rem;'>{best_client}</div><div class='metric-lbl'>Top Client</div></div>", unsafe_allow_html=True)

        col_l, col_r = st.columns(2)
        with col_l:
            monthly = df.groupby("month_year")["amount"].sum().reset_index().sort_values("month_year")
            fig = px.bar(monthly, x="month_year", y="amount", title="Monthly Revenue",
                         color_discrete_sequence=["#FFFFFF"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)
        with col_r:
            cat = df.groupby("category")["amount"].sum().reset_index()
            fig2 = px.pie(cat, values="amount", names="category", hole=0.5, title="Revenue by Category",
                          color_discrete_sequence=["#FFFFFF", "#D4D4D8", "#A1A1AA", "#71717A", "#52525B", "#3F3F46"])
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("All Sales Entries")
        st.dataframe(df[["month_year", "client", "category", "amount", "notes"]],
                     use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No sales data yet. Add your first entry above.")

# ── Campaigns ─────────────────────────────────────────────────────────────────
elif menu == "📧 Campaigns":
    st.markdown("<p class='page-title'>Email Campaigns</p>", unsafe_allow_html=True)
    tabs = st.tabs(["📋 Templates", "🚀 Campaigns"])

    with tabs[0]:
        templates = db.get_all_templates()
        with st.expander("➕ New Template"):
            with st.form("add_tmpl"):
                name = st.text_input("Template Name")
                subject = st.text_input("Email Subject")
                body = st.text_area("Email Body (HTML supported)", height=200)
                if st.form_submit_button("Save Template"):
                    if name:
                        db.add_template({"name": name, "subject": subject, "body": body,
                                         "created_at": str(datetime.now())})
                        st.success("Template saved!")
                        st.rerun()

        for t in templates:
            with st.expander(f"📄 {t['name']}"):
                st.write(f"**Subject:** {t.get('subject','')}")
                st.text_area("Body", value=t.get("body", ""), height=100, disabled=True, key=f"tmpl_{t['id']}")
                if st.button("🗑 Delete", key=f"del_tmpl_{t['id']}"):
                    db.delete_template(t["id"])
                    st.rerun()

    with tabs[1]:
        campaigns = db.get_all_campaigns()
        templates = db.get_all_templates()
        with st.expander("➕ New Campaign"):
            with st.form("add_camp"):
                cname = st.text_input("Campaign Name")
                tmpl = st.selectbox("Template", [t["id"] for t in templates],
                                    format_func=lambda x: next((t["name"] for t in templates if t["id"] == x), str(x))) if templates else None
                if st.form_submit_button("Create Campaign"):
                    if cname and tmpl:
                        t_obj = next((t for t in templates if t["id"] == tmpl), {})
                        db.add_campaign({"name": cname, "template_id": tmpl,
                                         "subject": t_obj.get("subject", ""),
                                         "body": t_obj.get("body", ""),
                                         "status": "Scheduled", "created_at": str(datetime.now())})
                        st.success("Campaign created!")
                        st.rerun()

        for c in campaigns:
            st.markdown(f"""<div class='card'>
            <b>{c['name']}</b> &nbsp; <span class='badge badge-new'>{c.get('status','')}</span><br>
            <small>Sent: {c.get('stats_sent',0)} | Failed: {c.get('stats_failed',0)}</small>
            </div>""", unsafe_allow_html=True)

# ── Settings ──────────────────────────────────────────────────────────────────
elif menu == "⚙️ Settings":
    st.markdown("<p class='page-title'>Settings</p>", unsafe_allow_html=True)
    settings = db.get_settings(DEFAULTS)

    with st.form("settings_form"):
        st.subheader("📬 SMTP / Email")
        c1, c2 = st.columns(2)
        smtp_host = c1.text_input("SMTP Host", value=settings.get("smtp_host", "smtp.gmail.com"))
        smtp_port = c2.number_input("SMTP Port", value=int(settings.get("smtp_port", 587)))
        c3, c4 = st.columns(2)
        smtp_user = c3.text_input("SMTP Username / Email", value=settings.get("smtp_user", ""))
        smtp_pass = c4.text_input("SMTP Password / App Password", type="password", value=settings.get("smtp_pass", ""))
        notify_email = st.text_input("Notification Email", value=settings.get("notify_email", ""))

        st.subheader("🤖 AI")
        gemini_key = st.text_input("Gemini API Key", type="password", value=settings.get("gemini_api_key", ""))

        if st.form_submit_button("💾 Save Settings", use_container_width=True):
            db.save_settings({
                "smtp_host": smtp_host, "smtp_port": smtp_port,
                "smtp_user": smtp_user, "smtp_pass": smtp_pass,
                "notify_email": notify_email, "gemini_api_key": gemini_key
            })
            st.success("✅ Settings saved!")

    st.markdown("---")
    st.subheader("🗃 Data Management")
    if st.button("🌱 Generate Sample Data"):
        with st.spinner("Generating..."):
            db.generate_dummy_data()
        st.success("Sample data generated!")
        st.rerun()

# ── Users (Admin) ─────────────────────────────────────────────────────────────
elif menu == "🔑 Users" and role == "Admin":
    st.markdown("<p class='page-title'>User Management</p>", unsafe_allow_html=True)
    users = db.get_all_users()

    with st.expander("➕ Add New User"):
        with st.form("add_user"):
            c1, c2, c3 = st.columns(3)
            uname = c1.text_input("Username")
            upass = c2.text_input("Password", type="password")
            urole = c3.selectbox("Role", ["User", "Admin"])
            if st.form_submit_button("Add User"):
                if uname and upass:
                    db.add_user({"username": uname, "password": upass, "role": urole,
                                 "allowed_pages": "all", "created_at": str(datetime.now())})
                    st.success(f"User '{uname}' created!")
                    st.rerun()

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    for u in users:
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.markdown(f"**{u['username']}** — {u.get('role','User')}")
        c2.caption(f"Created: {str(u.get('created_at',''))[:10]}")
        if u["username"] != user["username"]:
            if c3.button("🗑", key=f"del_u_{u['id']}"):
                db.delete_user(u["id"])
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
