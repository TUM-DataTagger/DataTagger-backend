from django.contrib import admin

from adminsortable2.admin import SortableAdminMixin, SortableStackedInline

from fdm.faq.models import *

__all__ = [
    "FAQAdmin",
    "FAQCategoryAdmin",
]


@admin.register(FAQ)
class FAQAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = [
        "question",
        "category",
        "published",
        "order",
    ]

    list_filter = [
        "category",
        "published",
    ]

    search_fields = [
        "pk",
        "question",
        "slug",
        "answer",
        "category__pk",
        "category__name",
        "category__slug",
    ]

    prepopulated_fields = {
        "slug": ("question",),
    }


class FAQStackedInline(SortableStackedInline):
    model = FAQ

    prepopulated_fields = {
        "slug": ("question",),
    }


@admin.register(FAQCategory)
class FAQCategoryAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "published",
        "order",
    ]

    list_filter = [
        "published",
    ]

    search_fields = [
        "pk",
        "name",
        "slug",
    ]

    inlines = [
        FAQStackedInline,
    ]

    prepopulated_fields = {
        "slug": ("name",),
    }
