from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    pat("admin/", admin.site.urls),
    path("", views.inicio, name="inicio"),
 ]