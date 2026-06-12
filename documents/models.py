from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name

class Document(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активный'),
        ('archived', 'В архиве'),
        ('draft', 'Черновик'),
    ]

    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Категория")
    file_name = models.CharField(max_length=255, verbose_name="Имя файла")
    file_size = models.PositiveIntegerField(default=0, verbose_name="Размер (байт)")
    pages = models.PositiveIntegerField(default=0, verbose_name="Страниц")
    author = models.CharField(max_length=150, blank=True, verbose_name="Автор")
    tags = models.CharField(max_length=500, blank=True, verbose_name="Теги")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Статус")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата добавления")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def file_size_kb(self):
        return round(self.file_size / 1024, 1)
