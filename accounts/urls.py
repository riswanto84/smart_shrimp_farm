from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
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
    path('profile/', views.edit_profile, name='edit_profile'),
    path('password/', views.change_password, name='change_password'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url=reverse_lazy('accounts:password_reset_done')
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete')
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
]
