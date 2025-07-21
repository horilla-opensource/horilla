"""
horilla_middlewares.py

This module is used to register horilla's middlewares without affecting the horilla/settings.py
"""

import threading

from django.http import HttpResponseNotAllowed
from django.shortcuts import render

from horilla.settings import MIDDLEWARE

MIDDLEWARE.append("base.middleware.CompanyMiddleware")
MIDDLEWARE.append("horilla.horilla_middlewares.MethodNotAllowedMiddleware")
MIDDLEWARE.append("horilla.horilla_middlewares.ThreadLocalMiddleware")
MIDDLEWARE.append("accessibility.middlewares.AccessibilityMiddleware")
MIDDLEWARE.append("base.middleware.ForcePasswordChangeMiddleware")
MIDDLEWARE.append("base.middleware.TwoFactorAuthMiddleware")
_thread_locals = threading.local()


class ThreadLocalMiddleware:
    """
    ThreadLocalMiddleWare
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        response = self.get_response(request)
        return response


class MethodNotAllowedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if isinstance(response, HttpResponseNotAllowed):
            return render(request, "405.html")
        return response
