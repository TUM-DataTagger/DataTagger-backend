import django.db.models.deletion
from django.db import migrations, models

import fdm.folders.models.models


class Migration(migrations.Migration):
    dependencies = [
        ("storages", "0005_create_default_dynamic_storage"),
        ("folders", "0021_alter_folder_metadata_template"),
    ]

    operations = [
        migrations.AlterField(
            model_name="folder",
            name="storage",
            field=models.ForeignKey(
                blank=True,
                default=fdm.folders.models.models.get_default_folder_storage,
                null=True,
                on_delete=django.db.models.deletion.SET_DEFAULT,
                related_name="folder",
                to="storages.dynamicstorage",
            ),
        ),
    ]
