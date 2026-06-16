import csv
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from openpyxl import Workbook

from .analytics import PERIOD_CHOICES, build_dashboard_analytics
from .forms import CategoryForm, DocumentForm, NotificationSettingsForm, UserInviteForm, UserRoleForm
from .models import AuditLog, Category, Document, DocumentComment, DocumentVersion, Tag, UserNotificationSettings, UserProfile
from .notifications import expiring_documents_queryset, send_user_invite
from .permissions import get_user_role, role_required
from .utils import comment_to_dict, format_file_size


SORT_OPTIONS = {
    'date_desc': '-created_at',
    'date_asc': 'created_at',
    'amount_desc': '-amount',
    'amount_asc': 'amount',
    'title_asc': 'title',
    'title_desc': '-title',
}

STATUS_LABELS = {
    'active': 'Активный',
    'draft': 'Черновик',
    'archived': 'В архиве',
}


def _parse_decimal(value):
    if not value:
        return None
    try:
        return Decimal(value.replace(',', '.').strip())
    except (InvalidOperation, AttributeError):
        return None


def _parse_document_filters(request):
    category_id_str = request.GET.get('category', '').strip()
    selected_category = None
    if category_id_str:
        try:
            selected_category = int(category_id_str)
        except ValueError:
            selected_category = None

    status = request.GET.get('status', '').strip()
    if status not in STATUS_LABELS:
        status = ''

    sort = request.GET.get('sort', 'date_desc')
    if sort not in SORT_OPTIONS:
        sort = 'date_desc'

    date_from = parse_date(request.GET.get('date_from', '').strip())
    date_to = parse_date(request.GET.get('date_to', '').strip())
    amount_min = _parse_decimal(request.GET.get('amount_min', ''))
    amount_max = _parse_decimal(request.GET.get('amount_max', ''))

    tag_ids = []
    for raw in request.GET.getlist('tag'):
        try:
            tag_ids.append(int(raw.strip()))
        except (TypeError, ValueError):
            continue

    return {
        'category': selected_category,
        'status': status,
        'sort': sort,
        'date_from': date_from,
        'date_to': date_to,
        'amount_min': amount_min,
        'amount_max': amount_max,
        'tags': tag_ids,
    }


def _filters_querystring(filters, exclude=None, page=None):
    exclude = exclude or set()
    params = {}
    if filters['category'] and 'category' not in exclude:
        params['category'] = filters['category']
    if filters['status'] and 'status' not in exclude:
        params['status'] = filters['status']
    if filters['date_from'] and 'date_from' not in exclude:
        params['date_from'] = filters['date_from'].isoformat()
    if filters['date_to'] and 'date_to' not in exclude:
        params['date_to'] = filters['date_to'].isoformat()
    if filters['amount_min'] is not None and 'amount_min' not in exclude:
        params['amount_min'] = str(filters['amount_min'])
    if filters['amount_max'] is not None and 'amount_max' not in exclude:
        params['amount_max'] = str(filters['amount_max'])
    if filters.get('tags') and 'tag' not in exclude:
        for tag_id in filters['tags']:
            params.setdefault('tag', [])
            if isinstance(params['tag'], list):
                params['tag'].append(str(tag_id))
            else:
                params['tag'] = [params['tag'], str(tag_id)]
    if filters['sort'] != 'date_desc' and 'sort' not in exclude:
        params['sort'] = filters['sort']
    if page:
        params['page'] = page
    if 'tag' in params and isinstance(params['tag'], list):
        return urlencode(params, doseq=True)
    return urlencode(params)


