"""
WSGI config for spot2-challenge project. # <-- Adjust project name if needed

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Make sure this matches your settings file location
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spot2-challenge.settings")

application = get_wsgi_application()  # <-- This line defines the 'application' object
