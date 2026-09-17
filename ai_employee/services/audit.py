from accounts.models import AuditLog
from ..models import AIAuditLog

def record_ai_event(action, actor, event, details=None, request=None):
    details = details or {}
    AIAuditLog.objects.create(action=action, actor=actor, event=event, details=details)
    if actor and request is not None:
        AuditLog.objects.create(
            user=actor,
            action=f'AI Employee: {event}',
            action_type='create' if event in {'draft_created', 'executed'} else 'access',
            module='ai_employee',
            description=action.command[:1000],
            object_repr=str(action),
            method=getattr(request, 'method', ''),
            path=getattr(request, 'path', ''),
            status_code=200,
            ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if hasattr(request, 'META') else '',
            session_key=getattr(getattr(request, 'session', None), 'session_key', '') or '',
            metadata={'ai_action_id': action.id, 'event': event, **details},
        )
