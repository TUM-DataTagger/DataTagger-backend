from rest_framework import serializers

from fdm.core.rest.base import BaseModelSerializer
from fdm.faq.models import *

__all__ = [
    "FilterPublishedFAQListSerializer",
    "PublishedFAQListSerializer",
    "FAQCategoryMinimalSerializer",
    "FAQMinimalSerializer",
    "FAQCategorySerializer",
    "FAQSerializer",
]


class FilterPublishedFAQListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        data = data.exclude(
            published=False,
        ).order_by(
            "order",
        )
        return super().to_representation(data)


class PublishedFAQListSerializer(BaseModelSerializer):
    class Meta:
        model = FAQ
        list_serializer_class = FilterPublishedFAQListSerializer
        fields = [
            "pk",
            "question",
            "slug",
            "answer",
            "order",
        ]


class FAQCategoryMinimalSerializer(BaseModelSerializer):
    class Meta:
        model = FAQCategory
        fields = [
            "pk",
            "name",
            "slug",
        ]


class FAQMinimalSerializer(BaseModelSerializer):
    class Meta:
        model = FAQ
        fields = [
            "pk",
            "question",
            "slug",
            "answer",
            "order",
        ]


class FAQCategorySerializer(BaseModelSerializer):
    faq = PublishedFAQListSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = FAQCategory
        fields = [
            "pk",
            "name",
            "slug",
            "faq",
            "order",
        ]


class FAQSerializer(BaseModelSerializer):
    category = FAQCategoryMinimalSerializer(
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = FAQ
        fields = [
            "pk",
            "question",
            "slug",
            "answer",
            "category",
            "order",
        ]
