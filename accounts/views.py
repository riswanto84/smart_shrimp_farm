import random
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import login as auth_login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required, normalized_roles, owner_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .models import Role, PermissionItem, AuditLog
from .activity import log_activity
from core.pagination import paginate_queryset
from django.utils.dateparse import parse_date
from django.db.models import Q, Count
from django.utils import timezone


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
            log_activity(request, user=form.get_user(), action='Login ke SMART SHRIMP FARM', action_type='login', module='Autentikasi', description='Login berhasil')
            return redirect(self.get_success_url())
        messages.error(request, 'Username atau password salah.')
        return render(request, self.template_name, {'form':form, 'captcha_question':self._set_captcha()})
class AppLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            log_activity(request, action="Logout dari SMART SHRIMP FARM", action_type="logout", module="Autentikasi", description="Logout berhasil")
        return super().dispatch(request, *args, **kwargs)

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
        log_activity(request, action=f'Menambahkan pengguna {u.username}', action_type='create', module='Pengguna & Hak Akses', description='Membuat akun pengguna baru', object_repr=u.username)
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
        log_activity(request, action=f'Mengubah pengguna {edited_user.username}', action_type='update', module='Pengguna & Hak Akses', description='Memperbarui akun dan role pengguna', object_repr=edited_user.username)
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
        log_activity(request, action=f'Menghapus pengguna {username}', action_type='delete', module='Pengguna & Hak Akses', description='Menghapus akun pengguna', object_repr=username)
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
        log_activity(request, action='Mengubah profil sendiri', action_type='update', module='Profil', description='Memperbarui profil sendiri')
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
            log_activity(request, action='Mengubah password sendiri', action_type='update', module='Keamanan Akun', description='Mengubah password sendiri')
            messages.success(request, 'Password berhasil diubah.')
            return redirect('accounts:edit_profile')
        messages.error(request, 'Password belum bisa diubah. Periksa kembali isian password.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


@owner_required
def activity_logs(request):
    logs = AuditLog.objects.select_related("user", "user__userprofile").prefetch_related("user__userprofile__roles")
    q = request.GET.get("q", "").strip()
    user_id = request.GET.get("user", "").strip()
    action_type = request.GET.get("action_type", "").strip()
    module = request.GET.get("module", "").strip()
    date_from = parse_date(request.GET.get("date_from", ""))
    date_to = parse_date(request.GET.get("date_to", ""))

    if q:
        logs = logs.filter(Q(action__icontains=q) | Q(description__icontains=q) | Q(path__icontains=q) | Q(user__username__icontains=q) | Q(user__first_name__icontains=q))
    if user_id:
        logs = logs.filter(user_id=user_id)
    if action_type:
        logs = logs.filter(action_type=action_type)
    if module:
        logs = logs.filter(module=module)
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    page_obj = paginate_queryset(request, logs, per_page=25)
    all_users = User.objects.filter(activity_logs__isnull=False).distinct().order_by("first_name", "username")
    modules = AuditLog.objects.exclude(module="").values_list("module", flat=True).distinct().order_by("module")
    summary = AuditLog.objects.aggregate(total=Count("id"))
    today_count = AuditLog.objects.filter(created_at__date=timezone.localdate()).count()
    failed_count = AuditLog.objects.filter(action_type="failed").count()
    active_users = AuditLog.objects.exclude(user=None).values("user").distinct().count()
    return render(request, "accounts/activity_logs.html", {
        "logs": page_obj, "page_obj": page_obj, "all_users": all_users, "modules": modules,
        "action_choices": AuditLog.ACTION_TYPES, "summary": summary, "today_count": today_count,
        "failed_count": failed_count, "active_users": active_users,
    })


@owner_required
def activity_log_detail(request, log_id):
    log = get_object_or_404(AuditLog.objects.select_related("user", "user__userprofile").prefetch_related("user__userprofile__roles"), id=log_id)
    return render(request, "accounts/activity_log_detail.html", {"log": log})
