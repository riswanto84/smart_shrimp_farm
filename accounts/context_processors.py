from .rbac import normalized_roles, has_permission, visible_menu, visible_bottom_menu, primary_role_label

def user_roles(request):
    roles = []
    if request.user.is_authenticated:
        roles = normalized_roles(request.user)
    return {
        'USER_ROLES': roles,
        'IS_OWNER': request.user.is_authenticated and has_permission(request.user, 'accounts.users'),
        'APP_MENU': visible_menu(request.user) if request.user.is_authenticated else [],
        'BOTTOM_MENU': visible_bottom_menu(request.user) if request.user.is_authenticated else [],
        'PRIMARY_ROLE_LABEL': primary_role_label(request.user) if request.user.is_authenticated else '',
        'can': lambda perm: has_permission(request.user, perm),
    }
