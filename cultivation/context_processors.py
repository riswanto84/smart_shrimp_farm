from .models import CultivationCycle


def cultivation_cycle_context(request):
    cycles = CultivationCycle.objects.all()
    selected = None
    selected_id = request.session.get('selected_cycle_id')
    if selected_id:
        selected = cycles.filter(pk=selected_id).first()
    if selected is None:
        selected = cycles.filter(status__in=['preparation', 'active', 'harvest']).first() or cycles.first()
        if selected:
            request.session['selected_cycle_id'] = selected.pk
    return {
        'cultivation_cycles': cycles,
        'selected_cycle': selected,
    }
