from .models import DocumentLink


def create_bidirectional_link(document, linked, link_type):
    if document.pk == linked.pk:
        return None, False

    created_any = False
    link, created = DocumentLink.objects.get_or_create(
        document=document,
        linked=linked,
        defaults={'link_type': link_type},
    )
    if created:
        created_any = True
    elif link.link_type != link_type:
        link.link_type = link_type
        link.save(update_fields=['link_type'])

    reverse, reverse_created = DocumentLink.objects.get_or_create(
        document=linked,
        linked=document,
        defaults={'link_type': link_type},
    )
    if reverse_created:
        created_any = True
    elif reverse.link_type != link_type:
        reverse.link_type = link_type
        reverse.save(update_fields=['link_type'])

    return link, created_any


def delete_bidirectional_link(document, linked):
    DocumentLink.objects.filter(document=document, linked=linked).delete()
    DocumentLink.objects.filter(document=linked, linked=document).delete()


def link_to_dict(link):
    return {
        'id': link.id,
        'link_type': link.link_type,
        'link_type_label': link.short_label(),
        'linked_title': link.linked.title,
        'linked_slug': link.linked.slug,
        'created_at': link.created_at.strftime('%d.%m.%Y'),
    }
