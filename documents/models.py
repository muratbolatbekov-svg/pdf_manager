from django.db import models
from django.utils import timezone
from django.utils.text import slugify

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
    pdf_file = models.FileField(upload_to='pdfs/', blank=True, null=True, verbose_name="PDF файл")
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Сумма договора")
    initiator = models.CharField(max_length=255, blank=True, verbose_name="Инициатор")
    author = models.CharField(max_length=150, blank=True, verbose_name="Автор")
    tags = models.CharField(max_length=500, blank=True, verbose_name="Теги")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Статус")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата добавления")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name='Slug')

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def amount_formatted(self):
        return f"{self.amount:,.0f} ₸"
