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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
:root{--primary:#6366f1;--primary-light:#818cf8;--bg:#0f172a;--card:rgba(30,41,59,0.8);--border:rgba(99,102,241,0.2);--text:#f1f5f9;--muted:#94a3b8;}
html,body,.stApp{background:#0f172a!important;color:var(--text)!important;font-family:'Inter',sans-serif!important;}
section[data-testid="stSidebar"]{background:rgba(15,23,42,0.97)!important;border-right:1px solid var(--border);}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;margin-bottom:16px;backdrop-filter:blur(10px);transition:all .3s;}
.card:hover{border-color:var(--primary);box-shadow:0 8px 32px rgba(99,102,241,.15);transform:translateY(-2px);}
.metric-val{font-size:2.4rem;font-weight:800;color:var(--primary-light);}
.metric-lbl{font-size:.75rem;text-transform:uppercase;letter-spacing:2px;color:var(--muted);}
.page-title{font-size:2.2rem;font-weight:800;background:linear-gradient(135deg,#fff,#94a3b8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:.7rem;font-weight:700;}
.badge-hot{background:rgba(239,68,68,.2);color:#f87171;}
.badge-warm{background:rgba(251,146,60,.2);color:#fb923c;}
.badge-cold{background:rgba(96,165,250,.2);color:#60a5fa;}
.badge-new{background:rgba(99,102,241,.2);color:#818cf8;}
.badge-progress{background:rgba(34,197,94,.2);color:#4ade80;}
.badge-closed{background:rgba(148,163,184,.2);color:#94a3b8;}
.stButton>button{border-radius:10px!important;font-weight:600!important;transition:all .3s!important;}
div[data-testid="stForm"]{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;}
.stTextInput>div>div>input,.stSelectbox>div>div,.stTextArea>div>div>textarea{background:rgba(30,41,59,0.9)!important;border:1px solid var(--border)!important;color:var(--text)!important;border-radius:10px!important;}
.stDataFrame{border-radius:12px;overflow:hidden;}
hr{border-color:var(--border)!important;}
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
            <div style='font-size:3rem;'>🤝</div>
            <h1 style='font-size:2rem;font-weight:800;color:#6366f1;margin:0;'>Sidekick CRM</h1>
            <p style='color:#94a3b8;font-size:.85rem;letter-spacing:2px;'>SIGN IN TO CONTINUE</p>
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
    <div style='text-align:center;padding:16px 0 24px;'>
        <div style='font-size:2rem;'>🤝</div>
        <h2 style='color:#6366f1;margin:4px 0;font-size:1.4rem;'>Sidekick CRM</h2>
        <p style='color:#94a3b8;font-size:.7rem;letter-spacing:2px;'>INTELLIGENCE PLATFORM</p>
    </div>
    <div class='card' style='text-align:center;padding:12px;margin-bottom:16px;'>
        <div style='font-weight:700;font-size:.95rem;'>👤 {user['username']}</div>
        <div style='color:#818cf8;font-size:.75rem;'>{role}</div>
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
                          color_discrete_sequence=["#6366f1"])
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
                          color_discrete_sequence=["#6366f1", "#818cf8", "#a5b4fc", "#c7d2fe"])
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
                         color_discrete_sequence=["#6366f1"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)
        with col_r:
            cat = df.groupby("category")["amount"].sum().reset_index()
            fig2 = px.pie(cat, values="amount", names="category", hole=0.5, title="Revenue by Category",
                          color_discrete_sequence=px.colors.sequential.Purp)
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
