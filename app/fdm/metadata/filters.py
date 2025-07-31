from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _

__all__ = [
    "IsPublishedFilter",
]


class IsPublishedFilter(SimpleListFilter):
    title = "is published"

    parameter_name = "is_published"

    def lookups(self, request, model_admin):
        return (
            ("1", _("Yes")),
            ("0", _("No")),
        )

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(publication_date__isnull=False)
        elif self.value() == "0":
            return queryset.filter(publication_date__isnull=True)

        return queryset
