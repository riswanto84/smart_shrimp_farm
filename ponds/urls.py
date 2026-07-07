from django.urls import path
from . import views
app_name='ponds'
urlpatterns=[
    path('',views.list_ponds,name='list'),
    path('add/',views.add_pond,name='add'),
    path('<int:pk>/',views.detail_pond,name='detail'),
    path('<int:pk>/edit/',views.edit_pond,name='edit'),
    path('<int:pk>/delete/',views.delete_pond,name='delete'),
]
