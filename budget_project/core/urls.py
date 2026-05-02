"""URL configuration for the core app."""

from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),

    # Dashboard (US #10)
    path("dashboard/", views.dashboard_view, name="dashboard"),

    # Transactions (US #3)
    path("transactions/", views.transactions_view, name="transactions"),
    path("transactions/add/", views.add_transaction_view, name="add_transaction"),
    path("transactions/<int:pk>/delete/", views.delete_transaction_view, name="delete_transaction"),

    # Budgets (US #4, #5)
    path("budgets/", views.budgets_view, name="budgets"),
    path("budgets/create/", views.create_budget_view, name="create_budget"),
    path("budgets/<int:pk>/edit/", views.edit_budget_view, name="edit_budget"),
    path("budgets/<int:pk>/delete/", views.delete_budget_view, name="delete_budget"),

    # Goals (US #6)
    path("goals/", views.goals_view, name="goals"),
    path("goals/create/", views.create_goal_view, name="create_goal"),
    path("goals/<int:pk>/contribute/", views.contribute_goal_view, name="contribute_goal"),
    path("goals/<int:pk>/delete/", views.delete_goal_view, name="delete_goal"),

    # Reports (US #7)
    path("reports/", views.reports_view, name="reports"),

    # Notifications
    path("notifications/", views.notifications_view, name="notifications"),

    # Task 5 Bonus - Categories
    path("categories/", views.categories_view, name="categories"),
    path("categories/<int:pk>/delete/", views.delete_category_view, name="delete_category"),
]