def _active_filter_tags(filters, categories, all_tags=None):
    tags = []
    if filters['category']:
        category = categories.filter(pk=filters['category']).first()
        if category:
            tags.append({'param': 'category', 'value': None, 'label': category.name})
    if filters['status']:
        tags.append({'param': 'status', 'value': None, 'label': STATUS_LABELS[filters['status']]})
    if filters['date_from']:
        tags.append({'param': 'date_from', 'value': None, 'label': f'от {filters["date_from"].strftime("%d.%m.%Y")}'})
    if filters['date_to']:
        tags.append({'param': 'date_to', 'value': None, 'label': f'до {filters["date_to"].strftime("%d.%m.%Y")}'})
    if filters['amount_min'] is not None:
        tags.append({'param': 'amount_min', 'value': None, 'label': f'сумма от {filters["amount_min"]:,.0f} ₸'.replace(',', ' ')})
    if filters['amount_max'] is not None:
        tags.append({'param': 'amount_max', 'value': None, 'label': f'сумма до {filters["amount_max"]:,.0f} ₸'.replace(',', ' ')})
    if filters.get('tags') and all_tags is not None:
        tag_map = {t.pk: t.name for t in all_tags}
        for tag_id in filters['tags']:
            if tag_id in tag_map:
                tags.append({'param': 'tag', 'value': tag_id, 'label': tag_map[tag_id]})
    return tags


def _documents_queryset(request):
    filters = _parse_document_filters(request)
    documents = Document.objects.select_related('category').prefetch_related('tags')

    if filters['category']:
        documents = documents.filter(category_id=filters['category'])

    if filters['status']:
        documents = documents.filter(status=filters['status'])

    if filters['date_from']:
        documents = documents.filter(end_date__gte=filters['date_from'])

    if filters['date_to']:
        documents = documents.filter(end_date__lte=filters['date_to'])

    if filters['amount_min'] is not None:
        documents = documents.filter(amount__gte=filters['amount_min'])

    if filters['amount_max'] is not None:
        documents = documents.filter(amount__lte=filters['amount_max'])

    if filters.get('tags'):
        documents = documents.filter(tags__in=filters['tags']).distinct()

    order = SORT_OPTIONS[filters['sort']]
    return documents.order_by(order), filters


def _contract_word(count):
    n = abs(count) % 100
    n1 = n % 10
    if 11 <= n <= 19:
        return 'договоров'
    if n1 == 1:
        return 'договор'
    if 2 <= n1 <= 4:
        return 'договора'
    return 'договоров'


def _get_notification_settings(user):
    settings_obj, _ = UserNotificationSettings.objects.get_or_create(
        user=user,
        defaults={'notify_email': user.email or ''},
    )
    return settings_obj


def _document_stats():
    return {
        'total_docs': Document.objects.count(),
        'active_docs': Document.objects.filter(status='active').count(),
        'archived_docs': Document.objects.filter(status='archived').count(),
        'draft_docs': Document.objects.filter(status='draft').count(),
    }


def home(request):
    context = {}
    if request.user.is_authenticated:
        context.update(_document_stats())
        context['user_role'] = get_user_role(request.user)
    return render(request, 'documents/home.html', context)


@login_required
def dashboard(request):
    today = timezone.localdate()
    user_settings = _get_notification_settings(request.user)
    expiry_days = user_settings.dashboard_expiry_days
    expiring_qs = expiring_documents_queryset(expiry_days)
    expiring_soon = expiring_qs.select_related('category')[:10]
    expiring_count = expiring_qs.count()
    expired = Document.objects.filter(end_date__lt=today, status='active').count()
    expiring_filter_qs = _filters_querystring({
        'category': None,
        'status': 'active',
        'sort': 'date_desc',
        'date_from': today,
        'date_to': today + timezone.timedelta(days=expiry_days),
        'amount_min': None,
        'amount_max': None,
    })
    period = request.GET.get('period', 'current_month')
    months = request.GET.get('months', '12')
    try:
        months_count = int(months)
    except (TypeError, ValueError):
        months_count = 12
    analytics = build_dashboard_analytics(period, months_count, today)
    context = {
        'categories': Category.objects.annotate(doc_count=Count('document')),
        'recent_docs': Document.objects.select_related('category').prefetch_related('tags')[:5],
        'expiring_soon': expiring_soon,
        'expiring_count': expiring_count,
        'expiring_label': _contract_word(expiring_count),
        'expiry_days': expiry_days,
        'expiring_filter_url': f"{reverse('document_list')}?{expiring_filter_qs}",
        'expired_count': expired,
        'period_choices': PERIOD_CHOICES,
        'analytics_json': analytics,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'documents/dashboard.html', context)


