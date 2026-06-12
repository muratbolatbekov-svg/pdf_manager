from django import forms
from .models import Document, Category

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'description', 'category', 'pdf_file', 'amount', 'initiator', 'author', 'tags', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название документа'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'pdf_file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'initiator': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО инициатора'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО автора'}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'тег1, тег2, тег3'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
