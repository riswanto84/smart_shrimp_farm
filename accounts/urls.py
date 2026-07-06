from django.urls import path
from . import views
app_name='accounts'
urlpatterns=[
    path('login/',views.AppLoginView.as_view(),name='login'),
    path('logout/',views.AppLogoutView.as_view(),name='logout'),
    path('users/',views.users,name='users'),
    path('users/add/',views.add_user,name='add_user'),
    path('users/<int:user_id>/edit/',views.edit_user,name='edit_user'),
    path('users/<int:user_id>/delete/',views.delete_user,name='delete_user'),
    path('roles/',views.roles,name='roles'),
]