@login_required
def dashboard_analytics(request):
    period = request.GET.get('period', 'current_month')
    try:
        months_count = int(request.GET.get('months', 12))
    except (TypeError, ValueError):
        months_count = 12
    return JsonResponse(build_dashboard_analytics(period, months_count))


@login_required
def document_list(request):
    documents, filters = _documents_queryset(request)
    categories = Category.objects.all()
    all_tags = Tag.objects.all()
    paginator = Paginator(documents, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    active_filters = _active_filter_tags(filters, categories, all_tags)
    context = {
        'page_obj': page_obj,
        'documents': page_obj.object_list,
        'categories': categories,
        'all_tags': all_tags,
        'filters': filters,
        'active_filters': active_filters,
        'has_active_filters': bool(active_filters),
        'filters_querystring': _filters_querystring(filters),
        'status_labels': STATUS_LABELS,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'documents/document_list.html', context)


@login_required
def tag_autocomplete(request):
    query = request.GET.get('q', '').strip()
    tags = Tag.objects.all()
    if query:
        tags = tags.filter(name__icontains=query)
    tags = tags.order_by('name')[:15]
    return JsonResponse({'tags': [tag.name for tag in tags]})


@login_required
def document_pdf_preview(request, slug):
    document = get_object_or_404(Document, slug=slug)
    if not document.pdf_file:
        raise Http404('PDF файл не найден')
    document.pdf_file.open('rb')
    try:
        content = document.pdf_file.read()
    finally:
        document.pdf_file.close()
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{document.title}.pdf"'
    return response


@login_required
def document_detail(request, slug):
    document = get_object_or_404(
        Document.objects.select_related('category').prefetch_related(
            'tags', 'versions__uploaded_by', 'comments__user',
        ),
        slug=slug,
    )
    audit_logs = AuditLog.objects.filter(model_name='Document', object_id=document.pk)[:10]
    user_role = get_user_role(request.user)
    comments = [
        comment_to_dict(c, request.user, user_role)
        for c in document.comments.select_related('user')
    ]
    current_version = None
    if document.pdf_file:
        uploader = document.author or '—'
        latest_version = document.versions.first()
        if latest_version and latest_version.uploaded_by:
            uploader = latest_version.uploaded_by.get_full_name() or latest_version.uploaded_by.username
        current_version = {
            'number': document.current_version_number(),
            'uploaded_at': timezone.localtime(document.updated_at).strftime('%d.%m.%Y'),
            'uploaded_by': uploader,
            'file_size': format_file_size(document.current_pdf_size()),
            'url': document.pdf_file.url,
            'is_current': True,
        }
    return render(request, 'documents/document_detail.html', {
        'document': document,
        'audit_logs': audit_logs,
        'comments': comments,
        'comments_json': comments,
        'current_version': current_version,
        'user_role': user_role,
    })


@login_required
@role_required(UserProfile.ROLE_MANAGER, UserProfile.ROLE_ADMIN)
def document_create(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            document = form.save()
            messages.success(request, 'Документ успешно добавлен!')
            return redirect('document_detail', slug=document.slug)
    else:
        form = DocumentForm(user=request.user)
    return render(request, 'documents/document_form.html', {'form': form, 'title': 'Добавить документ'})


@login_required
@role_required(UserProfile.ROLE_MANAGER, UserProfile.ROLE_ADMIN)
def document_edit(request, slug):
    document = get_object_or_404(Document, slug=slug)
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, instance=document, user=request.user)
        if form.is_valid():
            document = form.save()
            messages.success(request, 'Документ обновлён!')
            return redirect('document_detail', slug=document.slug)
    else:
        form = DocumentForm(instance=document, user=request.user)
    return render(request, 'documents/document_form.html', {
        'form': form,
        'title': 'Редактировать',
        'has_pdf_file': bool(document.pdf_file),
    })


@login_required
@role_required(UserProfile.ROLE_ADMIN)
def document_delete(request, slug):
    document = get_object_or_404(Document, slug=slug)
    if request.method == 'POST':
        document._audit_user = request.user
        document.delete()
        messages.success(request, 'Документ удалён!')
        return redirect('document_list')
    return render(request, 'documents/document_confirm_delete.html', {'document': document})


@login_required
def document_export(request):
    documents, filters = _documents_queryset(request)
    export_format = request.GET.get('format', 'xlsx')
    export_date = timezone.localdate().strftime('%Y-%m-%d')

    if export_format == 'xlsx':
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Документы'
        sheet.append([
            'Название', 'Категория', 'Статус', 'Дата создания',
            'Дата истечения', 'Сумма (₸)', 'Контрагент',
        ])
        for doc in documents:
            sheet.append([
                doc.title,
                doc.category.name if doc.category else '',
                doc.get_status_display(),
                doc.created_at.strftime('%d.%m.%Y'),
                doc.end_date.strftime('%d.%m.%Y') if doc.end_date else '',
                float(doc.amount),
                doc.signatory,
            ])
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="documents_{export_date}.xlsx"'
        workbook.save(response)
        return response

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="documents_{export_date}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow([
        'Название', 'Категория', 'Статус', 'Дата создания',
        'Дата истечения', 'Сумма (₸)', 'Контрагент',
    ])
    for doc in documents:
        writer.writerow([
            doc.title,
            doc.category.name if doc.category else '',
            doc.get_status_display(),
            doc.created_at.strftime('%d.%m.%Y'),
            doc.end_date.strftime('%d.%m.%Y') if doc.end_date else '',
            doc.amount,
            doc.signatory,
        ])
    return response


