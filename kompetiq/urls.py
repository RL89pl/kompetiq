from django.conf import settings
from django.contrib import admin
from django.views.static import serve as static_serve
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.assessments.api import AssessmentViewSet, CriterionViewSet, EvidenceViewSet
from apps.assistant.api import AssistantFeatureView, AssistantStatusView, ConversationViewSet, InteractionOutcomeView
from apps.competencies.api import CompetencyModelViewSet
from apps.deadlines.api import (AssessmentMessageView, HROverviewView, NotificationViewSet, SendRemindersView,
                                UpcomingDeadlinesView)
from apps.development.api import ActionViewSet, PlanViewSet
from apps.documents.api import ExportView
from apps.employees.api import EmployeeViewSet, JobDescriptionViewSet
from apps.institutions.api import (CsrfView, InstitutionUsersView, LoginView, LogoutView, MeView, OrgUnitViewSet,
                                   SwitchInstitutionView)

from .views import health, spa

router = DefaultRouter()
router.register('org-units', OrgUnitViewSet, basename='org-unit')
router.register('employees', EmployeeViewSet, basename='employee')
router.register('job-descriptions', JobDescriptionViewSet, basename='job-description')
router.register('competency-models', CompetencyModelViewSet, basename='competency-model')
router.register('assessments', AssessmentViewSet, basename='assessment')
router.register('criteria', CriterionViewSet, basename='criterion')
router.register('evidence', EvidenceViewSet, basename='evidence')
router.register('development-plans', PlanViewSet, basename='development-plan')
router.register('development-actions', ActionViewSet, basename='development-action')
router.register('notifications', NotificationViewSet, basename='notification')
router.register('assistant/conversations', ConversationViewSet, basename='conversation')

api = [
    path('auth/csrf/', CsrfView.as_view()),
    path('auth/login/', LoginView.as_view()),
    path('auth/logout/', LogoutView.as_view()),
    path('auth/me/', MeView.as_view()),
    path('auth/switch-institution/', SwitchInstitutionView.as_view()),
    path('users/', InstitutionUsersView.as_view()),
    path('deadlines/upcoming/', UpcomingDeadlinesView.as_view()),
    path('hr/overview/', HROverviewView.as_view()),
    path('hr/send-reminders/', SendRemindersView.as_view()),
    path('assessments/<int:pk>/message/', AssessmentMessageView.as_view()),
    path('assessments/<int:pk>/assistant/<slug:feature>/', AssistantFeatureView.as_view()),
    path('assessments/<int:pk>/export/<slug:kind>/', ExportView.as_view()),
    path('assistant/status/', AssistantStatusView.as_view()),
    path('assistant/interactions/<int:pk>/outcome/', InteractionOutcomeView.as_view()),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema')),
    path('', include(router.urls)),
]

urlpatterns = [
    *([re_path(r'^static/(?P<path>.*)$', static_serve, {'document_root': settings.STATIC_ROOT})]
      if settings.SERVE_STATIC else []),
    path('admin/', admin.site.urls),
    path('api/v1/', include(api)),
    path('health/', health),
    re_path(r'^(?!api/|admin/|static/|media/).*$', spa),
]
