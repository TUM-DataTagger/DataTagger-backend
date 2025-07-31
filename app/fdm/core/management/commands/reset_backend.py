from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from fdm.core.rest.views import ResetBackendView


class Command(BaseCommand):
    help = _("Resets the backend by truncating specific tables and cleaning media folders")

    def handle(self, *args, **options):
        # Ensure DEBUG mode is active
        if not settings.DEBUG:
            print(_("This command can only be run in DEBUG mode. Exiting."))
            return

        # Create a ResetBackendView instance
        view = ResetBackendView()

        try:
            # Call the `create` method directly without a request object
            response = view.create(request=None)

            # Check response status and act accordingly
            if response.status_code >= 400:
                print(_("Error: {error}").format(error=response.data.get("error", _("An error occurred"))))
            else:
                results = response.data.get("results", {})

                # Print table truncation results
                print(_("Backend Reset Results:"))
                for table, data in results.items():
                    if table == "media":
                        print(
                            _("Media: Deleted {folders} folders and {files} files.").format(
                                folders=data["deleted_folder_count"],
                                files=data["deleted_file_count"],
                            ),
                        )
                    else:
                        if "error" in data:
                            print(
                                _("Table: {table} - Error: {error}").format(
                                    table=table,
                                    error=data["error"],
                                ),
                            )
                        else:
                            print(
                                _("Table: {table} - Deleted rows: {count}").format(
                                    table=table,
                                    count=data["deleted_count"],
                                ),
                            )

                print(_("Reset successfully completed."))

        except Exception as e:
            print(_("An error occurred: {error}").format(error=str(e)))
