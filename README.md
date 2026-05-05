========================================================
  Personal Budgeting Software
  CS251 - Introduction to Software Engineering
  Cairo University, FCAI
========================================================

TEAM
----
- Amr Abdelrahman      (20240399)
- Marwan Medhat Atta   (20240569)
- Mohammed Ramy        (20240496)
- Walaa Hassan Mohamed (20220829)

TECHNOLOGY
----------
  Language   : Python 3.x
  Framework  : Django 6.x (Web - as permitted by Task 3)
  Database   : SQLite3 (auto-created, persists across runs)
  Style Guide: PEP 8

USER STORIES IMPLEMENTED (Tasks 3 & 5)
---------------------------------------
  US #1  - User Sign-Up          (AuthService, SignUpForm, signup_view)
  US #2  - User Login            (AuthService, LoginForm,  login_view)
  US #3  - Add Transaction       (TransactionService, TransactionForm, add_transaction_view)
  US #4  - Create / Edit Budget  (BudgetService, BudgetForm, create_budget_view / edit_budget_view)
  US #5  - Budget Over-Limit Alert (BudgetService.check_budget_alerts, NotificationService)
  US #6  - Set & Track Goals     (GoalService, GoalForm, create_goal_view / contribute_goal_view)
  US #7  - View Reports          (ReportService, ReportFilterForm, reports_view)
  US #10 - Dashboard Overview    (dashboard_view, all services)

TASK 5 BONUS FEATURES
---------------------
  - Custom category management (create / delete user categories)
  - Transaction filtering by type and category
  - Goal contribution flow with completion notification
  - Notification centre with read/unread tracking
  - Chart.js pie + bar charts on the Reports page
  - Full Django Admin panel (/admin/)

SEQUENCE DIAGRAM → CODE MAPPING (Class-Sequence Usage Table)
--------------------------------------------------------------
  SD1 (Sign-Up)  : signup_view → AuthService.register()
                   → User.objects.create_user() → DB
                   → CategoryService.seed_default_categories()

  SD2 (Login)    : login_view → django.contrib.auth.authenticate()
                   → UserRepository (Django ORM) → DB

  SD3 (Add Txn)  : add_transaction_view → TransactionService.add_transaction()
                   → Transaction.save() → DB
                   → BudgetService.check_budget_alerts()
                   → NotificationService.create_notification() → DB

  SD4 (Budget)   : create_budget_view → BudgetService.create_budget()
                   → Budget.objects.create() → DB

  SD5 (Alert)    : (triggered inside Transaction.save())
                   → BudgetService.check_budget_alerts()
                   → Budget.get_percentage_used()
                   → NotificationService.create_notification() → DB

  SD6 (Goal)     : create_goal_view → GoalService.create_goal()
                   → Goal.objects.create() → DB
                   contribute_goal_view → GoalService.add_contribution()
                   → Goal.save() → (if complete) NotificationService

  SD7 (Report)   : reports_view → ReportService.generate_report()
                   → Transaction.objects.filter() → DB
                   → Report.objects.create() → DB

HOW TO RUN
----------
  1. Install dependencies:
       pip install django

  2. Run migrations (creates db.sqlite3):
       python manage.py migrate

  3. (Optional) Create a superuser for admin:
       python manage.py createsuperuser

  4. Start the server:
       python manage.py runserver

  5. Open in browser:
       http://127.0.0.1:8000/

  6. Admin panel:
       http://127.0.0.1:8000/admin/

FILES INCLUDED
--------------
  budget_project/
  ├── manage.py
  ├── README.txt
  ├── db.sqlite3              (auto-created after migrate)
  ├── budget_project/
  │   ├── settings.py         (Django settings, SQLite3 DB, custom AUTH_USER_MODEL)
  │   ├── urls.py             (root URL conf)
  │   └── wsgi.py
  ├── core/                   (main application)
  │   ├── models.py           (Entity + Service classes)
  │   ├── views.py            (Screen classes as Django views)
  │   ├── forms.py            (Form classes per US data dictionary)
  │   ├── urls.py             (app URL conf)
  │   ├── admin.py            (Admin registration)
  │   └── context_processors.py
  ├── templates/core/         (HTML templates per screen)
  │   ├── base.html, login.html, signup.html
  │   ├── dashboard.html, transactions.html, add_transaction.html
  │   ├── budgets.html, create_budget.html, edit_budget.html
  │   ├── goals.html, create_goal.html, contribute_goal.html
  │   ├── reports.html, notifications.html, categories.html
  └── static/css/style.css    (complete stylesheet)

SOLID PRINCIPLES APPLIED
-------------------------
  S - Single Responsibility : Each service class handles exactly one domain
      (TransactionService only manages transactions, GoalService only goals).

  O - Open/Closed : New transaction types or report formats can be added
      without modifying existing service methods.

  D - Dependency Inversion : Views depend on service abstractions
      (TransactionService.add_transaction) not directly on ORM calls.

DESIGN PATTERNS USED
---------------------
  1. Repository Pattern   : Django ORM acts as the repository layer
     (UserRepository = User.objects, BudgetRepository = Budget.objects).

  2. Service Layer Pattern: AuthService, TransactionService, BudgetService,
     GoalService, ReportService, NotificationService.

  3. Template Method      : Transaction.save() calls the hook
     BudgetService.check_budget_alerts() — subclasses can override.

NOTE ON DATABASE PERSISTENCE
-----------------------------
  All data is stored in db.sqlite3 (relative to manage.py).
  The database is created automatically on first `python manage.py migrate`.
  Data persists across server restarts as required by Task 3.
