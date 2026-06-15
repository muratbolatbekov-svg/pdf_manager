from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.conf import settings
from .models import Document, Category

class DocumentForm(forms.ModelForm):
    pdf_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'})
    )

    class Meta:
        model = Document
        fields = ['title', 'description', 'category', 'pdf_file', 'amount', 'initiator', 'author', 'tags', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название документа'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'initiator': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО инициатора'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО автора'}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'тег1, тег2, тег3'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_pdf_file(self):
        pdf = self.cleaned_data.get('pdf_file')
        if not pdf:
            return pdf
        
        max_size = getattr(settings, 'PDF_MAX_SIZE', 10 * 1024 * 1024)
        if pdf.size > max_size:
            raise ValidationError(f'Размер файла не должен превышать {max_size // (1024*1024)} МБ')
        
        if pdf.content_type != 'application/pdf':
            raise ValidationError('Файл должен быть в формате PDF')
        
        return pdf

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
