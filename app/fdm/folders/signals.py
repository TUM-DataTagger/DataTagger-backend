from django.dispatch import Signal

__all__ = [
    "folder_datasets_count_updated",
]

"""
Signal arguments: instance
"""
folder_datasets_count_updated = Signal()
