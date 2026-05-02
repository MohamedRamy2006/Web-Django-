"""
Models for Personal Budgeting Software.
Implements entity classes from the Class Diagram (SDS Task 2.2):
  User, Transaction, Budget, Goal, Notification, Report, Category, TransactionType
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Enumeration: TransactionType (US #3)
# ---------------------------------------------------------------------------
class TransactionType(models.TextChoices):
    """Defines whether a transaction is INCOME or EXPENSE."""
    INCOME = "INCOME", "Income"
    EXPENSE = "EXPENSE", "Expense"


# ---------------------------------------------------------------------------
# Entity: User (extends Django AbstractUser) (US #1)
# ---------------------------------------------------------------------------
class User(AbstractUser):
    """
    Represents an application user.

    Attributes:
        full_name (str): Display name of the user.
        email (str): Unique email address used for login.
    """
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "full_name"]

    def get_total_balance(self):
        """Calculate total balance: sum(income) - sum(expenses)."""
        from django.db.models import Sum
        income = self.transactions.filter(
            transaction_type=TransactionType.INCOME
        ).aggregate(total=Sum("amount"))["total"] or 0
        expenses = self.transactions.filter(
            transaction_type=TransactionType.EXPENSE
        ).aggregate(total=Sum("amount"))["total"] or 0
        return income - expenses

    def get_monthly_income(self):
        """Return total income for the current month."""
        from django.db.models import Sum
        now = timezone.now()
        return self.transactions.filter(
            transaction_type=TransactionType.INCOME,
            date__year=now.year,
            date__month=now.month,
        ).aggregate(total=Sum("amount"))["total"] or 0

    def get_monthly_expenses(self):
        """Return total expenses for the current month."""
        from django.db.models import Sum
        now = timezone.now()
        return self.transactions.filter(
            transaction_type=TransactionType.EXPENSE,
            date__year=now.year,
            date__month=now.month,
        ).aggregate(total=Sum("amount"))["total"] or 0

    def __str__(self):
        return f"{self.full_name} <{self.email}>"


# ---------------------------------------------------------------------------
# Entity: Category (US #3)
# ---------------------------------------------------------------------------
class Category(models.Model):
    """
    Represents the category of a financial transaction.

    Attributes:
        name (str): Category label (e.g. Food, Transport).
        user (User): Owner of the category (null = system default).
    """
    name = models.CharField(max_length=50)
    user = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="categories",
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = ("name", "user")
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Entity: Transaction (US #3)
# ---------------------------------------------------------------------------
class Transaction(models.Model):
    """
    Represents a single financial transaction (income or expense).

    Attributes:
        user (User): Owner of the transaction.
        transaction_type (str): INCOME or EXPENSE.
        amount (Decimal): Positive monetary value.
        category (Category): Spending/income category.
        date (datetime): When the transaction occurred.
        description (str): Optional free-form note.
        payment_method (str): Optional payment method.
    """
    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_type = models.CharField(
        max_length=10, choices=TransactionType.choices
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    date = models.DateTimeField(default=timezone.now)
    description = models.CharField(max_length=200, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["-date"]

    def save(self, *args, **kwargs):
        """Override save to trigger budget alert check after persistence."""
        super().save(*args, **kwargs)
        if self.transaction_type == TransactionType.EXPENSE:
            BudgetService.check_budget_alerts(self)

    def __str__(self):
        return f"{self.transaction_type} {self.amount} [{self.category}]"


# ---------------------------------------------------------------------------
# Entity: Budget (US #4, US #5)
# ---------------------------------------------------------------------------
class Budget(models.Model):
    """
    Represents a user-defined spending budget for a category and period.

    Attributes:
        user (User): Owner of the budget.
        category (Category): Spending category being budgeted.
        amount (Decimal): Limit for the budget period.
        start_date (date): First day of the budget period.
        end_date (date): Last day of the budget period.
        alert_threshold (int): Percentage at which to notify user (e.g. 75).
    """
    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, related_name="budgets"
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="budgets"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    alert_threshold = models.IntegerField(default=75)

    class Meta:
        unique_together = ("user", "category", "start_date")

    def get_spent_amount(self):
        """Sum of all expense transactions for this budget category & period."""
        from django.db.models import Sum
        return self.user.transactions.filter(
            transaction_type=TransactionType.EXPENSE,
            category=self.category,
            date__date__gte=self.start_date,
            date__date__lte=self.end_date,
        ).aggregate(total=Sum("amount"))["total"] or 0

    def get_percentage_used(self):
        """Return percentage of budget consumed."""
        if self.amount == 0:
            return 0
        return round(float(self.get_spent_amount()) / float(self.amount) * 100, 1)

    def get_status(self):
        """Return 'On Track', 'Near Limit', or 'Exceeded'."""
        pct = self.get_percentage_used()
        if pct >= 100:
            return "Exceeded"
        if pct >= self.alert_threshold:
            return "Near Limit"
        return "On Track"

    def __str__(self):
        return f"{self.category} budget ({self.start_date} to {self.end_date})"


# ---------------------------------------------------------------------------
# Entity: Goal (US #6)
# ---------------------------------------------------------------------------
class Goal(models.Model):
    """
    Represents a financial savings goal.

    Attributes:
        user (User): Owner of the goal.
        name (str): Descriptive goal name.
        target_amount (Decimal): Amount the user wants to reach.
        current_amount (Decimal): How much has been saved so far.
        deadline (date): Target completion date.
    """
    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, related_name="goals"
    )
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    current_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def get_status(self):
        """Return 'Completed' or 'In Progress'."""
        return "Completed" if self.current_amount >= self.target_amount else "In Progress"

    def get_progress_percentage(self):
        """Return progress as a percentage."""
        if self.target_amount == 0:
            return 0
        return round(float(self.current_amount) / float(self.target_amount) * 100, 1)

    def get_monthly_savings_needed(self):
        """Calculate monthly contribution needed to reach goal by deadline."""
        from datetime import date
        today = date.today()
        months_remaining = (
            (self.deadline.year - today.year) * 12
            + (self.deadline.month - today.month)
        )
        remaining = float(self.target_amount) - float(self.current_amount)
        if months_remaining <= 0 or remaining <= 0:
            return max(0, remaining)
        return round(remaining / months_remaining, 2)

    def __str__(self):
        return f"{self.name} ({self.get_status()})"


# ---------------------------------------------------------------------------
# Entity: Notification (US #5)
# ---------------------------------------------------------------------------
class Notification(models.Model):
    """
    Represents a system notification or alert sent to the user.

    Attributes:
        user (User): Recipient.
        message (str): Notification text.
        is_read (bool): Whether the user has dismissed it.
        created_at (datetime): When it was generated.
    """
    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.CharField(max_length=500)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{'Read' if self.is_read else 'Unread'}] {self.message[:60]}"


# ---------------------------------------------------------------------------
# Entity: Report (US #7)
# ---------------------------------------------------------------------------
class Report(models.Model):
    """
    Represents a generated financial report snapshot.

    Attributes:
        user (User): Owner.
        period_start (date): Start of the report period.
        period_end (date): End of the report period.
        total_income (Decimal): Sum of income in the period.
        total_expenses (Decimal): Sum of expenses in the period.
        generated_at (datetime): When the report was created.
    """
    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, related_name="reports"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    total_income = models.DecimalField(max_digits=10, decimal_places=2)
    total_expenses = models.DecimalField(max_digits=10, decimal_places=2)
    generated_at = models.DateTimeField(auto_now_add=True)

    def get_net(self):
        """Return net amount (income - expenses)."""
        return float(self.total_income) - float(self.total_expenses)

    def __str__(self):
        return f"Report {self.period_start} to {self.period_end}"


# ===========================================================================
# SERVICE LAYER  (Control Classes from SDS)
# ===========================================================================

class AuthService:
    """
    Control class: handles user registration and authentication (US #1, #2).
    Sequence diagrams SD1/SD2 map here.
    """

    @staticmethod
    def register(full_name: str, email: str, password: str) -> "User":
        """
        Create a new user account.

        Args:
            full_name: User's display name.
            email: Unique email address.
            password: Raw password (will be hashed by Django).

        Returns:
            Newly created User instance.

        Raises:
            ValueError: If email already exists.
        """
        if User.objects.filter(email=email).exists():
            raise ValueError("A user with this email already exists.")
        username = email.split("@")[0]
        base = username
        i = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{i}"
            i += 1
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
        )
        CategoryService.seed_default_categories(user)
        return user


class TransactionService:
    """
    Control class: adds and processes financial transactions (US #3).
    Sequence diagram SD3 maps here.
    """

    @staticmethod
    def add_transaction(
        user: "User",
        transaction_type: str,
        amount,
        category: "Category",
        date=None,
        description: str = "",
        payment_method: str = "",
    ) -> "Transaction":
        """
        Validate and persist a new transaction.

        Args:
            user: Owner of the transaction.
            transaction_type: 'INCOME' or 'EXPENSE'.
            amount: Positive monetary value.
            category: Category instance.
            date: Optional datetime; defaults to now.
            description: Optional note.
            payment_method: Optional payment method string.

        Returns:
            Saved Transaction instance.

        Raises:
            ValueError: If amount is not positive.
        """
        if float(amount) <= 0:
            raise ValueError("Amount must be a positive number greater than 0.")
        txn = Transaction(
            user=user,
            transaction_type=transaction_type,
            amount=amount,
            category=category,
            description=description,
            payment_method=payment_method,
        )
        if date:
            txn.date = date
        txn.save()
        return txn


class BudgetService:
    """
    Control class: creates/edits budgets and checks over-limit alerts (US #4, #5).
    Sequence diagrams SD4/SD5 map here.
    """

    @staticmethod
    def create_budget(
        user: "User",
        category: "Category",
        amount,
        start_date,
        end_date,
        alert_threshold: int = 75,
    ) -> "Budget":
        """
        Create a new budget for a user/category/period.

        Raises:
            ValueError: If a budget already exists for the same category/period.
        """
        if Budget.objects.filter(
            user=user, category=category, start_date=start_date
        ).exists():
            raise ValueError(
                "A budget for this category already exists for this period."
            )
        return Budget.objects.create(
            user=user,
            category=category,
            amount=amount,
            start_date=start_date,
            end_date=end_date,
            alert_threshold=alert_threshold,
        )

    @staticmethod
    def update_budget(budget: "Budget", **kwargs) -> "Budget":
        """Update fields on an existing budget."""
        for field, value in kwargs.items():
            setattr(budget, field, value)
        budget.save()
        return budget

    @staticmethod
    def check_budget_alerts(transaction: "Transaction"):
        """
        Called after every EXPENSE transaction is saved (US #5).
        Generates Notification if budget is Near Limit or Exceeded.
        """
        if not transaction.category:
            return
        budgets = Budget.objects.filter(
            user=transaction.user,
            category=transaction.category,
            start_date__lte=transaction.date.date(),
            end_date__gte=transaction.date.date(),
        )
        for budget in budgets:
            pct = budget.get_percentage_used()
            spent = budget.get_spent_amount()
            if pct >= 100:
                overage = float(spent) - float(budget.amount)
                msg = (
                    f"Budget Exceeded – {budget.category}! "
                    f"You've exceeded your ${budget.amount} budget by ${overage:.2f}."
                )
            elif pct >= budget.alert_threshold:
                msg = (
                    f"Budget Alert – {budget.category}: "
                    f"You've used {pct}% of your {budget.category} budget."
                )
            else:
                continue
            if not Notification.objects.filter(
                user=transaction.user, message=msg, is_read=False
            ).exists():
                NotificationService.create_notification(
                    user=transaction.user, message=msg
                )


class GoalService:
    """
    Control class: creates and manages financial goals (US #6).
    Sequence diagram SD6 maps here.
    """

    @staticmethod
    def create_goal(
        user: "User",
        name: str,
        target_amount,
        deadline,
        current_amount=0,
    ) -> "Goal":
        """
        Validate and persist a new financial goal.

        Raises:
            ValueError: If target_amount <= 0 or deadline is in the past.
        """
        from datetime import date
        if float(target_amount) <= 0:
            raise ValueError("Target amount must be a positive number.")
        if deadline <= date.today():
            raise ValueError("Deadline must be a future date.")
        return Goal.objects.create(
            user=user,
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            deadline=deadline,
        )

    @staticmethod
    def add_contribution(goal: "Goal", amount) -> "Goal":
        """
        Add a monetary contribution toward a goal (US #6 step 9-10).

        Args:
            goal: The Goal to update.
            amount: Positive contribution amount.

        Returns:
            Updated Goal instance.
        """
        if float(amount) <= 0:
            raise ValueError("Contribution must be positive.")
        goal.current_amount = min(
            float(goal.current_amount) + float(amount), float(goal.target_amount)
        )
        goal.save()
        if goal.get_status() == "Completed":
            NotificationService.create_notification(
                user=goal.user,
                message=f"Congratulations! You have completed your goal: {goal.name}!",
            )
        return goal


class ReportService:
    """
    Control class: generates financial reports and analytics (US #7).
    Sequence diagram SD7 maps here.
    """

    @staticmethod
    def generate_report(user: "User", period_start, period_end) -> dict:
        """
        Fetch and aggregate transaction data for the given period.

        Args:
            user: The requesting user.
            period_start: Start date of the report period.
            period_end: End date of the report period.

        Returns:
            dict with total_income, total_expenses, category_totals,
            weekly_data, has_data flag, and a persisted Report snapshot.
        """
        from django.db.models import Sum
        from collections import defaultdict

        transactions = user.transactions.filter(
            date__date__gte=period_start,
            date__date__lte=period_end,
        )

        total_income = transactions.filter(
            transaction_type=TransactionType.INCOME
        ).aggregate(total=Sum("amount"))["total"] or 0

        total_expenses = transactions.filter(
            transaction_type=TransactionType.EXPENSE
        ).aggregate(total=Sum("amount"))["total"] or 0

        category_totals = {}
        for txn in transactions.filter(transaction_type=TransactionType.EXPENSE):
            cat_name = txn.category.name if txn.category else "Uncategorized"
            category_totals[cat_name] = category_totals.get(cat_name, 0) + float(txn.amount)

        weekly_data = defaultdict(lambda: {"income": 0, "expense": 0})
        for txn in transactions:
            week = txn.date.strftime("%Y-W%U")
            key = "income" if txn.transaction_type == TransactionType.INCOME else "expense"
            weekly_data[week][key] += float(txn.amount)

        report = Report.objects.create(
            user=user,
            period_start=period_start,
            period_end=period_end,
            total_income=total_income,
            total_expenses=total_expenses,
        )

        return {
            "report": report,
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "net": float(total_income) - float(total_expenses),
            "category_totals": category_totals,
            "weekly_data": dict(weekly_data),
            "has_data": transactions.exists(),
        }


class NotificationService:
    """
    Control class: creates and retrieves notifications (US #5).
    """

    @staticmethod
    def create_notification(user: "User", message: str) -> "Notification":
        """Persist a new notification for the user."""
        return Notification.objects.create(user=user, message=message)

    @staticmethod
    def get_unread(user: "User"):
        """Return unread notifications for a user."""
        return Notification.objects.filter(user=user, is_read=False)

    @staticmethod
    def mark_all_read(user: "User"):
        """Mark all notifications as read."""
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)


class CategoryService:
    """Helper service for managing transaction categories."""

    DEFAULT_CATEGORIES = [
        "Food & Dining", "Transport", "Housing", "Healthcare",
        "Entertainment", "Shopping", "Education", "Salary",
        "Freelance", "Investment", "Savings", "Other",
    ]

    @staticmethod
    def seed_default_categories(user: "User"):
        """Create default categories for a newly registered user."""
        for name in CategoryService.DEFAULT_CATEGORIES:
            Category.objects.get_or_create(name=name, user=user)
