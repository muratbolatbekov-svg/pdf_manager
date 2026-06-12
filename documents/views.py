from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from .models import Document, Category
from .forms import DocumentForm, CategoryForm

def dashboard(request):
    total_docs = Document.objects.count()
    active_docs = Document.objects.filter(status='active').count()
    archived_docs = Document.objects.filter(status='archived').count()
    categories = Category.objects.annotate(doc_count=Count('document'))
    recent_docs = Document.objects.select_related('category')[:5]
    context = {
        'total_docs': total_docs,
        'active_docs': active_docs,
        'archived_docs': archived_docs,
        'categories': categories,
        'recent_docs': recent_docs,
    }
    return render(request, 'documents/dashboard.html', context)

def document_list(request):
    documents = Document.objects.select_related('category')
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', '')
    if query:
        documents = documents.filter(Q(title__icontains=query) | Q(author__icontains=query) | Q(tags__icontains=query))
    if category_id:
        documents = documents.filter(category_id=category_id)
    if status:
        documents = documents.filter(status=status)
    categories = Category.objects.all()
    context = {'documents': documents, 'categories': categories, 'query': query, 'selected_category': category_id, 'selected_status': status}
    return render(request, 'documents/document_list.html', context)

def document_detail(request, pk):
    document = get_object_or_404(Document, pk=pk)
    return render(request, 'documents/document_detail.html', {'document': document})

def document_create(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Документ успешно добавлен!')
            return redirect('document_list')
    else:
        form = DocumentForm()
    return render(request, 'documents/document_form.html', {'form': form, 'title': 'Добавить документ'})

def document_edit(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if request.method == 'POST':
        form = DocumentForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, 'Документ обновлён!')
            return redirect('document_detail', pk=pk)
    else:
        form = DocumentForm(instance=document)
    return render(request, 'documents/document_form.html', {'form': form, 'title': 'Редактировать'})

def document_delete(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if request.method == 'POST':
        document.delete()
        messages.success(request, 'Документ удалён!')
        return redirect('document_list')
    return render(request, 'documents/document_confirm_delete.html', {'document': document})

def category_list(request):
    categories = Category.objects.annotate(doc_count=Count('document'))
    return render(request, 'documents/category_list.html', {'categories': categories})

def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Категория создана!')
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'documents/category_form.html', {'form': form})
