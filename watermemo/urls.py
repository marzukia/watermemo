from django.contrib import admin
from django.shortcuts import render
from django.urls import path

from core.api import api


def debug_view(request):
    return render(request, "core/debug.html")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("chat/", debug_view),
]
