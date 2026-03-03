import smtplib
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import google.generativeai as genai
from modules import db

def send_email(settings, subject, body, to_email):
    # Auto-wrap raw text if it's not already HTML
    # (Note: automation.py hardcoded emails already start with <div, so they skip this)
    if not (body.strip().startswith("<") or "<html>" in body.lower()):
        # Since automation.py is separate, we'd need the layout here. 
        # But usually automation uses hardcoded HTML. Let's just make it safe.
        pass

    if not all([settings.get("smtp_user"), settings.get("smtp_pass"), to_email]):
        print(f"Skipping email to {to_email}: SMTP not configured properly.")
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = settings["smtp_user"]
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        
        with smtplib.SMTP(settings["smtp_host"], int(settings["smtp_port"])) as server:
            server.starttls()
            server.login(settings["smtp_user"], settings["smtp_pass"])
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email to {to_email}: {e}")
        return False

def generate_ai_followup(lead, api_key):
    if not api_key:
        print("AI Skip: No API Key found.")
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        history_context = ""
        last_date = lead.get('last_followup_date', 'N/A')
        last_notes = lead.get('last_followup_notes', 'N/A')
        
        if lead.get("last_followup_notes"):
            history_context = f"Last interaction ({last_date}): {last_notes}"
        else:
            history_context = "No previous history."

        prompt = f"""
        Lead: {lead['name']} ({lead.get('company', 'N/A')})
        Status: {lead.get('status', 'New')}
        Notes: {lead.get('notes', 'N/A')}
        History: {history_context}
        
        Write a short (2-3 sentence) follow-up message to send today. 
        Refer to pichli baat (last interaction) if available.
        Just the message body text.
        """
        response = model.generate_content(prompt)
        msg = response.text.replace('"', '').strip()
        return msg
    except Exception as e:
        print(f"AI Generation Error for {lead['name']}: {e}")
        return None

def run_reminders():
    print(f"Running automated reminders at {datetime.now()}")
    
    tasks = db.get_all_tasks()
    leads = db.get_all_leads()
    settings = db.get_settings({
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_pass": "",
        "notify_email": "",
        "gemini_api_key": "",
        "auto_reminders": True,
        "last_auto_run": ""
    })
    
    if not settings.get("smtp_user"):
        print("No SMTP settings found. Please configure in the app.")
        return

    gemini_key = settings.get("gemini_api_key")
    today_date = datetime.now().date()
    emails_sent = 0
    tasks_processed = 0
    leads_processed = 0

    # 1. PROCESS TASKS
    lead_map = {l["id"]: l["name"] for l in leads}
    pending_tasks = [t for t in tasks if not t.get("done")]
    
    for task in pending_tasks:
        target_email = task.get("remind_email") or settings.get("notify_email")
        if target_email:
            lead_name = lead_map.get(task.get("lead_id"), "N/A")
            subject = f"🔔 Task Reminder: {task['title']}"
            body = f"""
            <div style='font-family: sans-serif; border: 1px solid #1b6656; border-radius: 10px; padding: 20px; max-width: 600px;'>
                <h2 style='color: #1b6656;'>Task Reminder</h2>
                <p>This is an automated reminder for your pending task.</p>
                <hr>
                <p><b>Task:</b> {task['title']}</p>
                <p><b>Lead:</b> {lead_name}</p>
                <p><b>Priority:</b> {task.get('priority', 'Medium')}</p>
                <p><b>Due Date:</b> {task.get('due_date', 'N/A')}</p>
                <p><b>Description:</b> {task.get('description', 'N/A')}</p>
                <hr>
                <p style='color: #666; font-size: 12px;'>Mark as 'Completed' in CRM to stop these reminders.</p>
                <p style='color: #999; font-size: 10px;'>Sent from Sidekick Tasks</p>
            </div>
            """
            if send_email(settings, subject, body, target_email):
                print(f"Sent task reminder for {task['title']}")
                emails_sent += 1
            tasks_processed += 1

    # 2. PROCESS LEADS (Follow-ups)
    for lead in leads:
        f_date_str = lead.get("followup_date")
        if not f_date_str or lead.get("status") == "Closed":
            continue
            
        try:
            f_date = datetime.strptime(f_date_str, "%Y-%m-%d").date()
            if f_date <= today_date:
                target_email = lead.get("remind_email") or settings.get("notify_email")
                if target_email:
                    # Generate AI Suggestion
                    ai_suggestion = generate_ai_followup(lead, gemini_key) if gemini_key else None
                    
                    subject = f"👥 Lead Follow-up: {lead['name']}"
                    ai_section = f"""
                        <div style='background: #f0f7ff; border: 1px dashed #1d4354; border-radius: 8px; padding: 15px; margin: 15px 0;'>
                            <h4 style='color: #1d4354; margin-top: 0;'>✨ Gemini AI Suggestion:</h4>
                            <p style='font-style: italic; color: #333;'>"{ai_suggestion or 'AI suggestion currently unavailable.'}"</p>
                        </div>
                    """
                    
                    body = f"""
                    <div style='font-family: sans-serif; border: 1px solid #1d4354; border-radius: 10px; padding: 20px; max-width: 600px;'>
                        <h2 style='color: #1d4354;'>Lead Follow-up Reminder</h2>
                        <p>It's time to follow up with this lead. Here is a custom draft by Gemini AI based on your last interaction:</p>
                        <hr>
                        {ai_section}
                        <p><b>Lead Name:</b> {lead['name']}</p>
                        <p><b>Company:</b> {lead.get('company', 'N/A')}</p>
                        <p><b>Status:</b> {lead.get('status', 'New')}</p>
                        <p><b>Last Interaction:</b> {lead.get('last_followup_date', 'N/A')} - {lead.get('last_followup_notes', 'N/A')}</p>
                        <p><b>Scheduled Follow-up:</b> {f_date_str}</p>
                        <p><b>General Notes:</b> {lead.get('notes', 'N/A')}</p>
                        <hr>
                        <p style='color: #666; font-size: 12px;'>Update the 'Follow-up Date' or close the lead in CRM to stop these reminders.</p>
                        <p style='color: #999; font-size: 10px;'>Sent from Sidekick Tasks</p>
                    </div>
                    """
                    if send_email(settings, subject, body, target_email):
                        print(f"Sent lead follow-up reminder for {lead['name']}")
                        emails_sent += 1
                    leads_processed += 1
        except Exception as e:
            print(f"Error processing lead {lead.get('id')}: {e}")

    # Log the run
    db.add_log(emails_sent, tasks_processed, leads_processed)
    print(f"Summary: Sent {emails_sent} emails (Tasks: {tasks_processed}, Leads: {leads_processed})")

if __name__ == "__main__":
    run_reminders()
