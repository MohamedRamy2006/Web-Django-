"""Context processors for global template variables."""

def unread_notifications(request):
    """Inject unread notification count into every template context."""
    if request.user.is_authenticated:
        count = request.user.notifications.filter(is_read=False).count()
        return {"unread_count": count}
    return {"unread_count": 0}
