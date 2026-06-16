from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Category, Document, Tag
from .permissions import get_user_role
from .models import UserProfile


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at']


class DocumentSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amount_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'slug', 'description', 'category', 'category_name',
            'pdf_file', 'amount', 'amount_formatted', 'signatory', 'author',
            'tags', 'status', 'status_display', 'start_date', 'end_date',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']

    def get_amount_formatted(self, obj):
        return obj.amount_formatted()


class RolePermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        role = get_user_role(request.user)
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        if request.method == 'DELETE':
            return role == UserProfile.ROLE_ADMIN
        return role in (UserProfile.ROLE_EDITOR, UserProfile.ROLE_ADMIN)


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.select_related('category').prefetch_related('tags')
    serializer_class = DocumentSerializer
    permission_classes = [RolePermission]
    lookup_field = 'slug'


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [RolePermission]

    def destroy(self, request, *args, **kwargs):
        role = get_user_role(request.user)
        if role != UserProfile.ROLE_ADMIN:
            from rest_framework.response import Response
            from rest_framework import status
            return Response({'detail': 'Недостаточно прав.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
