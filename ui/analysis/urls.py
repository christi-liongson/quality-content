from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('summary', views.summary, name='summary'),
    path('about', views.about, name='about')
    # path('', url(r^graph.png$), views.graph_speakers)
]