from django.contrib import admin

from .models import AIInteraction, LegalChunk


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
