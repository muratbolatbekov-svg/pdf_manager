import csv
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from openpyxl import Workbook

from .forms import CategoryForm, DocumentForm, NotificationSettingsForm
from .models import AuditLog, Category, Document, UserNotificationSettings, UserProfile
from .notifications import expiring_documents_queryset
from .permissions import get_user_role, role_required


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

    return {
        'category': selected_category,
        'status': status,
        'sort': sort,
        'date_from': date_from,
        'date_to': date_to,
        'amount_min': amount_min,
        'amount_max': amount_max,
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
    if filters['sort'] != 'date_desc' and 'sort' not in exclude:
        params['sort'] = filters['sort']
    if page:
        params['page'] = page
    return urlencode(params)


def _active_filter_tags(filters, categories):
    tags = []
    if filters['category']:
        category = categories.filter(pk=filters['category']).first()
        if category:
            tags.append({'param': 'category', 'label': category.name})
    if filters['status']:
        tags.append({'param': 'status', 'label': STATUS_LABELS[filters['status']]})
    if filters['date_from']:
        tags.append({'param': 'date_from', 'label': f'от {filters["date_from"].strftime("%d.%m.%Y")}'})
    if filters['date_to']:
        tags.append({'param': 'date_to', 'label': f'до {filters["date_to"].strftime("%d.%m.%Y")}'})
    if filters['amount_min'] is not None:
        tags.append({'param': 'amount_min', 'label': f'сумма от {filters["amount_min"]:,.0f} ₸'.replace(',', ' ')})
    if filters['amount_max'] is not None:
        tags.append({'param': 'amount_max', 'label': f'сумма до {filters["amount_max"]:,.0f} ₸'.replace(',', ' ')})
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
    amount_by_category = (
        Category.objects.annotate(total_amount=Sum('document__amount'))
        .filter(total_amount__gt=0)
        .order_by('-total_amount')[:5]
    )
    context = {
        **_document_stats(),
        'total_amount': Document.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0'),
        'categories': Category.objects.annotate(doc_count=Count('document')),
        'recent_docs': Document.objects.select_related('category').prefetch_related('tags')[:5],
        'expiring_soon': expiring_soon,
        'expiring_count': expiring_count,
        'expiring_label': _contract_word(expiring_count),
        'expiry_days': expiry_days,
        'expiring_filter_url': f"{reverse('document_list')}?{expiring_filter_qs}",
        'expired_count': expired,
        'amount_by_category': amount_by_category,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'documents/dashboard.html', context)


@login_required
def document_list(request):
    documents, filters = _documents_queryset(request)
    categories = Category.objects.all()
    paginator = Paginator(documents, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    active_filters = _active_filter_tags(filters, categories)
    context = {
        'page_obj': page_obj,
        'documents': page_obj.object_list,
        'categories': categories,
        'filters': filters,
        'active_filters': active_filters,
        'has_active_filters': bool(active_filters),
        'filters_querystring': _filters_querystring(filters),
        'status_labels': STATUS_LABELS,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'documents/document_list.html', context)


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
        Document.objects.select_related('category').prefetch_related('tags', 'versions'),
        slug=slug,
    )
    audit_logs = AuditLog.objects.filter(model_name='Document', object_id=document.pk)[:10]
    return render(request, 'documents/document_detail.html', {
        'document': document,
        'audit_logs': audit_logs,
        'user_role': get_user_role(request.user),
    })


@login_required
@role_required(UserProfile.ROLE_EDITOR, UserProfile.ROLE_ADMIN)
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
@role_required(UserProfile.ROLE_EDITOR, UserProfile.ROLE_ADMIN)
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
    return render(request, 'documents/document_form.html', {'form': form, 'title': 'Редактировать'})


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
@role_required(UserProfile.ROLE_ADMIN)
def document_export(request):
    documents, filters = _documents_queryset(request)
    export_format = request.GET.get('format', 'csv')

    if export_format == 'xlsx':
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Документы'
        sheet.append(['Название', 'Категория', 'Подписант', 'Автор', 'Сумма', 'Статус', 'Начало', 'Окончание', 'Теги', 'Создан'])
        for doc in documents:
            sheet.append([
                doc.title,
                doc.category.name if doc.category else '',
                doc.signatory,
                doc.author,
                float(doc.amount),
                doc.get_status_display(),
                doc.start_date.isoformat() if doc.start_date else '',
                doc.end_date.isoformat() if doc.end_date else '',
                doc.tag_names(),
                doc.created_at.strftime('%d.%m.%Y'),
            ])
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="documents.xlsx"'
        workbook.save(response)
        return response

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="documents.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['Название', 'Категория', 'Подписант', 'Автор', 'Сумма', 'Статус', 'Начало', 'Окончание', 'Теги', 'Создан'])
    for doc in documents:
        writer.writerow([
            doc.title,
            doc.category.name if doc.category else '',
            doc.signatory,
            doc.author,
            doc.amount,
            doc.get_status_display(),
            doc.start_date or '',
            doc.end_date or '',
            doc.tag_names(),
            doc.created_at.strftime('%d.%m.%Y'),
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
