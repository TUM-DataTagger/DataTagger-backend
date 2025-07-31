from fdm.projects.models import ProjectMembership

__all__ = [
    "set_project_admin_permissions",
]


def set_project_admin_permissions(membership: ProjectMembership):
    membership.is_project_admin = True
    membership.can_create_folders = True
    membership.is_metadata_template_admin = True
