from django.contrib import admin

from .models import AIInteraction, KnowledgeDocument, LegalChunk


@admin.register(AIInteraction)
class AIInteractionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'feature', 'user', 'institution', 'model', 'outcome', 'input_tokens',
                    'output_tokens', 'cache_read_tokens', 'duration_ms')
    list_filter = ('feature', 'outcome', 'institution')
    readonly_fields = [f.name for f in AIInteraction._meta.fields]


@admin.register(LegalChunk)
class LegalChunkAdmin(admin.ModelAdmin):
    list_display = ('title', 'page')
    list_filter = ('title',)


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    """Superużytkownik: źródła wspólne dla wszystkich urzędów (institution puste)."""
    list_display = ('title', 'kind', 'institution', 'builtin', 'valid_from', 'is_active', 'updated_at')
    list_filter = ('kind', 'builtin', 'is_active', 'institution')
    search_fields = ('title', 'source')
    filter_horizontal = ('disabled_for',)
    readonly_fields = ('builtin', 'created_at', 'updated_at')
