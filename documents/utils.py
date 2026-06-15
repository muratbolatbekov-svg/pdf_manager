import re

from django.utils.text import slugify


def generate_unique_slug(title, instance=None):
    from .models import Document

    base_slug = slugify(title, allow_unicode=True) or 'document'
    slug = base_slug
    counter = 2
    queryset = Document.objects.all()
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    while queryset.filter(slug=slug).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1
    return slug


def parse_tags(raw_tags):
    if not raw_tags:
        return []
    parts = re.split(r'[,;\s]+', raw_tags.strip())
    return [tag.strip() for tag in parts if tag.strip()]


def sync_document_tags(document, raw_tags):
    from .models import Tag

    names = parse_tags(raw_tags)
    tag_objects = []
    for name in names:
        tag, _ = Tag.objects.get_or_create(name=name)
        tag_objects.append(tag)
    document.tags.set(tag_objects)


def extract_pdf_text(uploaded_file):
    from pypdf import PdfReader

    uploaded_file.seek(0)
    try:
        reader = PdfReader(uploaded_file)
        pages = [page.extract_text() or '' for page in reader.pages]
        return '\n'.join(pages).strip()
    except Exception:
        return ''
    finally:
        uploaded_file.seek(0)


def delete_cloudinary_file(field_file):
    if not field_file or not field_file.name:
        return
    try:
        import cloudinary.uploader

        public_id = getattr(field_file, 'public_id', None) or field_file.name.rsplit('.', 1)[0]
        cloudinary.uploader.destroy(public_id, resource_type='raw', invalidate=True)
    except Exception:
        pass
