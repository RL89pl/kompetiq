from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.competencies.importer import ImportError_, import_model


class Command(BaseCommand):
    help = 'Importuje model kompetencji z pliku xlsx (domyślnie docs_assets/Model_kompetencji.xlsx).'

    def add_arguments(self, parser):
        parser.add_argument('path', nargs='?', default=str(settings.LEGAL_DOCS_DIR / 'Model_kompetencji.xlsx'))
        parser.add_argument('--model-version', dest='model_version', default='1.0')
        parser.add_argument('--replace', action='store_true')
        parser.add_argument('--if-missing', action='store_true', help='nic nie rób, jeśli model już istnieje')

    def handle(self, path, model_version, replace, if_missing, **opts):
        from apps.competencies.models import CompetencyModel
        if if_missing and CompetencyModel.objects.filter(institution__isnull=True).exists():
            self.stdout.write('Model kompetencji już istnieje — pomijam.')
            return
        try:
            model = import_model(path, version=model_version, replace=replace)
        except ImportError_ as e:
            raise CommandError(str(e))
        n_c = model.competencies.count()
        n_i = sum(c.indicators.count() for c in model.competencies.all())
        self.stdout.write(self.style.SUCCESS(f'Zaimportowano {model}: {n_c} kompetencji, {n_i} wskaźników.'))
