from django.db import models
from django.contrib.auth.models import User

class CRMSetting(models.Model):
    key = models.CharField(max_length=100, primary_key=True)
    value = models.TextField()

    def __str__(self):
        return f"{self.key}: {self.value}"

class Lead(models.Model):
    STATUS_CHOICES = [
        ('New', 'New'),
        ('In Progress', 'In Progress'),
        ('Closed', 'Closed'),
    ]
    TEMP_CHOICES = [
        ('Hot', 'Hot'),
        ('Warm', 'Warm'),
        ('Cold', 'Cold'),
    ]
    name = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='New')
    temperature = models.CharField(max_length=50, choices=TEMP_CHOICES, default='Warm')
    source = models.CharField(max_length=100, default='Manual Entry')
    notes = models.TextField(blank=True, null=True)
    followup_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.company or 'No Company'})"

class Task(models.Model):
    PRIORITY_CHOICES = [
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, blank=True, null=True, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='Medium')
    due_date = models.DateField(blank=True, null=True)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class SaleReport(models.Model):
    month_year = models.CharField(max_length=7) # format: YYYY-MM
    category = models.CharField(max_length=100)
    client = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client} - {self.category} (${self.amount})"

class EmailTemplate(models.Model):
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Campaign(models.Model):
    name = models.CharField(max_length=255)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, blank=True, null=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=50, default='Scheduled')
    stats_sent = models.IntegerField(default=0)
    stats_failed = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class CampaignLog(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='logs')
    email = models.EmailField()
    status = models.CharField(max_length=50)
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)

class FollowupLog(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='followup_logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=100)
    result = models.CharField(max_length=255)
    notes = models.TextField(blank=True, null=True)