@login_required
def category_list(request):
    categories = Category.objects.annotate(doc_count=Count('document'))
    return render(request, 'documents/category_list.html', {
        'categories': categories,
        'user_role': get_user_role(request.user),
    })


@login_required
@role_required(UserProfile.ROLE_ADMIN)
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        form.user = request.user
        if form.is_valid():
            form.save()
            messages.success(request, 'Категория создана!')
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'documents/category_form.html', {'form': form, 'title': 'Новая категория'})


@login_required
@role_required(UserProfile.ROLE_ADMIN)
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        form.user = request.user
        if form.is_valid():
            form.save()
            messages.success(request, 'Категория обновлена!')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'documents/category_form.html', {'form': form, 'title': 'Редактировать категорию'})


@login_required
@role_required(UserProfile.ROLE_ADMIN)
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category._audit_user = request.user
        category.delete()
        messages.success(request, 'Категория удалена!')
        return redirect('category_list')
    return render(request, 'documents/category_confirm_delete.html', {'category': category})


@login_required
@role_required(UserProfile.ROLE_ADMIN)
def audit_log_list(request):
    logs = AuditLog.objects.select_related('user')[:100]
    return render(request, 'documents/audit_log.html', {'logs': logs})


@login_required
def notification_settings(request):
    settings_obj = _get_notification_settings(request.user)
    if request.method == 'POST':
        form = NotificationSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки уведомлений сохранены.')
            return redirect('notification_settings')
    else:
        form = NotificationSettingsForm(instance=settings_obj)
    return render(request, 'documents/notification_settings.html', {
        'form': form,
        'user_role': get_user_role(request.user),
    })


def _build_invite_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return reverse('invite_set_password', kwargs={'uidb64': uid, 'token': token})


@login_required
@role_required(UserProfile.ROLE_ADMIN)
def user_list(request):
    users = User.objects.select_related('profile').order_by('-last_login', 'username')
    for user in users:
        UserProfile.objects.get_or_create(user=user)
    users = User.objects.select_related('profile').order_by('-last_login', 'username')
    invite_form = UserInviteForm()
    return render(request, 'documents/user_list.html', {
        'users': users,
        'invite_form': invite_form,
        'role_choices': UserProfile.ROLE_CHOICES,
        'user_role': get_user_role(request.user),
    })


