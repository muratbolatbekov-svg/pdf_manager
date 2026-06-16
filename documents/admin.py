from django.contrib import admin

from .models import AuditLog, ApiKey, Category, Document, DocumentComment, DocumentLink, DocumentVersion, Tag, UserNotificationSettings, UserProfile


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'masked_key', 'created_by', 'created_at', 'last_used_at']
    readonly_fields = ['key_hash', 'key_suffix', 'created_at', 'last_used_at']


@admin.register(DocumentLink)
class DocumentLinkAdmin(admin.ModelAdmin):
    list_display = ['document', 'linked', 'link_type', 'created_at']
    list_filter = ['link_type']


@admin.register(DocumentComment)
class DocumentCommentAdmin(admin.ModelAdmin):
    list_display = ['document', 'user', 'created_at']
    search_fields = ['text', 'document__title', 'user__username']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'signatory', 'amount', 'status', 'end_date', 'created_at']
    list_filter = ['status', 'category']
    search_fields = ['title', 'signatory', 'pdf_text']
    list_editable = ['status']
    prepopulated_fields = {'slug': ('title',)}


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ['document', 'version_number', 'file_size', 'uploaded_at', 'uploaded_by']
    list_filter = ['uploaded_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'model_name', 'object_repr']
    list_filter = ['action', 'model_name']
    readonly_fields = ['timestamp', 'user', 'action', 'model_name', 'object_id', 'object_repr', 'details']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'role']
    list_filter = ['role']


@admin.register(UserNotificationSettings)
class UserNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'notify_email_enabled',
        'notify_telegram_enabled',
        'dashboard_expiry_days',
    ]
    search_fields = ['user__username', 'notify_email', 'telegram_chat_id']
