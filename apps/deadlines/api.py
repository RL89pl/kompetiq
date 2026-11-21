from collections import Counter, defaultdict
from datetime import date

from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assessments.api import assessments_visible_to, get_visible_assessment
from apps.assessments.models import Assessment, Status
from apps.institutions.models import Role
from apps.institutions.permissions import IsHROrAdmin, membership

from .models import Notification
from .notify import hr_users, notify, unit_head_for
from .reminders import send_due_reminders
from .service import deadlines_for


def _visible(request):
    m = membership(request)
    return assessments_visible_to(Assessment.objects.filter(institution=m.institution), request.user, m) \
        .select_related('employee__org_unit__head', 'evaluator', 'unit_head', 'institution')


class UpcomingDeadlinesView(APIView):
    """Nadchodzące i przekroczone terminy w ocenach widocznych dla użytkownika."""

    def get(self, request):
        horizon = min(int(request.query_params.get('days', 60)), 730)
        return Response(deadlines_for(list(_visible(request)), horizon_days=horizon))


class HROverviewView(APIView):
    """Panel HR/administratora: statusy procesów, terminy, komórki, przekroczenia."""

    permission_classes = [IsHROrAdmin]

    def get(self, request):
        items = list(_visible(request))
        today = date.today()
        dls = deadlines_for(items, horizon_days=30, today=today, include_development=False)
        next_dl = {}
        for d in dls:
            next_dl.setdefault(d['assessment'], d)
        overdue_ids = {d['assessment'] for d in dls if d['overdue']}
        by_status = Counter(a.status for a in items)
        by_form = Counter(a.form_type for a in items if a.status != Status.CANCELLED)
        units = defaultdict(lambda: {'in_progress': 0, 'done': 0, 'overdue': 0, 'negative': 0})
        rows = []
        for a in items:
            unit = a.employee.org_unit.name if a.employee.org_unit else '(bez komórki)'
            done = a.status in (Status.FINALIZED, Status.APPROVED, Status.ACKNOWLEDGED)
            if a.status == Status.CANCELLED:
                continue
            units[unit]['done' if done else 'in_progress'] += 1
            units[unit]['overdue'] += a.id in overdue_ids
            units[unit]['negative'] += a.result == 'NEGATIVE'
            nd = next_dl.get(a.id)
            rows.append({
                'id': a.id, 'employee': a.employee.full_name, 'position': a.employee.position, 'unit': unit,
                'evaluator': a.evaluator.get_full_name() or a.evaluator.username, 'evaluator_id': a.evaluator_id,
                'form_type': a.form_type, 'status': a.status, 'status_label': a.get_status_display(),
                'result': a.result, 'updated_at': a.updated_at,
                'next_deadline': nd and {'label': nd['label'], 'date': nd['date'], 'days_left': nd['days_left'],
                                         'overdue': nd['overdue']},
            })
        rows.sort(key=lambda r: (r['next_deadline'] is None, r['next_deadline']['date'] if r['next_deadline'] else today))
        return Response({
            'totals': {'all': len(rows), 'overdue': len(overdue_ids),
                       'in_progress': sum(v['in_progress'] for v in units.values()),
                       'done': sum(v['done'] for v in units.values()),
                       'negative': sum(v['negative'] for v in units.values())},
            'by_status': [{'status': s, 'label': Status(s).label, 'count': by_status.get(s, 0)}
                          for s in Status.values if s != Status.CANCELLED],
            'by_form': dict(by_form),
            'units': [{'unit': k, **v} for k, v in sorted(units.items())],
            'assessments': rows,
            'deadlines': dls,
        })


class SendRemindersView(APIView):
    """Ręczne uruchomienie przypomnień o terminach (HR/administrator)."""

    permission_classes = [IsHROrAdmin]

    def post(self, request):
        n = send_due_reminders(institution=membership(request).institution)
        return Response({'sent': n})


class AssessmentMessageView(APIView):
    """Komunikacja w procesie: wiadomość / przypomnienie do oceniającego, kierującego komórką lub kadr."""

    def post(self, request, pk):
        a = get_visible_assessment(request, pk)
        m = membership(request)
        to = request.data.get('to')
        text = (request.data.get('message') or '').strip()
        if len(text) > 1000:
            raise ValidationError('Wiadomość do 1000 znaków.')
        recipients = {'evaluator': [a.evaluator], 'unit_head': [unit_head_for(a)], 'hr': hr_users(a.institution)}.get(to)
        if recipients is None:
            raise ValidationError('Nieznany adresat.')
        if to == 'evaluator' and m.role not in (Role.HR, Role.ADMIN, Role.UNIT_HEAD):
            raise PermissionDenied()
        kind = Notification.Kind.REMINDER if request.data.get('reminder') else Notification.Kind.MESSAGE
        who = request.user.get_full_name() or request.user.username
        title = (f'Przypomnienie od {who}: ocena {a.employee.full_name}' if kind == Notification.Kind.REMINDER
                 else f'Wiadomość od {who}: ocena {a.employee.full_name}')
        sent = 0
        for r in recipients:
            if r is not None and r.id != request.user.id:
                sent += notify(r, institution=a.institution, kind=kind, assessment=a, sender=request.user,
                               title=title, body=text) is not None
        if not sent:
            raise ValidationError('Brak adresata (np. komórka nie ma przypisanego kierującego).')
        return Response({'sent': sent}, status=status.HTTP_201_CREATED)


class NotificationSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    kind_label = serializers.CharField(source='get_kind_display', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'kind', 'kind_label', 'title', 'body', 'assessment', 'sender_name', 'read_at', 'created_at']

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() if obj.sender else 'Kompas Kompetencji'


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user,
                                         institution=membership(self.request).institution).select_related('sender')
        if self.request.query_params.get('unread') == '1':
            qs = qs.filter(read_at__isnull=True)
        return qs[:100]

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        Notification.objects.filter(pk=pk, recipient=request.user).update(read_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)
