from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


def send_templated_email(subject, template_name, context, to_email):
    """Send an email using the authenticated SMTP From address."""
    from_email = settings.DEFAULT_FROM_EMAIL
    email = EmailMessage(
        subject,
        render_to_string(template_name, context),
        from_email=from_email,
        to=[to_email],
    )
    return email.send()
