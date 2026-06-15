from django import forms
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from django.conf import settings

from .models import Category, Document, DocumentVersion, Tag
from .utils import extract_pdf_text, parse_tags, sync_document_tags


class DocumentForm(forms.ModelForm):
    pdf_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
    )
    tags_input = forms.CharField(
        required=False,
        label='Теги',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'тег1, тег2, тег3'}),
    )

    class Meta:
        model = Document
        fields = [
            'title', 'description', 'category', 'pdf_file', 'amount', 'initiator',
            'author', 'status', 'start_date', 'end_date',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название документа'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'initiator': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО инициатора'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО автора'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['tags_input'].initial = ', '.join(self.instance.tags.values_list('name', flat=True))
        elif self.user:
            display_name = self.user.get_full_name() or self.user.username
            self.fields['author'].initial = display_name

    def _file_size(self, uploaded_file):
        size = getattr(uploaded_file, 'size', None)
        if size is not None:
            return size
        if hasattr(uploaded_file, 'seek') and hasattr(uploaded_file, 'tell'):
            try:
                uploaded_file.seek(0, 2)
                size = uploaded_file.tell()
                uploaded_file.seek(0)
                return size
            except (OSError, TypeError, ValueError):
                return None
        return None

    def clean_pdf_file(self):
        pdf = self.cleaned_data.get('pdf_file')
        if not pdf:
            return pdf

        if getattr(self.instance, 'pdf_file', None) and pdf == self.instance.pdf_file:
            return pdf

        max_size = getattr(settings, 'PDF_MAX_SIZE', 10 * 1024 * 1024)
        file_size = self._file_size(pdf)
        if file_size is not None and file_size > max_size:
            raise ValidationError(f'Размер файла не должен превышать {max_size // (1024 * 1024)} МБ')

        content_type = getattr(pdf, 'content_type', None)
        if content_type and content_type not in ('application/pdf', 'application/x-pdf'):
            raise ValidationError('Файл должен быть в формате PDF')

        name = getattr(pdf, 'name', '') or ''
        if not name.lower().endswith('.pdf'):
            raise ValidationError('Файл должен быть в формате PDF')

        return pdf

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise ValidationError('Дата окончания не может быть раньше даты начала.')
        return cleaned_data

    def _archive_previous_pdf(self, instance):
        if not instance.pk:
            return
        old = Document.objects.filter(pk=instance.pk).first()
        if not old or not old.pdf_file or not self.cleaned_data.get('pdf_file'):
            return
        version_number = old.versions.count() + 1
        old.pdf_file.open()
        content = old.pdf_file.read()
        old.pdf_file.close()
        version = DocumentVersion(
            document=old,
            version_number=version_number,
            uploaded_by=self.user,
        )
        version.pdf_file.save(old.pdf_file.name, ContentFile(content), save=False)
        version.save()

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.author and self.user:
            instance.author = self.user.get_full_name() or self.user.username

        if commit:
            self._archive_previous_pdf(instance)
            instance._uploaded_by = self.user
            instance._audit_user = self.user
            instance.save()
            sync_document_tags(instance, self.cleaned_data.get('tags_input', ''))

            pdf = self.cleaned_data.get('pdf_file')
            if pdf:
                pdf.seek(0)
                pdf_text = extract_pdf_text(pdf)
                if pdf_text:
                    Document.objects.filter(pk=instance.pk).update(pdf_text=pdf_text)

        return instance


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance._audit_user = getattr(self, 'user', None)
            instance.save()
        return instance
