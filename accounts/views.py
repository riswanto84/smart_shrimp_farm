import random
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import login as auth_login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required, normalized_roles
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .models import Role, PermissionItem, AuditLog
from core.pagination import paginate_queryset


def is_staff_or_superuser(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


class AppLoginView(LoginView):
    template_name='accounts/login.html'
    redirect_authenticated_user = True
    authentication_form = AuthenticationForm
    def _set_captcha(self):
        a=random.randint(3,9); b=random.randint(2,8)
        self.request.session['captcha_answer']=a+b
        return f'{a} + {b} = ?'
    def get_context_data(self, **kwargs):
        ctx=super().get_context_data(**kwargs)
        ctx['captcha_question']=self._set_captcha()
        return ctx

    def get_success_url(self):
        roles = normalized_roles(self.request.user)
        if roles == ['investor']:
            return '/investor/dashboard/'
        if roles == ['kasir']:
            return '/sales/cashier/'
        if roles == ['akuntan']:
            return '/finance/profit-loss/'
        if roles == ['teknisi']:
            return '/operations/parameters/'
        return '/dashboard/'
    def post(self, request, *args, **kwargs):
        expected=request.session.get('captcha_answer')
        answer=request.POST.get('captcha','').strip()
        if expected is None or answer != str(expected):
            form=self.authentication_form(request, data=request.POST)
            messages.error(request, 'Kode keamanan matematika tidak sesuai. Silakan coba lagi.')
            request.session['captcha_answer']=None
            return render(request, self.template_name, {'form':form, 'captcha_question':self._set_captcha()})
        form=self.authentication_form(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            AuditLog.objects.create(user=form.get_user(), action='Login ke SMART SHRIMP FARM')
            return redirect(self.get_success_url())
        messages.error(request, 'Username atau password salah.')
        return render(request, self.template_name, {'form':form, 'captcha_question':self._set_captcha()})
class AppLogoutView(LogoutView): pass

@permission_required('accounts.users')
def users(request):
    users=User.objects.select_related('userprofile').prefetch_related('userprofile__roles').all().order_by('first_name','username')
    roles=Role.objects.all()
    active_count=users.filter(is_active=True).count()
    page_obj = paginate_queryset(request, users, per_page=10)
    return render(request,'accounts/users.html',{'users':page_obj,'page_obj':page_obj,'roles':roles,'active_count':active_count})

@permission_required('accounts.users')
def add_user(request):
    roles=Role.objects.all()
    if request.method=='POST':
        username=request.POST.get('username','').strip()
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username sudah digunakan. Silakan gunakan username lain.')
            return render(request,'accounts/add_user.html',{'roles':roles})
        u=User.objects.create_user(
            username=username,
            email=request.POST.get('email','').strip(),
            password=request.POST.get('password','12345678'),
            first_name=request.POST.get('first_name','').strip(),
            is_active=bool(request.POST.get('is_active','on')),
        )
        u.userprofile.phone=request.POST.get('phone','').strip()
        u.userprofile.save()
        u.userprofile.roles.set(Role.objects.filter(id__in=request.POST.getlist('roles')))
        AuditLog.objects.create(user=request.user, action=f'Menambahkan pengguna {u.username}')
        messages.success(request, f'Pengguna {u.username} berhasil ditambahkan.')
        return redirect('accounts:users')
    return render(request,'accounts/add_user.html',{'roles':roles})

@permission_required('accounts.users')
def edit_user(request, user_id):
    edited_user = get_object_or_404(User.objects.select_related('userprofile').prefetch_related('userprofile__roles'), id=user_id)
    roles = Role.objects.all()
    if request.method == 'POST':
        username = request.POST.get('username','').strip()
        if User.objects.exclude(id=edited_user.id).filter(username=username).exists():
            messages.error(request, 'Username sudah digunakan oleh pengguna lain.')
            return render(request, 'accounts/add_user.html', {'roles': roles, 'edited_user': edited_user, 'is_edit': True})
        edited_user.username = username
        edited_user.first_name = request.POST.get('first_name','').strip()
        edited_user.email = request.POST.get('email','').strip()
        edited_user.is_active = bool(request.POST.get('is_active'))
        new_password = request.POST.get('password','').strip()
        if new_password:
            edited_user.set_password(new_password)
        edited_user.save()
        edited_user.userprofile.phone = request.POST.get('phone','').strip()
        edited_user.userprofile.save()
        edited_user.userprofile.roles.set(Role.objects.filter(id__in=request.POST.getlist('roles')))
        AuditLog.objects.create(user=request.user, action=f'Mengubah pengguna {edited_user.username}')
        messages.success(request, f'Data pengguna {edited_user.username} berhasil diperbarui.')
        return redirect('accounts:users')
    return render(request, 'accounts/add_user.html', {'roles': roles, 'edited_user': edited_user, 'is_edit': True})

@permission_required('accounts.users')
def delete_user(request, user_id):
    deleted_user = get_object_or_404(User, id=user_id)
    if deleted_user.id == request.user.id:
        messages.error(request, 'Akun yang sedang digunakan tidak boleh dihapus.')
        return redirect('accounts:users')
    if request.method == 'POST':
        username = deleted_user.username
        deleted_user.delete()
        AuditLog.objects.create(user=request.user, action=f'Menghapus pengguna {username}')
        messages.success(request, f'Pengguna {username} berhasil dihapus.')
        return redirect('accounts:users')
    return render(request, 'accounts/confirm_delete_user.html', {'deleted_user': deleted_user})

@permission_required('accounts.roles')
def roles(request):
    roles = Role.objects.all().order_by('name')
    perms = PermissionItem.objects.all().order_by('group','code')
    page_obj = paginate_queryset(request, perms, per_page=10)
    return render(request,'accounts/roles.html',{'roles':roles,'perms':page_obj,'page_obj':page_obj})


@login_required
def edit_profile(request):
    profile = request.user.userprofile
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        if email and User.objects.exclude(id=request.user.id).filter(email=email).exists():
            messages.error(request, 'Email sudah digunakan oleh pengguna lain.')
            return render(request, 'accounts/profile_form.html', {'profile': profile})
        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.email = email
        request.user.save()
        profile.phone = phone
        profile.save()
        AuditLog.objects.create(user=request.user, action='Mengubah profil sendiri')
        messages.success(request, 'Profil berhasil diperbarui.')
        return redirect('accounts:edit_profile')
    return render(request, 'accounts/profile_form.html', {'profile': profile})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            AuditLog.objects.create(user=request.user, action='Mengubah password sendiri')
            messages.success(request, 'Password berhasil diubah.')
            return redirect('accounts:edit_profile')
        messages.error(request, 'Password belum bisa diubah. Periksa kembali isian password.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})
