import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from openpyxl import Workbook

from .forms import CategoryForm, DocumentForm
from .models import AuditLog, Category, Document, UserProfile
from .permissions import get_user_role, role_required


SORT_OPTIONS = {
    'date_desc': '-created_at',
    'date_asc': 'created_at',
    'amount_desc': '-amount',
    'amount_asc': 'amount',
    'title_asc': 'title',
    'title_desc': '-title',
}


def _documents_queryset(request):
    documents = Document.objects.select_related('category').prefetch_related('tags')
    query = request.GET.get('q', '').strip()
    category_id_str = request.GET.get('category', '').strip()
    status = request.GET.get('status', '').strip()
    sort = request.GET.get('sort', 'date_desc')

    selected_category = None
    if category_id_str:
        try:
            selected_category = int(category_id_str)
            documents = documents.filter(category_id=selected_category)
        except ValueError:
            pass

    if status:
        documents = documents.filter(status=status)

    if query:
        documents = documents.filter(
            Q(title__icontains=query)
            | Q(initiator__icontains=query)
            | Q(author__icontains=query)
            | Q(pdf_text__icontains=query)
            | Q(tags__name__icontains=query)
        ).distinct()

    order = SORT_OPTIONS.get(sort, '-created_at')
    return documents.order_by(order), query, selected_category, status, sort


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
    expiring_soon = Document.objects.filter(
        end_date__gte=today,
        end_date__lte=today + timezone.timedelta(days=30),
        status='active',
    ).select_related('category')[:10]
    expired = Document.objects.filter(end_date__lt=today, status='active').count()
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
        'expired_count': expired,
        'amount_by_category': amount_by_category,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'documents/dashboard.html', context)


@login_required
def document_list(request):
    documents, query, selected_category, selected_status, sort = _documents_queryset(request)
    paginator = Paginator(documents, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'page_obj': page_obj,
        'documents': page_obj.object_list,
        'categories': Category.objects.all(),
        'query': query,
        'selected_category': selected_category,
        'selected_status': selected_status,
        'sort': sort,
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
    documents, query, selected_category, selected_status, sort = _documents_queryset(request)
    export_format = request.GET.get('format', 'csv')

    if export_format == 'xlsx':
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Документы'
        sheet.append(['Название', 'Категория', 'Инициатор', 'Автор', 'Сумма', 'Статус', 'Начало', 'Окончание', 'Теги', 'Создан'])
        for doc in documents:
            sheet.append([
                doc.title,
                doc.category.name if doc.category else '',
                doc.initiator,
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
    writer.writerow(['Название', 'Категория', 'Инициатор', 'Автор', 'Сумма', 'Статус', 'Начало', 'Окончание', 'Теги', 'Создан'])
    for doc in documents:
        writer.writerow([
            doc.title,
            doc.category.name if doc.category else '',
            doc.initiator,
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
