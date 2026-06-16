from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .utils import generate_unique_slug


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('Название'))
    description = models.TextField(blank=True, verbose_name=_('Описание'))
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _('Категория')
        verbose_name_plural = _('Категории')

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name=_('Название'))

    class Meta:
        verbose_name = _('Тег')
        verbose_name_plural = _('Теги')
        ordering = ['name']

    def __str__(self):
        return self.name


class Document(models.Model):
    STATUS_CHOICES = [
        ('active', _('Активный')),
        ('archived', _('В архиве')),
        ('draft', _('Черновик')),
    ]

    title = models.CharField(max_length=255, verbose_name=_('Название'))
    description = models.TextField(blank=True, verbose_name=_('Описание'))
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Категория')
    )
    pdf_file = models.FileField(upload_to='pdfs/', blank=True, null=True, verbose_name=_('PDF файл'))
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=_('Сумма договора'))
    signatory = models.CharField(max_length=255, blank=True, verbose_name=_('Подписант'))
    author = models.CharField(max_length=150, blank=True, verbose_name=_('Автор'))
    tags = models.ManyToManyField(Tag, blank=True, related_name='documents', verbose_name=_('Теги'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name=_('Статус'))
    start_date = models.DateField(null=True, blank=True, verbose_name=_('Дата начала'))
    end_date = models.DateField(null=True, blank=True, verbose_name=_('Дата окончания'))
    pdf_text = models.TextField(blank=True, editable=False, verbose_name=_('Текст PDF'))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_('Дата добавления'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name='Slug')

    class Meta:
        verbose_name = _('Документ')
        verbose_name_plural = _('Документы')
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

    def current_version_number(self):
        return self.versions.count() + 1

    def current_pdf_size(self):
        if not self.pdf_file:
            return None
        try:
            return self.pdf_file.size
        except (OSError, TypeError, ValueError):
            return None


class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions', verbose_name=_('Документ'))
    pdf_file = models.FileField(upload_to='pdfs/versions/', verbose_name=_('PDF файл'))
    version_number = models.PositiveIntegerField(verbose_name=_('Версия'))
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('Размер файла'))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Загружено'))
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Пользователь')
    )

    class Meta:
        verbose_name = _('Версия документа')
        verbose_name_plural = _('Версии документов')
        ordering = ['-version_number']

    def __str__(self):
        return f'{self.document.title} v{self.version_number}'

    def file_size_display(self):
        from .utils import format_file_size
        return format_file_size(self.file_size)


class DocumentComment(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='comments', verbose_name=_('Документ')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Пользователь'))
    text = models.TextField(max_length=2000, verbose_name=_('Текст'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создан'))

    class Meta:
        verbose_name = _('Комментарий')
        verbose_name_plural = _('Комментарии')
        ordering = ['created_at']

    def __str__(self):
        return f'Комментарий к {self.document.title}'


class DocumentLink(models.Model):
    TYPE_SUPPLEMENT = 'supplement'
    TYPE_ACT = 'act'
    TYPE_INVOICE = 'invoice'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_SUPPLEMENT, _('Дополнительное соглашение')),
        (TYPE_ACT, _('Акт выполненных работ')),
        (TYPE_INVOICE, _('Счёт')),
        (TYPE_OTHER, _('Другое')),
    ]
    TYPE_SHORT_LABELS = {
        TYPE_SUPPLEMENT: _('Доп. согл.'),
        TYPE_ACT: _('Акт'),
        TYPE_INVOICE: _('Счёт'),
        TYPE_OTHER: _('Другое'),
    }

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='outgoing_links', verbose_name=_('Документ')
    )
    linked = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='incoming_links', verbose_name=_('Связанный документ')
    )
    link_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_OTHER, verbose_name=_('Тип связи'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))

    class Meta:
        db_table = 'document_links'
        verbose_name = _('Связь документов')
        verbose_name_plural = _('Связи документов')
        constraints = [
            models.UniqueConstraint(fields=['document', 'linked'], name='unique_document_link'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.document.title} → {self.linked.title}'

    def short_label(self):
        return str(self.TYPE_SHORT_LABELS.get(self.link_type, self.link_type))


class AuditLog(models.Model):
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_CHOICES = [
        (ACTION_CREATE, _('Создание')),
        (ACTION_UPDATE, _('Изменение')),
        (ACTION_DELETE, _('Удаление')),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Пользователь'))
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name=_('Действие'))
    model_name = models.CharField(max_length=50, verbose_name=_('Модель'))
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('ID объекта'))
    object_repr = models.CharField(max_length=255, verbose_name=_('Объект'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Время'))
    details = models.JSONField(default=dict, blank=True, verbose_name=_('Детали'))

    class Meta:
        verbose_name = _('Журнал изменений')
        verbose_name_plural = _('Журнал изменений')
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.get_action_display()}: {self.object_repr}'


class UserProfile(models.Model):
    ROLE_VIEWER = 'viewer'
    ROLE_MANAGER = 'manager'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_VIEWER, _('Читатель')),
        (ROLE_MANAGER, _('Менеджер')),
        (ROLE_ADMIN, _('Администратор')),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name=_('Пользователь'))
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_MANAGER, verbose_name=_('Роль'))

    class Meta:
        verbose_name = _('Профиль пользователя')
        verbose_name_plural = _('Профили пользователей')

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'


class UserNotificationSettings(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_settings',
        verbose_name=_('Пользователь'),
    )
    notify_email_enabled = models.BooleanField(default=True, verbose_name=_('Email-уведомления'))
    notify_email = models.EmailField(blank=True, verbose_name=_('Email'))
    notify_telegram_enabled = models.BooleanField(default=False, verbose_name=_('Telegram-уведомления'))
    telegram_chat_id = models.CharField(max_length=128, blank=True, verbose_name=_('Telegram Chat ID'))
    notify_30_days = models.BooleanField(default=True, verbose_name=_('За 30 дней'))
    notify_7_days = models.BooleanField(default=True, verbose_name=_('За 7 дней'))
    notify_on_expiry_day = models.BooleanField(default=False, verbose_name=_('В день истечения'))
    dashboard_expiry_days = models.PositiveIntegerField(default=30, verbose_name=_('Порог виджета (дней)'))

    class Meta:
        verbose_name = _('Настройки уведомлений')
        verbose_name_plural = _('Настройки уведомлений')

    def __str__(self):
        return f'Уведомления: {self.user.username}'

    @property
    def notifications_enabled(self):
        return self.notify_email_enabled or self.notify_telegram_enabled


class ApiKey(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('Название'))
    key_hash = models.CharField(max_length=64, unique=True, verbose_name=_('Хеш ключа'))
    key_suffix = models.CharField(max_length=4, verbose_name=_('Суффикс'))
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='api_keys', verbose_name=_('Создал')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создан'))
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Последнее использование'))

    class Meta:
        verbose_name = _('API-ключ')
        verbose_name_plural = _('API-ключи')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def masked_key(self):
        return f'sk-...{self.key_suffix}'

    @classmethod
    def create_key(cls, name, user):
        import hashlib
        import secrets

        raw_key = f'sk-{secrets.token_urlsafe(32)}'
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        obj = cls.objects.create(
            name=name,
            key_hash=key_hash,
            key_suffix=raw_key[-4:],
            created_by=user,
        )
        return obj, raw_key

    @classmethod
    def authenticate(cls, raw_key):
        import hashlib

        if not raw_key or not raw_key.startswith('sk-'):
            return None
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return cls.objects.filter(key_hash=key_hash).select_related('created_by').first()
