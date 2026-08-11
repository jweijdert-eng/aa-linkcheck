"""App URLs"""

from django.urls import path

from . import views

app_name: str = "linkcheck"

urlpatterns = [
    path("", views.index, name="index"),
    path("account/<int:user_id>/", views.detail, name="detail"),
]
