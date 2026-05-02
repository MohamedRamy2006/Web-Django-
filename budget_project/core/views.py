"""
Views for Personal Budgeting Software.
Each view maps to a screen class from the SDS Class Diagram:
  LoginScreen, DashboardScreen, TransactionScreen, BudgetScreen, GoalsScreen, ReportsScreen.
"""

from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Transaction, Budget, Goal, Notification, Category,
    TransactionType, AuthService, TransactionService,
    BudgetService, GoalService, ReportService, NotificationService,
    CategoryService,
)
from .forms import (
    SignUpForm, LoginForm, TransactionForm, BudgetForm,
    GoalForm, GoalContributionForm, ReportFilterForm, CategoryForm,
)


# ===========================================================================
# AUTH VIEWS  (US #1, #2)
# Sequence diagrams SD1, SD2
# ===========================================================================

def signup_view(request):
    """
    SignUpScreen: Display registration form and create new account (US #1).
    SD1: User -> LoginScreen -> AuthService -> UserRepository -> Database
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                user = AuthService.register(
                    full_name=form.cleaned_data["full_name"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                )
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                messages.success(request, f"Welcome, {user.full_name}! Your account has been created.")
                return redirect("dashboard")
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = SignUpForm()

    return render(request, "core/signup.html", {"form": form})


def login_view(request):
    """
    LoginScreen: Display login form and authenticate user (US #2).
    SD2: User -> LoginScreen -> AuthService -> UserRepository -> Database
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
            if user:
                login(request, user)
                return redirect("dashboard")
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()

    return render(request, "core/login.html", {"form": form})


def logout_view(request):
    """Log out the current user."""
    logout(request)
    return redirect("login")


# ===========================================================================
# DASHBOARD  (US #10)
# ===========================================================================

@login_required
def dashboard_view(request):
    """
    DashboardScreen: Display financial overview (US #10).
    Shows: total balance, monthly income/expenses, recent transactions,
    budget previews, and budget warning alerts.
    """
    user = request.user
    recent_transactions = user.transactions.select_related("category").all()[:5]
    budgets = user.budgets.select_related("category").all()

    # Augment budgets with computed values for the template
    budget_data = []
    for b in budgets:
        budget_data.append({
            "budget": b,
            "spent": b.get_spent_amount(),
            "percentage": b.get_percentage_used(),
            "status": b.get_status(),
        })

    unread_notifications = NotificationService.get_unread(user)

    context = {
        "total_balance": user.get_total_balance(),
        "monthly_income": user.get_monthly_income(),
        "monthly_expenses": user.get_monthly_expenses(),
        "recent_transactions": recent_transactions,
        "budget_data": budget_data,
        "goals": user.goals.all()[:4],
        "unread_notifications": unread_notifications,
        "transaction_count": user.transactions.count(),
        "budget_count": user.budgets.count(),
        "goal_count": user.goals.count(),
    }
    return render(request, "core/dashboard.html", context)


# ===========================================================================
# TRANSACTIONS  (US #3)
# ===========================================================================

@login_required
def transactions_view(request):
    """
    TransactionScreen: List all transactions with filtering (US #3).
    """
    transactions = request.user.transactions.select_related("category").all()

    # Optional filter by type
    txn_type = request.GET.get("type")
    if txn_type in [TransactionType.INCOME, TransactionType.EXPENSE]:
        transactions = transactions.filter(transaction_type=txn_type)

    # Optional filter by category
    cat_id = request.GET.get("category")
    if cat_id:
        transactions = transactions.filter(category_id=cat_id)

    categories = Category.objects.filter(user=request.user)

    return render(request, "core/transactions.html", {
        "transactions": transactions,
        "categories": categories,
        "selected_type": txn_type,
        "selected_category": cat_id,
    })


@login_required
def add_transaction_view(request):
    """
    TransactionScreen: Add new transaction form (US #3).
    SD3: User -> TransactionScreen -> TransactionService -> TransactionRepository -> Database
    """
    if request.method == "POST":
        form = TransactionForm(user=request.user, data=request.POST)
        if form.is_valid():
            try:
                txn = TransactionService.add_transaction(
                    user=request.user,
                    transaction_type=form.cleaned_data["transaction_type"],
                    amount=form.cleaned_data["amount"],
                    category=form.cleaned_data["category"],
                    date=form.cleaned_data.get("date"),
                    description=form.cleaned_data.get("description", ""),
                    payment_method=form.cleaned_data.get("payment_method", ""),
                )
                messages.success(request, "Transaction saved successfully!")
                return redirect("transactions")
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = TransactionForm(user=request.user)

    return render(request, "core/add_transaction.html", {"form": form})


@login_required
def delete_transaction_view(request, pk):
    """Delete a transaction owned by the current user."""
    txn = get_object_or_404(Transaction, pk=pk, user=request.user)
    txn.delete()
    messages.success(request, "Transaction deleted.")
    return redirect("transactions")


# ===========================================================================
# BUDGETS  (US #4, #5)
# ===========================================================================

@login_required
def budgets_view(request):
    """
    BudgetScreen: List all budgets with spending progress (US #4, #5).
    """
    budgets = request.user.budgets.select_related("category").all()
    budget_data = []
    for b in budgets:
        budget_data.append({
            "budget": b,
            "spent": b.get_spent_amount(),
            "remaining": float(b.amount) - float(b.get_spent_amount()),
            "percentage": b.get_percentage_used(),
            "status": b.get_status(),
        })

    return render(request, "core/budgets.html", {"budget_data": budget_data})


@login_required
def create_budget_view(request):
    """
    BudgetScreen: Create budget form (US #4).
    SD4: User -> BudgetScreen -> BudgetService -> BudgetRepository -> Database
    """
    if request.method == "POST":
        form = BudgetForm(user=request.user, data=request.POST)
        if form.is_valid():
            try:
                BudgetService.create_budget(
                    user=request.user,
                    category=form.cleaned_data["category"],
                    amount=form.cleaned_data["amount"],
                    start_date=form.cleaned_data["start_date"],
                    end_date=form.cleaned_data["end_date"],
                    alert_threshold=form.cleaned_data.get("alert_threshold", 75),
                )
                messages.success(request, "Budget created successfully!")
                return redirect("budgets")
            except ValueError as e:
                messages.error(request, str(e))
    else:
        # Default to current month
        today = date.today()
        first = today.replace(day=1)
        if today.month == 12:
            last = today.replace(day=31)
        else:
            last = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
        form = BudgetForm(
            user=request.user,
            initial={"start_date": first, "end_date": last},
        )

    return render(request, "core/create_budget.html", {"form": form})


@login_required
def edit_budget_view(request, pk):
    """Edit an existing budget (US #4 normal scenario – edit path)."""
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    if request.method == "POST":
        form = BudgetForm(user=request.user, data=request.POST, instance=budget)
        if form.is_valid():
            BudgetService.update_budget(
                budget,
                amount=form.cleaned_data["amount"],
                alert_threshold=form.cleaned_data.get("alert_threshold", budget.alert_threshold),
                end_date=form.cleaned_data["end_date"],
            )
            messages.success(request, "Budget updated.")
            return redirect("budgets")
    else:
        form = BudgetForm(user=request.user, instance=budget)

    return render(request, "core/edit_budget.html", {"form": form, "budget": budget})


@login_required
def delete_budget_view(request, pk):
    """Delete a budget."""
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    budget.delete()
    messages.success(request, "Budget deleted.")
    return redirect("budgets")


# ===========================================================================
# GOALS  (US #6)
# ===========================================================================

@login_required
def goals_view(request):
    """
    GoalsScreen: List all financial goals with progress bars (US #6).
    """
    goals = request.user.goals.all()
    goal_data = []
    for g in goals:
        goal_data.append({
            "goal": g,
            "progress": g.get_progress_percentage(),
            "status": g.get_status(),
            "monthly_needed": g.get_monthly_savings_needed(),
        })

    return render(request, "core/goals.html", {"goal_data": goal_data})


@login_required
def create_goal_view(request):
    """
    GoalsScreen: Create goal form (US #6).
    SD6: User -> GoalsScreen -> GoalService -> GoalRepository -> Database
    """
    if request.method == "POST":
        form = GoalForm(request.POST)
        if form.is_valid():
            try:
                GoalService.create_goal(
                    user=request.user,
                    name=form.cleaned_data["name"],
                    target_amount=form.cleaned_data["target_amount"],
                    deadline=form.cleaned_data["deadline"],
                    current_amount=form.cleaned_data.get("current_amount", 0),
                )
                messages.success(request, "Goal created successfully!")
                return redirect("goals")
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = GoalForm()

    return render(request, "core/create_goal.html", {"form": form})


@login_required
def contribute_goal_view(request, pk):
    """
    GoalsScreen: Add contribution to an existing goal (US #6 step 9-10).
    """
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == "POST":
        form = GoalContributionForm(request.POST)
        if form.is_valid():
            try:
                GoalService.add_contribution(goal, form.cleaned_data["amount"])
                messages.success(request, f"Contribution added to '{goal.name}'!")
                return redirect("goals")
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = GoalContributionForm()

    return render(request, "core/contribute_goal.html", {"form": form, "goal": goal})


@login_required
def delete_goal_view(request, pk):
    """Delete a goal."""
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    goal.delete()
    messages.success(request, "Goal deleted.")
    return redirect("goals")


# ===========================================================================
# REPORTS  (US #7)
# ===========================================================================

@login_required
def reports_view(request):
    """
    ReportsScreen: Display financial reports with charts (US #7).
    SD7: User -> ReportsScreen -> ReportService -> TransactionRepository -> Database
    """
    today = date.today()
    default_start = today.replace(day=1)
    default_end = today

    form = ReportFilterForm(
        request.GET or None,
        initial={"period_start": default_start, "period_end": default_end},
    )

    report_data = None
    if form.is_valid():
        period_start = form.cleaned_data["period_start"]
        period_end = form.cleaned_data["period_end"]
    else:
        period_start = default_start
        period_end = default_end

    report_data = ReportService.generate_report(request.user, period_start, period_end)

    return render(request, "core/reports.html", {
        "form": form,
        "report_data": report_data,
        "period_start": period_start,
        "period_end": period_end,
    })


# ===========================================================================
# NOTIFICATIONS
# ===========================================================================

@login_required
def notifications_view(request):
    """List all notifications for the current user."""
    notifications = request.user.notifications.all()
    NotificationService.mark_all_read(request.user)
    return render(request, "core/notifications.html", {"notifications": notifications})


# ===========================================================================
# TASK 5 BONUS - Custom Categories
# ===========================================================================

@login_required
def categories_view(request):
    """Manage custom transaction categories (Task 5 bonus)."""
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            try:
                Category.objects.create(
                    name=form.cleaned_data["name"],
                    user=request.user,
                )
                messages.success(request, "Category created.")
                return redirect("categories")
            except Exception:
                messages.error(request, "A category with this name already exists.")
    else:
        form = CategoryForm()

    categories = Category.objects.filter(user=request.user)
    return render(request, "core/categories.html", {"form": form, "categories": categories})


@login_required
def delete_category_view(request, pk):
    """Delete a custom category."""
    cat = get_object_or_404(Category, pk=pk, user=request.user)
    cat.delete()
    messages.success(request, "Category deleted.")
    return redirect("categories")
