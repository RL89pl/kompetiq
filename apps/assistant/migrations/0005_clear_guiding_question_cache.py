"""Jednorazowe wyczyszczenie zapamiętanych pytań pomocniczych.

Wcześniejsze wersje promptu nie podawały modelowi bieżącej daty (w pytaniach zdarzały się lata z danych
treningowych, np. 2023) ani nie zabraniały numerów wskaźników w tekście. Pytania wygenerują się ponownie przy
pierwszym użyciu.
"""
from django.db import migrations


def clear(apps, schema_editor):
    apps.get_model('assistant', 'GuidingQuestionCache').objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [('assistant', '0004_knowledge_documents')]
    operations = [migrations.RunPython(clear, migrations.RunPython.noop)]