@login_required
@role_required(UserProfile.ROLE_ADMIN)
@require_POST
def user_update_role(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        messages.error(request, 'Нельзя изменить собственную роль.')
        return redirect('user_list')
    form = UserRoleForm(request.POST)
    if form.is_valid():
        profile, _ = UserProfile.objects.get_or_create(user=target)
        profile.role = form.cleaned_data['role']
        profile.save()
        messages.success(request, f'Роль пользователя {target.username} обновлена.')
    else:
        messages.error(request, 'Некорректная роль.')
    return redirect('user_list')


@login_required
@role_required(UserProfile.ROLE_ADMIN)
@require_POST
def user_block(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        messages.error(request, 'Нельзя заблокировать себя.')
        return redirect('user_list')
    target.is_active = False
    target.save(update_fields=['is_active'])
    messages.success(request, f'Пользователь {target.username} заблокирован.')
    return redirect('user_list')


@login_required
@role_required(UserProfile.ROLE_ADMIN)
@require_POST
def user_delete(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        messages.error(request, 'Нельзя удалить себя.')
        return redirect('user_list')
    username = target.username
    target.delete()
    messages.success(request, f'Пользователь {username} удалён.')
    return redirect('user_list')


@login_required
@role_required(UserProfile.ROLE_ADMIN)
@require_POST
def user_invite(request):
    form = UserInviteForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Проверьте email и роль.')
        return redirect('user_list')

    email = form.cleaned_data['email']
    role = form.cleaned_data['role']
    username = email.split('@')[0]
    base_username = username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f'{base_username}{counter}'
        counter += 1

    user = User(username=username, email=email, is_active=True)
    user.set_unusable_password()
    user.save()
    UserProfile.objects.update_or_create(user=user, defaults={'role': role})
    UserNotificationSettings.objects.get_or_create(user=user, defaults={'notify_email': email})

    invite_path = _build_invite_url(user)
    invite_url = request.build_absolute_uri(invite_path)
    try:
        send_user_invite(email, invite_url)
        messages.success(request, f'Приглашение отправлено на {email}.')
    except Exception:
        messages.warning(
            request,
            f'Пользователь создан, но письмо не отправлено. Ссылка: {invite_url}',
        )
    return redirect('user_list')


def invite_set_password(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, 'documents/invite_invalid.html', status=400)

    if request.method == 'POST':
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        if len(password) < 8:
            messages.error(request, 'Пароль должен содержать минимум 8 символов.')
        elif password != password2:
            messages.error(request, 'Пароли не совпадают.')
        else:
            user.set_password(password)
            user.is_active = True
            user.save()
            messages.success(request, 'Пароль установлен. Теперь можно войти.')
            return redirect('login')

    return render(request, 'documents/invite_set_password.html', {'email': user.email})


@login_required
@require_POST
def document_comment_create(request, slug):
    document = get_object_or_404(Document, slug=slug)
    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'error': 'Введите текст комментария.'}, status=400)
    if len(text) > 2000:
        return JsonResponse({'error': 'Комментарий слишком длинный.'}, status=400)
    comment = DocumentComment.objects.create(document=document, user=request.user, text=text)
    return JsonResponse({
        'comment': comment_to_dict(comment, request.user),
        'count': document.comments.count(),
    })


@login_required
@require_POST
def document_comment_delete(request, slug, comment_id):
    document = get_object_or_404(Document, slug=slug)
    comment = get_object_or_404(DocumentComment, pk=comment_id, document=document)
    user_role = get_user_role(request.user)
    if user_role != UserProfile.ROLE_ADMIN and comment.user_id != request.user.id:
        return JsonResponse({'error': 'Недостаточно прав.'}, status=403)
    comment.delete()
    return JsonResponse({'count': document.comments.count()})


def permission_denied(request, exception=None):
    return render(request, '403.html', status=403)
