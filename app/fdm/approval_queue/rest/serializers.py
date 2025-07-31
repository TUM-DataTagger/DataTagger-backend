from fdm.approval_queue.models import *
from fdm.core.rest.serializers import BaseModelWithByUserSerializer, ContentObjectSerializer

__all__ = [
    "ApprovalQueueSerializer",
]


class ApprovalQueueSerializer(BaseModelWithByUserSerializer):
    content_object = ContentObjectSerializer()

    class Meta:
        model = ApprovalQueue
        fields = [
            "pk",
            "content_type",
            "object_id",
            "content_object",
            "approved_by",
            "approved_at",
        ]
