from django.urls import path

from . import views

app_name = "portfolio"

urlpatterns = [
    path("", views.home, name="home"),
    path("work/", views.project_list, name="project_list"),
    path("work/<slug:slug>/", views.project_detail, name="project_detail"),
    path("about/", views.about, name="about"),
    path("toolkit/", views.toolkit, name="toolkit"),
    path("journey/", views.journey, name="journey"),
    path("playground/", views.playground, name="playground"),
    path("contact/", views.contact, name="contact"),
    path("contact/thanks/", views.contact_thanks, name="contact_thanks"),
]
