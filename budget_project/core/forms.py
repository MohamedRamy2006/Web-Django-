"""
Forms for Personal Budgeting Software.
Each form corresponds to a user story data dictionary (SDS).
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import User, Transaction, Budget, Goal, Category, TransactionType



# US #1 - Sign Up

class SignUpForm(UserCreationForm):
    """Registration form: full_name, email, password (US #1 data dictionary)."""

    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Full Name", "class": "form-control"}),
        label="Full Name",
    )
    email = forms.EmailField(
        max_length=100,
        widget=forms.EmailInput(attrs={"placeholder": "Email", "class": "form-control"}),
        label="Email",
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Password", "class": "form-control"}),
        help_text="At least 8 characters with uppercase, number, and special character.",
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm Password", "class": "form-control"}),
    )

    class Meta:
        model = User
        fields = ("full_name", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.full_name = self.cleaned_data["full_name"]
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"].split("@")[0]
        if commit:
            user.save()
        return user



# US #2 - Login

class LoginForm(forms.Form):
    """Login form using email + password."""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "Email", "class": "form-control"}),
        label="Email",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password", "class": "form-control"}),
        label="Password",
    )


# ---------------------------------------------------------------------------
# US #3 - Add Transaction
# ---------------------------------------------------------------------------
class TransactionForm(forms.ModelForm):
    """
    Add transaction form (US #3 data dictionary).
    Fields: type, amount, category, date, description, payment_method.
    """

    PAYMENT_CHOICES = [
        ("", "-- Select Payment Method --"),
        ("Cash", "Cash"),
        ("Credit Card", "Credit Card"),
        ("Debit Card", "Debit Card"),
        ("Bank Transfer", "Bank Transfer"),
        ("Mobile Payment", "Mobile Payment"),
    ]

    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Transaction
        fields = ["transaction_type", "amount", "category", "date", "description", "payment_method"]
        widgets = {
            "transaction_type": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={
                "class": "form-control", "placeholder": "0.00", "min": "0.01", "step": "0.01"
            }),
            "category": forms.Select(attrs={"class": "form-select"}),
            "date": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Optional note..."}),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["category"].queryset = Category.objects.filter(user=user)
        self.fields["date"].initial = timezone.now().strftime("%Y-%m-%dT%H:%M")

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Amount must be a positive number greater than 0.")
        return amount


# ---------------------------------------------------------------------------
# US #4 - Create / Edit Budget
# ---------------------------------------------------------------------------
class BudgetForm(forms.ModelForm):
    """
    Budget form (US #4 data dictionary).
    Fields: category, amount, start_date, end_date, alert_threshold.
    """

    class Meta:
        model = Budget
        fields = ["category", "amount", "start_date", "end_date", "alert_threshold"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={
                "class": "form-control", "placeholder": "0.00", "min": "0.01", "step": "0.01"
            }),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "alert_threshold": forms.NumberInput(attrs={
                "class": "form-control", "min": "1", "max": "100", "value": "75"
            }),
        }
        labels = {
            "alert_threshold": "Alert Threshold (%)",
        }
        help_texts = {
            "alert_threshold": "Notify me when I reach this % of my budget.",
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["category"].queryset = Category.objects.filter(user=user)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            raise forms.ValidationError("End date must be after start date.")
        return cleaned


# ---------------------------------------------------------------------------
# US #6 - Create Goal
# ---------------------------------------------------------------------------
class GoalForm(forms.ModelForm):
    """
    Goal form (US #6 data dictionary).
    Fields: name, target_amount, current_amount, deadline.
    """

    class Meta:
        model = Goal
        fields = ["name", "target_amount", "current_amount", "deadline"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Summer Vacation"}),
            "target_amount": forms.NumberInput(attrs={
                "class": "form-control", "placeholder": "0.00", "min": "0.01", "step": "0.01"
            }),
            "current_amount": forms.NumberInput(attrs={
                "class": "form-control", "placeholder": "0.00", "min": "0", "step": "0.01"
            }),
            "deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
        labels = {
            "current_amount": "Initial Saved Amount (Optional)",
        }

    def clean_deadline(self):
        from datetime import date
        deadline = self.cleaned_data.get("deadline")
        if deadline and deadline <= date.today():
            raise forms.ValidationError("Deadline must be a future date.")
        return deadline

    def clean_target_amount(self):
        amount = self.cleaned_data.get("target_amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Target amount must be greater than 0.")
        return amount


class GoalContributionForm(forms.Form):
    """Form for adding a contribution to an existing goal."""

    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": "form-control", "placeholder": "Amount to add", "step": "0.01"
        }),
        label="Contribution Amount",
    )


# ---------------------------------------------------------------------------
# US #7 - Report date range
# ---------------------------------------------------------------------------
class ReportFilterForm(forms.Form):
    """Date range selector for report generation (US #7)."""

    from datetime import date
    period_start = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="From",
    )
    period_end = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="To",
    )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("period_start")
        end = cleaned.get("period_end")
        if start and end and end < start:
            raise forms.ValidationError("End date must be after start date.")
        return cleaned


# ---------------------------------------------------------------------------
# Task 5 Bonus: Category management form
# ---------------------------------------------------------------------------
class CategoryForm(forms.ModelForm):
    """Form for creating a custom transaction category (Task 5 bonus)."""

    class Meta:
        model = Category
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Category Name"}),
        }
