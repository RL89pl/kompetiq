"""Panel „Baza wiedzy”: źródła urzędu, wyłączanie źródeł wspólnych, zastępowanie przepisów, uprawnienia."""
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from apps.assistant.models import KnowledgeDocument, LegalChunk
from apps.assistant.retrieval import search_scored
from apps.institutions.models import Institution, Role
from tests.conftest import make_user

TEXT = ('Zarządzenie dyrektora generalnego w sprawie harmonogramu ocen okresowych w urzędzie.\n\n'
        'Oceny okresowe w urzędzie przeprowadza się w terminie do 30 listopada każdego roku. '
        'Kalendarz ocen okresowych ogłasza komórka kadr do 15 września.\n\n') * 3


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def admin_user(org):
    return make_user(org.inst, 'adm', Role.ADMIN)


def upload(c, name='zarzadzenie.txt', data=TEXT.encode(), **extra):
    return c.post('/api/v1/knowledge-documents/',
                  {'file': SimpleUploadedFile(name, data), 'title': 'Zarządzenie DG nr 5/2026', 'kind': 'OTHER', **extra},
                  format='multipart')


def test_admin_uploads_source_visible_only_in_own_institution(org, api, admin_user):
    r = upload(api(admin_user))
    assert r.status_code == 201, r.data
    doc = KnowledgeDocument.objects.get(pk=r.data['id'])
    assert doc.institution == org.inst and doc.chunks.count() >= 1 and doc.file.name
    assert search_scored('kalendarz ocen okresowych komórka kadr', institution=org.inst)[0][1].document == doc
    other = Institution.objects.create(name='Urząd B', slug='b')
    assert all(c.document != doc for _, c in search_scored('kalendarz ocen okresowych komórka kadr', institution=other))
    # widok listy: kadry widzą, ale nie zmieniają
    hr = api(org.hr)
    assert any(d['id'] == doc.id and d['chunk_count'] >= 1 for d in hr.get('/api/v1/knowledge-documents/').data)
    assert upload(hr).status_code == 403
    assert hr.delete(f'/api/v1/knowledge-documents/{doc.id}/').status_code == 403
    assert api(org.sup).get('/api/v1/knowledge-documents/').status_code == 403


def test_rejects_bad_files(org, api, admin_user):
    c = api(admin_user)
    assert upload(c, name='wirus.exe').status_code == 400
    assert upload(c, name='pusty.txt', data=b'krotko').status_code == 400
    assert upload(c, name='zly.pdf', data=b'%PDF-to nie jest pdf').status_code == 400
    assert not KnowledgeDocument.objects.filter(institution=org.inst).exists()


def test_shared_source_disable_and_replace(org, api, admin_user, competency_model):
    call_command('ingest_legal_docs', stdout=io.StringIO())
    act = KnowledgeDocument.objects.get(builtin=True, kind='ACT')
    c = api(admin_user)
    # źródła wspólnego urząd nie usuwa
    assert c.delete(f'/api/v1/knowledge-documents/{act.id}/').status_code == 403
    r = c.post(f'/api/v1/knowledge-documents/{act.id}/disable/')
    assert r.status_code == 200 and r.data['disabled_here'] is True
    assert all(ch.document_id != act.id for _, ch in search_scored('sprzeciw od oceny okresowej', k=20,
                                                                    institution=org.inst))
    other = Institution.objects.create(name='Urząd B', slug='b')
    assert any(ch.document_id == act.id for _, ch in search_scored('sprzeciw od oceny okresowej', k=20,
                                                                    institution=other))
    assert c.post(f'/api/v1/knowledge-documents/{act.id}/enable/').data['disabled_here'] is False
    # nowa wersja przepisu: wgranie źródła ze wskazaniem „zastępuje” wyłącza stare w tym urzędzie
    r = upload(c, replaces=act.id, valid_from='2027-01-01')
    assert r.status_code == 201 and r.data['replaces_title'] == act.title
    assert act.disabled_for.filter(pk=org.inst.pk).exists()
    # przebudowa wbudowanej bazy (np. przy wdrożeniu) zachowuje wyłączenia i źródła urzędu
    call_command('ingest_legal_docs', stdout=io.StringIO())
    assert KnowledgeDocument.objects.get(pk=act.pk).disabled_for.filter(pk=org.inst.pk).exists()
    assert KnowledgeDocument.objects.filter(institution=org.inst).count() == 1
    assert LegalChunk.objects.filter(document__isnull=True).count() == 0


def test_edit_and_delete_own_source(org, api, admin_user):
    c = api(admin_user)
    doc_id = upload(c).data['id']
    r = c.patch(f'/api/v1/knowledge-documents/{doc_id}/', {'title': 'Zarządzenie DG nr 6/2026', 'is_active': False},
                format='json')
    assert r.status_code == 200 and r.data['is_active'] is False
    assert set(LegalChunk.objects.filter(document_id=doc_id).values_list('title', flat=True)) == {'Zarządzenie DG nr 6/2026'}
    assert not search_scored('kalendarz ocen okresowych komórka kadr', institution=org.inst) or \
        all(ch.document_id != doc_id for _, ch in search_scored('kalendarz ocen okresowych komórka kadr', institution=org.inst))
    assert c.delete(f'/api/v1/knowledge-documents/{doc_id}/').status_code == 204
    assert not LegalChunk.objects.filter(document_id=doc_id).exists()


def test_upload_docx(org, api, admin_user):
    from docx import Document
    d = Document()
    for para in TEXT.split('\n\n'):
        if para.strip():
            d.add_paragraph(para)
    buf = io.BytesIO()
    d.save(buf)
    r = upload(api(admin_user), name='zarzadzenie.docx', data=buf.getvalue())
    assert r.status_code == 201 and r.data['chunk_count'] >= 1
    doc = KnowledgeDocument.objects.get(pk=r.data['id'])
    assert doc.chunks.count() >= 1 and 'harmonogramu ocen' in doc.chunks.first().text
