from django.contrib import admin
from .models import Document, Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'author', 'status', 'pages', 'created_at']
    list_filter = ['status', 'category']
    search_fields = ['title', 'author', 'tags']
    list_editable = ['status']
