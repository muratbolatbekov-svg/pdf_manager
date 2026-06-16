from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view

from .analytics import build_dashboard_analytics
from .models import Category, Document, Tag, UserProfile
from .permissions import get_user_role


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

    def create(self, validated_data):
        user = self.context['request'].user
        document = Document(**validated_data)
        if not document.author:
            document.author = user.get_full_name() or user.username
        document._audit_user = user
        document.save()
        return document

    def update(self, instance, validated_data):
        user = self.context['request'].user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance._audit_user = user
        instance.save()
        return instance


class RolePermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        role = get_user_role(request.user)
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        if request.method == 'DELETE':
            return role == UserProfile.ROLE_ADMIN
        return role in (UserProfile.ROLE_MANAGER, UserProfile.ROLE_ADMIN)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter('category', int, description='ID категории'),
            OpenApiParameter('status', str, description='active | draft | archived'),
            OpenApiParameter('search', str, description='Поиск по названию, подписанту, автору'),
        ],
    ),
)
class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.select_related('category').prefetch_related('tags')
    serializer_class = DocumentSerializer
    permission_classes = [RolePermission]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        doc_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search', '').strip()

        if category:
            try:
                qs = qs.filter(category_id=int(category))
            except (TypeError, ValueError):
                pass
        if doc_status in ('active', 'draft', 'archived'):
            qs = qs.filter(status=doc_status)
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(signatory__icontains=search)
                | Q(author__icontains=search)
                | Q(description__icontains=search)
            )
        return qs

    @extend_schema(summary='Скачать PDF файл документа')
    @action(detail=True, methods=['get'], url_path='file')
    def file(self, request, pk=None):
        document = self.get_object()
        if not document.pdf_file:
            return Response({'detail': 'PDF файл не найден.'}, status=status.HTTP_404_NOT_FOUND)
        document.pdf_file.open('rb')
        try:
            content = document.pdf_file.read()
        finally:
            document.pdf_file.close()
        response = HttpResponse(content, content_type='application/pdf')
        filename = f'{document.title}.pdf'.replace('"', '')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [RolePermission]


class StatsSerializer(serializers.Serializer):
    period = serializers.CharField()
    documents = serializers.DictField()
    total_documents = serializers.IntegerField()
    active_documents = serializers.IntegerField()
    draft_documents = serializers.IntegerField()
    archived_documents = serializers.IntegerField()
    total_amount = serializers.FloatField()
    expired_active = serializers.IntegerField()
    trend = serializers.ListField()
    categories = serializers.ListField()


class StatsAPIView(APIView):
    permission_classes = [RolePermission]
    serializer_class = StatsSerializer

    @extend_schema(summary='Статистика для дашборда', responses=StatsSerializer)
    def get(self, request):
        today = timezone.localdate()
        period = build_dashboard_analytics('current_month', 12, today)
        totals = Document.objects.aggregate(total_amount=Sum('amount'))
        return Response({
            'period': period['period_label'],
            'documents': period['stats'],
            'total_documents': Document.objects.count(),
            'active_documents': Document.objects.filter(status='active').count(),
            'draft_documents': Document.objects.filter(status='draft').count(),
            'archived_documents': Document.objects.filter(status='archived').count(),
            'total_amount': float(totals['total_amount'] or 0),
            'expired_active': Document.objects.filter(end_date__lt=today, status='active').count(),
            'trend': period['trend'],
            'categories': period['categories'],
        })
