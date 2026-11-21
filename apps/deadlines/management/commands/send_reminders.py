from django.core.management.base import BaseCommand

from apps.deadlines.reminders import send_due_reminders


class Command(BaseCommand):
    help = ('Wysyła przypomnienia o zbliżających się i przekroczonych terminach (14, 7, 1 dzień, w dniu terminu, '
            'po terminie). Bez duplikatów — uruchamiaj codziennie z crona hosta.')

    def handle(self, **opts):
        n = send_due_reminders()
        self.stdout.write(self.style.SUCCESS(f'Wysłano przypomnień: {n}'))
