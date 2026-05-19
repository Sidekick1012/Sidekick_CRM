from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard_view, name='dashboard'),
    
    # Leads pipeline
    path('leads/', views.leads_view, name='leads'),
    path('leads/add/', views.add_lead_view, name='add_lead'),
    path('leads/<int:lead_id>/update/', views.update_lead_view, name='update_lead'),
    path('leads/<int:lead_id>/delete/', views.delete_lead_view, name='delete_lead'),
    
    # Tasks
    path('tasks/', views.tasks_view, name='tasks'),
    path('tasks/add/', views.add_task_view, name='add_task'),
    path('tasks/<int:task_id>/complete/', views.complete_task_view, name='complete_task'),
    path('tasks/<int:task_id>/delete/', views.delete_task_view, name='delete_task'),
    
    # Sales
    path('sales/', views.sales_view, name='sales'),
    path('sales/add/', views.add_sale_view, name='add_sale'),
    path('sales/<int:sale_id>/delete/', views.delete_sale_view, name='delete_sale'),
    
    # Campaigns
    path('campaigns/', views.campaigns_view, name='campaigns'),
    path('templates/add/', views.add_template_view, name='add_template'),
    path('templates/<int:template_id>/delete/', views.delete_template_view, name='delete_template'),
    path('campaigns/add/', views.add_campaign_view, name='add_campaign'),
    
    # Settings
    path('settings/', views.settings_view, name='settings'),
    path('settings/generate-dummy-data/', views.generate_dummy_data_view, name='generate_dummy_data'),
    
    # Users (Admin only)
    path('users/', views.users_view, name='users'),
    path('users/add/', views.add_user_view, name='add_user'),
    path('users/<int:user_id>/delete/', views.delete_user_view, name='delete_user'),
]
