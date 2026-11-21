from apps.competencies.models import BehavioralIndicator, Competency, IndicatorLevelDescription


def test_import_counts(competency_model):
    assert Competency.objects.filter(model=competency_model).count() == 14
    assert BehavioralIndicator.objects.filter(competency__model=competency_model).count() == 49
    assert IndicatorLevelDescription.objects.count() == 49 * 5
    wsp = Competency.objects.get(code='wspolpraca')
    assert wsp.indicators.count() == 6
    first = wsp.indicators.first()
    assert first.text.startswith('Włączanie się w działania')
    assert first.levels.get(level=3).text.startswith('Podejmuje uzgodnioną część')
