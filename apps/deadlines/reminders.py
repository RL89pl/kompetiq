from datetime import date

from apps.assessments.models import Assessment

from .models import Notification
from .notify import notify, unit_head_for
from .service import deadlines_for

# Progi przypomnień: na tyle dni przed terminem oraz po jego przekroczeniu
THRESHOLDS = (14, 7, 1, 0)


def send_due_reminders(today=None, institution=None):
    today = today or date.today()
    qs = Assessment.objects.select_related('employee', 'evaluator', 'institution', 'unit_head',
                                           'employee__org_unit__head')
    if institution is not None:
        qs = qs.filter(institution=institution)
    by_id = {a.id: a for a in qs}
    sent = 0
    for d in deadlines_for(list(by_id.values()), horizon_days=max(THRESHOLDS), today=today):
        a = by_id[d['assessment']]
        if d['overdue']:
            bucket = 'overdue'
        else:
            bucket = next((str(t) for t in sorted(THRESHOLDS) if d['days_left'] <= t), None)
            if bucket is None:
                continue
        recipient = unit_head_for(a) if d['kind'] == 'approval' else a.evaluator
        key = f'{d["kind"]}:{a.id}:{d["date"]}:{bucket}'
        when = 'termin minął' if d['overdue'] else ('dziś' if d['days_left'] == 0 else f'za {d["days_left"]} dni')
        n = notify(recipient, institution=a.institution, kind=Notification.Kind.REMINDER, assessment=a,
                   title=f'{d["label"]}: {a.employee.full_name} ({when}, {d["date"]:%d.%m.%Y})',
                   body=d['basis'], dedupe_key=key)
        sent += n is not None
    return sent
