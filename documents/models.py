from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .utils import generate_unique_slug


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Название')

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name


class Document(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активный'),
        ('archived', 'В архиве'),
        ('draft', 'Черновик'),
    ]

    title = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Категория'
    )
    pdf_file = models.FileField(upload_to='pdfs/', blank=True, null=True, verbose_name='PDF файл')
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Сумма договора')
    initiator = models.CharField(max_length=255, blank=True, verbose_name='Инициатор')
    author = models.CharField(max_length=150, blank=True, verbose_name='Автор')
    tags = models.ManyToManyField(Tag, blank=True, related_name='documents', verbose_name='Теги')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='Статус')
    start_date = models.DateField(null=True, blank=True, verbose_name='Дата начала')
    end_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания')
    pdf_text = models.TextField(blank=True, editable=False, verbose_name='Текст PDF')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Дата добавления')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name='Slug')

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self.title, self)
        super().save(*args, **kwargs)

    def amount_formatted(self):
        return f'{self.amount:,.0f} ₸'

    def tag_names(self):
        return ', '.join(self.tags.values_list('name', flat=True))

    def is_expiring_soon(self, days=30):
        if not self.end_date:
            return False
        today = timezone.localdate()
        return today <= self.end_date <= today + timezone.timedelta(days=days)

    def is_expired(self):
        if not self.end_date:
            return False
        return self.end_date < timezone.localdate()


class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions', verbose_name='Документ')
    pdf_file = models.FileField(upload_to='pdfs/versions/', verbose_name='PDF файл')
    version_number = models.PositiveIntegerField(verbose_name='Версия')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Загружено')
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Пользователь'
    )

    class Meta:
        verbose_name = 'Версия документа'
        verbose_name_plural = 'Версии документов'
        ordering = ['-version_number']

    def __str__(self):
        return f'{self.document.title} v{self.version_number}'


class AuditLog(models.Model):
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Создание'),
        (ACTION_UPDATE, 'Изменение'),
        (ACTION_DELETE, 'Удаление'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Пользователь')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name='Действие')
    model_name = models.CharField(max_length=50, verbose_name='Модель')
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='ID объекта')
    object_repr = models.CharField(max_length=255, verbose_name='Объект')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')
    details = models.JSONField(default=dict, blank=True, verbose_name='Детали')

    class Meta:
        verbose_name = 'Журнал аудита'
        verbose_name_plural = 'Журнал аудита'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.get_action_display()}: {self.object_repr}'


class UserProfile(models.Model):
    ROLE_VIEWER = 'viewer'
    ROLE_EDITOR = 'editor'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_VIEWER, 'Просмотр'),
        (ROLE_EDITOR, 'Редактор'),
        (ROLE_ADMIN, 'Администратор'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='Пользователь')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_EDITOR, verbose_name='Роль')

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'


class UserNotificationSettings(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_settings',
        verbose_name='Пользователь',
    )
    notify_email_enabled = models.BooleanField(default=True, verbose_name='Email-уведомления')
    notify_email = models.EmailField(blank=True, verbose_name='Email')
    notify_telegram_enabled = models.BooleanField(default=False, verbose_name='Telegram-уведомления')
    telegram_chat_id = models.CharField(max_length=128, blank=True, verbose_name='Telegram Chat ID')
    notify_30_days = models.BooleanField(default=True, verbose_name='За 30 дней')
    notify_7_days = models.BooleanField(default=True, verbose_name='За 7 дней')
    notify_on_expiry_day = models.BooleanField(default=False, verbose_name='В день истечения')
    dashboard_expiry_days = models.PositiveIntegerField(default=30, verbose_name='Порог виджета (дней)')

    class Meta:
        verbose_name = 'Настройки уведомлений'
        verbose_name_plural = 'Настройки уведомлений'

    def __str__(self):
        return f'Уведомления: {self.user.username}'

    @property
    def notifications_enabled(self):
        return self.notify_email_enabled or self.notify_telegram_enabled
