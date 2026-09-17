from django.db.models import Q
from django.db.models.fields import CharField, TextField, EmailField, IntegerField, DecimalField, FloatField


def apply_database_search(queryset, keyword, max_related_fields=24):
    """Pencarian database generik untuk tabel yang dipaginasi.

    Mencari pada field teks model dan field teks relasi ForeignKey satu tingkat.
    Field angka juga dapat dicari dengan nilai persis.
    """
    keyword = str(keyword or '').strip()
    if not keyword or not hasattr(queryset, 'model'):
        return queryset

    model = queryset.model
    condition = Q()
    related_count = 0

    for field in model._meta.get_fields():
        if getattr(field, 'auto_created', False) and not getattr(field, 'concrete', False):
            continue

        if isinstance(field, (CharField, TextField, EmailField)):
            condition |= Q(**{f'{field.name}__icontains': keyword})
            continue

        if isinstance(field, IntegerField):
            try:
                numeric_value = int(keyword)
            except (TypeError, ValueError):
                continue
            condition |= Q(**{field.name: numeric_value})
            continue

        if isinstance(field, (DecimalField, FloatField)):
            try:
                numeric_value = float(keyword.replace(',', '.'))
            except (TypeError, ValueError):
                continue
            condition |= Q(**{field.name: numeric_value})
            continue

        if getattr(field, 'many_to_one', False) and getattr(field, 'related_model', None):
            for rel_field in field.related_model._meta.get_fields():
                if related_count >= max_related_fields:
                    break
                if isinstance(rel_field, (CharField, TextField, EmailField)):
                    condition |= Q(**{f'{field.name}__{rel_field.name}__icontains': keyword})
                    related_count += 1

    if not condition.children:
        return queryset
    return queryset.filter(condition).distinct()
