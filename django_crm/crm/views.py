from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count
from django.http import JsonResponse
from datetime import datetime, timedelta, date
import random

from .models import CRMSetting, Lead, Task, SaleReport, EmailTemplate, Campaign, CampaignLog, FollowupLog

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            # Auto-create admin if it doesn't exist to replicate DB initialization
            if u == 'admin' and p == 'admin123':
                if not User.objects.filter(username='admin').exists():
                    user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
                    login(request, user)
                    return redirect('dashboard')
            messages.error(request, 'Invalid credentials')
    return render(request, 'crm/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard_view(request):
    leads = Lead.objects.all().order_by('-created_at')
    tasks = Task.objects.all().order_by('-created_at')
    sales = SaleReport.objects.all().order_by('-created_at')

    total_revenue = sales.aggregate(Sum('amount'))['amount__sum'] or 0
    active_leads_count = leads.exclude(status='Closed').count()
    pending_tasks_count = tasks.filter(done=False).count()

    # Dynamic metrics
    metrics = {
        'total_leads': leads.count(),
        'active_leads': active_leads_count,
        'pending_tasks': pending_tasks_count,
        'total_revenue': total_revenue,
    }

    # Revenue by Month
    sales_by_month = {}
    for s in sales:
        sales_by_month[s.month_year] = sales_by_month.get(s.month_year, 0) + float(s.amount)
    
    sorted_months = sorted(sales_by_month.keys())
    revenue_chart_labels = sorted_months
    revenue_chart_data = [sales_by_month[m] for m in sorted_months]

    # Lead status pie chart data
    status_counts = list(Lead.objects.values('status').annotate(count=Count('status')))
    
    context = {
        'metrics': metrics,
        'recent_leads': leads[:8],
        'revenue_labels': revenue_chart_labels,
        'revenue_data': revenue_chart_data,
        'status_counts': status_counts,
        'active_tab': 'dashboard'
    }
    return render(request, 'crm/dashboard.html', context)

@login_required
def leads_view(request):
    leads = Lead.objects.all().order_by('-created_at')
    status_filter = request.GET.get('status', 'All')
    temp_filter = request.GET.get('temp', 'All')
    q = request.GET.get('q', '')

    if status_filter != 'All':
        leads = leads.filter(status=status_filter)
    if temp_filter != 'All':
        leads = leads.filter(temperature=temp_filter)
    if q:
        leads = leads.filter(name__icontains=q) | leads.filter(company__icontains=q)

    context = {
        'leads': leads,
        'status_filter': status_filter,
        'temp_filter': temp_filter,
        'q': q,
        'active_tab': 'leads'
    }
    return render(request, 'crm/leads.html', context)

@login_required
def add_lead_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        company = request.POST.get('company')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        status = request.POST.get('status', 'New')
        temp = request.POST.get('temperature', 'Warm')
        source = request.POST.get('source', 'Manual Entry')
        followup = request.POST.get('followup_date')
        notes = request.POST.get('notes')

        if not followup:
            followup = date.today()

        Lead.objects.create(
            name=name, company=company, email=email, phone=phone,
            status=status, temperature=temp, source=source,
            followup_date=followup, notes=notes
        )
        messages.success(request, f'Lead {name} added successfully!')
    return redirect('leads')

@login_required
def update_lead_view(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    if request.method == 'POST':
        lead.status = request.POST.get('status')
        lead.temperature = request.POST.get('temperature')
        lead.notes = request.POST.get('notes')
        lead.save()
        messages.success(request, f'Lead {lead.name} updated successfully!')
    return redirect('leads')

@login_required
def delete_lead_view(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    lead.delete()
    messages.success(request, 'Lead deleted successfully!')
    return redirect('leads')

@login_required
def tasks_view(request):
    tasks = Task.objects.all().order_by('-created_at')
    leads = Lead.objects.all()
    status = request.GET.get('status', 'All')

    if status == 'Pending':
        tasks = tasks.filter(done=False)
    elif status == 'Completed':
        tasks = tasks.filter(done=True)

    context = {
        'tasks': tasks,
        'leads': leads,
        'status_filter': status,
        'active_tab': 'tasks'
    }
    return render(request, 'crm/tasks.html', context)

@login_required
def add_task_view(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        priority = request.POST.get('priority', 'Medium')
        lead_id = request.POST.get('lead')
        due = request.POST.get('due_date')
        desc = request.POST.get('description')

        lead = None
        if lead_id:
            lead = Lead.objects.get(id=lead_id)

        if not due:
            due = date.today()

        Task.objects.create(
            title=title, priority=priority, lead=lead,
            due_date=due, description=desc
        )
        messages.success(request, 'Task added successfully!')
    return redirect('tasks')

@login_required
def complete_task_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.done = True
    task.save()
    messages.success(request, 'Task marked as completed!')
    return redirect('tasks')

@login_required
def delete_task_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    messages.success(request, 'Task deleted successfully!')
    return redirect('tasks')

@login_required
def sales_view(request):
    sales = SaleReport.objects.all().order_by('-created_at')
    total_rev = sales.aggregate(Sum('amount'))['amount__sum'] or 0

    # Sales aggregations
    category_sales = list(SaleReport.objects.values('category').annotate(total=Sum('amount')))
    top_client_data = SaleReport.objects.values('client').annotate(total=Sum('amount')).order_by('-total')
    top_client = top_client_data[0]['client'] if top_client_data else "—"

    # Monthly Sales Chart
    monthly_sales = list(SaleReport.objects.values('month_year').annotate(total=Sum('amount')).order_by('month_year'))

    context = {
        'sales': sales,
        'total_revenue': total_rev,
        'total_entries': sales.count(),
        'top_client': top_client,
        'category_sales': category_sales,
        'monthly_sales': monthly_sales,
        'active_tab': 'sales'
    }
    return render(request, 'crm/sales.html', context)

@login_required
def add_sale_view(request):
    if request.method == 'POST':
        month = request.POST.get('month_year')
        category = request.POST.get('category')
        client = request.POST.get('client')
        amount = request.POST.get('amount', 0)
        notes = request.POST.get('notes')

        SaleReport.objects.create(
            month_year=month, category=category, client=client,
            amount=amount, notes=notes
        )
        messages.success(request, 'Sale entry added successfully!')
    return redirect('sales')

@login_required
def delete_sale_view(request, sale_id):
    sale = get_object_or_404(SaleReport, id=sale_id)
    sale.delete()
    messages.success(request, 'Sale entry deleted successfully!')
    return redirect('sales')

@login_required
def campaigns_view(request):
    templates = EmailTemplate.objects.all().order_by('-created_at')
    campaigns = Campaign.objects.all().order_by('-created_at')
    context = {
        'templates': templates,
        'campaigns': campaigns,
        'active_tab': 'campaigns'
    }
    return render(request, 'crm/campaigns.html', context)

@login_required
def add_template_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        subject = request.POST.get('subject')
        body = request.POST.get('body')

        EmailTemplate.objects.create(name=name, subject=subject, body=body)
        messages.success(request, 'Email Template saved successfully!')
    return redirect('campaigns')

@login_required
def delete_template_view(request, template_id):
    template = get_object_or_404(EmailTemplate, id=template_id)
    template.delete()
    messages.success(request, 'Template deleted successfully!')
    return redirect('campaigns')

@login_required
def add_campaign_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        template_id = request.POST.get('template')

        if template_id:
            tmpl = EmailTemplate.objects.get(id=template_id)
            Campaign.objects.create(
                name=name, template=tmpl, subject=tmpl.subject, body=tmpl.body
            )
            messages.success(request, 'Campaign created successfully!')
    return redirect('campaigns')

@login_required
def settings_view(request):
    defaults = {
        "smtp_host": "smtp.gmail.com", "smtp_port": "587",
        "smtp_user": "", "smtp_pass": "", "notify_email": "",
        "gemini_api_key": ""
    }
    if request.method == 'POST':
        for key in defaults.keys():
            val = request.POST.get(key, '')
            setting, created = CRMSetting.objects.get_or_create(key=key)
            setting.value = val
            setting.save()
        messages.success(request, 'Settings saved successfully!')
        return redirect('settings')

    settings = {}
    for key, d_val in defaults.items():
        try:
            settings[key] = CRMSetting.objects.get(key=key).value
        except CRMSetting.DoesNotExist:
            settings[key] = d_val

    context = {
        'settings': settings,
        'active_tab': 'settings'
    }
    return render(request, 'crm/settings.html', context)

@login_required
def generate_dummy_data_view(request):
    # Standard dummy data generator
    lead_names = [
        "Ahmed Khan", "Sara Malik", "Zainab Ali", "Usman Sheikh", "Faizan Qureshi",
        "Ayesha Siddiqa", "Bilal Ahmed", "Hira Shah", "Imran Abbas", "Kiran Noor",
        "Muneeb Farooq", "Nida Yasir", "Omar Lodhi", "Rabia Batool", "Sami Ullah"
    ]
    companies = ["Global Tech", "Marketing Pro", "Real Estate Co", "Freelance Hub", "Retail Group", "Hospitality Solutions", "Education Inst"]
    sources = ["Website", "Referral", "Ads", "Other"]
    temps = ["Hot", "Warm", "Cold"]
    statuses = ["New", "In Progress", "Closed"]

    # Leads
    for i in range(15):
        name = lead_names[i]
        Lead.objects.create(
            name=name, company=random.choice(companies),
            email=f"{name.lower().replace(' ', '.')}@example.com",
            phone=f"03{random.randint(10, 45)}-{random.randint(1000000, 9999999)}",
            status=random.choice(statuses), temperature=random.choice(temps),
            source=random.choice(sources),
            notes=f"High potential lead looking for custom software solutions.",
            followup_date=date.today() + timedelta(days=random.randint(-10, 30))
        )

    # Sales
    categories = ["Software License", "Professional Services", "System Integration", "Cloud Hosting", "Training & Support"]
    months_2025 = [f"2025-{str(m).zfill(2)}" for m in range(1, 13)]
    months_2026 = [f"2026-{str(m).zfill(2)}" for m in range(1, 13)]
    all_months = months_2025 + months_2026

    for m_y in all_months:
        for _ in range(2):
            SaleReport.objects.create(
                month_year=m_y,
                category=random.choice(categories),
                client=random.choice(lead_names),
                amount=round(random.uniform(500, 15000), 2),
                notes="Automated dummy entry."
            )

    messages.success(request, 'Sample data populated perfectly!')
    return redirect('settings')

@login_required
def users_view(request):
    if not request.user.is_superuser:
        return redirect('dashboard')
    users = User.objects.all().order_by('-id')
    context = {
        'users_list': users,
        'active_tab': 'users'
    }
    return render(request, 'crm/users.html', context)

@login_required
def add_user_view(request):
    if not request.user.is_superuser:
        return redirect('dashboard')
    if request.method == 'POST':
        uname = request.POST.get('username')
        upass = request.POST.get('password')
        role = request.POST.get('role')

        if uname and upass:
            if role == 'Admin':
                User.objects.create_superuser(uname, '', upass)
            else:
                User.objects.create_user(uname, '', upass)
            messages.success(request, f'User {uname} created successfully!')
    return redirect('users')

@login_required
def delete_user_view(request, user_id):
    if not request.user.is_superuser:
        return redirect('dashboard')
    u = get_object_or_404(User, id=user_id)
    if u != request.user:
        u.delete()
        messages.success(request, 'User deleted successfully!')
    return redirect('users')
