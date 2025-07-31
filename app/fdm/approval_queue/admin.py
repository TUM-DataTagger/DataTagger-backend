from django.conf import settings
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import ApprovalQueue


@admin.register(ApprovalQueue)
class ApprovalQueueAdmin(admin.ModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False

    list_display = (
        "content_object",
        "content_type",
        "approved_by",
        "approved_at",
    )

    list_filter = [
        "approved_at",
        "creation_date",
        "last_modification_date",
    ]

    readonly_fields = (
        "content_type",
        "object_id",
        "content_object",
        "storage_type",
        "local_private_dss_path",
        "link_to_object",
        "approved_by",
        "approved_at",
        "created_by",
        "creation_date",
        "last_modified_by",
        "last_modification_date",
    )

    ordering = ["-creation_date"]

    def content_object(self, obj):
        return str(obj.content_object)

    content_object.short_description = "Object"

    def storage_type(self, obj):
        """
        Display the storage_type from the related content_object (e.g. DynamicStorage).
        """
        try:
            return obj.content_object.storage_type
        except AttributeError:
            return "N/A"

    storage_type.short_description = "Storage Type"

    def local_private_dss_path(self, obj):
        """
        Display the local_private_dss_path from the related content_object (e.g. DynamicStorage).
        """
        try:
            return obj.content_object.local_private_dss_path_encrypted.decrypt(settings.SECRET_KEY)
        except AttributeError:
            return "N/A"

    local_private_dss_path.short_description = "Local Private DSS Path"

    def link_to_object(self, obj):
        """
        Generate a link to the related object's admin detail page.
        """
        try:
            # Use the `url` helper to generate the link dynamically
            admin_url = reverse(
                f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change",
                args=[obj.object_id],
            )
            return format_html('<a href="{}">View Object</a>', admin_url)  # Safe HTML rendering
        except AttributeError:
            return "N/A"

    link_to_object.short_description = "Link to Object"

    def approve_selected(self, request, queryset):
        ct_id = request.GET.get("ct_id")
        for obj in queryset:
            content_object = obj.content_object
            content_object.approved = True
            content_object.save()
            obj.approved_by = request.user
            obj.approved_at = timezone.now()
            obj.save()
        self.message_user(request, "Selected items approved successfully.")

        changelist_url = reverse("admin:approval_queue_approvalqueue_changelist")
        if ct_id:
            changelist_url += f"?content_type__id__exact={ct_id}"

        return HttpResponseRedirect(changelist_url)

    approve_selected.short_description = "Approve selected items"
    actions = ["approve_selected"]

    def response_change(self, request, obj):
        if "_approve" in request.POST:
            content_object = obj.content_object
            content_object.approved = True  # Make sure the `approved` field exists
            content_object.save()

            obj.approved_by = request.user
            obj.approved_at = timezone.now()
            obj.save()

            # Confirmation message to user
            self.message_user(request, "Item approved successfully.")

            # Redirect after approval
            return HttpResponseRedirect(reverse("admin:approval_queue_approvalqueue_changelist"))

        return super().response_change(request, obj)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}

        # Fetch the ApprovalQueue object
        approval_queue_obj = self.get_object(request, object_id)
        if not approval_queue_obj.approved_at:
            # Pass this variable to the template to conditionally render the button
            extra_context["has_approve_permission"] = True

        # Call the parent class method and pass the extra context
        return super().change_view(request, object_id, form_url, extra_context=extra_context)
