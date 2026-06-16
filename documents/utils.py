import re

from django.utils import timezone
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
    if isinstance(raw_tags, list):
        return [str(tag).strip() for tag in raw_tags if str(tag).strip()]
    parts = re.split(r'[,;]+', str(raw_tags).strip())
    return [tag.strip() for tag in parts if tag.strip()]


def sync_document_tags(document, raw_tags):
    from .models import Tag

    names = parse_tags(raw_tags)
    tag_objects = []
    seen = set()
    for name in names:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        tag, _ = Tag.objects.get_or_create(name=name)
        tag_objects.append(tag)
    document.tags.set(tag_objects)


def format_file_size(size):
    if size is None:
        return '—'
    if size < 1024:
        return f'{size} B'
    if size < 1024 * 1024:
        return f'{round(size / 1024)} KB'
    return f'{round(size / (1024 * 1024), 1)} MB'


def user_initials(user):
    name = user.get_full_name().strip()
    if name:
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return parts[0][:2].upper()
    return user.username[:2].upper()


AVATAR_COLORS = ['#0071e3', '#34c759', '#ff9500', '#5856d6', '#ff3b30', '#af52de', '#5ac8fa', '#ff2d55']


def avatar_color(user):
    idx = sum(ord(c) for c in user.username) % len(AVATAR_COLORS)
    return AVATAR_COLORS[idx]


def comment_to_dict(comment, current_user, user_role=None):
    from .permissions import get_user_role
    from .models import UserProfile

    role = user_role if user_role is not None else get_user_role(current_user)
    can_delete = role == UserProfile.ROLE_ADMIN or comment.user_id == current_user.id
    local_dt = timezone.localtime(comment.created_at)
    return {
        'id': comment.id,
        'text': comment.text,
        'author_name': comment.user.get_full_name().strip() or comment.user.username,
        'initials': user_initials(comment.user),
        'avatar_color': avatar_color(comment.user),
        'created_at': local_dt.strftime('%d.%m.%Y %H:%M'),
        'can_delete': can_delete,
    }


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
        for resource_type in ('raw', 'image', 'video'):
            response = cloudinary.uploader.destroy(
                public_id,
                resource_type=resource_type,
                invalidate=True,
            )
            if response.get('result') == 'ok':
                return
    except Exception:
        pass
