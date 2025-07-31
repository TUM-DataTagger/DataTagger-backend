from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

import pytest

from fdm.core.helpers import get_content_type_for_object, set_request_for_user
from fdm.metadata.enums import MetadataFieldType
from fdm.metadata.helpers import (
    check_metadata_template_permissions_for_object,
    create_metadata_template_for_object,
    set_metadata,
)
from fdm.metadata.models import Metadata, MetadataField, MetadataTemplate, MetadataTemplateField
from fdm.projects.models import Project


@pytest.mark.django_db
class TestMetadataModel:
    def test_field_type_fallback(self):
        """
        Ensure we get the correct field type on the metadata itself if a field is linked to it.
        """
        metadata_field_1 = MetadataField.objects.create(
            key="metadata_field_1",
            field_type=MetadataFieldType.INTEGER,
        )

        metadata_1 = set_metadata(
            field=metadata_field_1,
            value=1,
        )
        assert metadata_1.field_type == MetadataFieldType.INTEGER


@pytest.mark.django_db
class TestMetadataFieldModel:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.metadata_field_1 = MetadataField.objects.create(
            key="metadata_field_1",
            field_type=MetadataFieldType.TEXT,
            read_only=False,
        )

    def test_string_representation(self):
        """
        Ensure we get the correct string representation of a metadata field.
        """
        assert str(self.metadata_field_1) == f"{self.metadata_field_1.key} ({self.metadata_field_1.field_type})"

    def test_validate_integer(self):
        """
        Ensure we get a correct validation of an integer value.
        """
        assert Metadata.objects.count() == 0

        set_metadata(
            custom_key="integer_1",
            field_type=MetadataFieldType.INTEGER,
            value=0,
        )
        assert Metadata.objects.count() == 1
        assert Metadata.objects.latest("creation_date").get_value() == "0"

        set_metadata(
            custom_key="integer_2",
            field_type=MetadataFieldType.INTEGER,
            value=1337,
        )
        assert Metadata.objects.count() == 2
        assert Metadata.objects.latest("creation_date").get_value() == "1337"

        set_metadata(
            custom_key="integer_3",
            field_type=MetadataFieldType.INTEGER,
            value=-7331,
        )
        assert Metadata.objects.count() == 3
        assert Metadata.objects.latest("creation_date").get_value() == "-7331"

        set_metadata(
            custom_key="integer_4",
            field_type=MetadataFieldType.INTEGER,
            value="0",
        )
        assert Metadata.objects.count() == 4
        assert Metadata.objects.latest("creation_date").get_value() == "0"

        set_metadata(
            custom_key="integer_5",
            field_type=MetadataFieldType.INTEGER,
            value="1337",
        )
        assert Metadata.objects.count() == 5
        assert Metadata.objects.latest("creation_date").get_value() == "1337"

        set_metadata(
            custom_key="integer_6",
            field_type=MetadataFieldType.INTEGER,
            value="-7331",
        )
        assert Metadata.objects.count() == 6
        assert Metadata.objects.latest("creation_date").get_value() == "-7331"

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="integer_7",
                field_type=MetadataFieldType.INTEGER,
                value="Text",
            )
        assert Metadata.objects.count() == 6

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="integer_8",
                field_type=MetadataFieldType.INTEGER,
                value=13.37,
            )
        assert Metadata.objects.count() == 6

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="integer_9",
                field_type=MetadataFieldType.INTEGER,
                value="13.37",
            )
        assert Metadata.objects.count() == 6

        set_metadata(
            custom_key="integer_10",
            field_type=MetadataFieldType.INTEGER,
            value=None,
        )
        assert Metadata.objects.count() == 7

        set_metadata(
            custom_key="integer_11",
            field_type=MetadataFieldType.INTEGER,
            value="",
        )
        assert Metadata.objects.count() == 8

    def test_validate_decimal(self):
        """
        Ensure we get a correct validation of a decimal numeral value.
        """
        assert Metadata.objects.count() == 0

        set_metadata(
            custom_key="decimal_1",
            field_type=MetadataFieldType.DECIMAL,
            value=0,
        )
        assert Metadata.objects.count() == 1
        assert Metadata.objects.latest("creation_date").get_value() == "0"

        set_metadata(
            custom_key="decimal_2",
            field_type=MetadataFieldType.DECIMAL,
            value=1337,
        )
        assert Metadata.objects.count() == 2
        assert Metadata.objects.latest("creation_date").get_value() == "1337"

        set_metadata(
            custom_key="decimal_3",
            field_type=MetadataFieldType.DECIMAL,
            value=-7331,
        )
        assert Metadata.objects.count() == 3
        assert Metadata.objects.latest("creation_date").get_value() == "-7331"

        set_metadata(
            custom_key="decimal_4",
            field_type=MetadataFieldType.DECIMAL,
            value=0.0,
        )
        assert Metadata.objects.count() == 4
        assert Metadata.objects.latest("creation_date").get_value() == "0.0"

        set_metadata(
            custom_key="decimal_5",
            field_type=MetadataFieldType.DECIMAL,
            value=13.37,
        )
        assert Metadata.objects.count() == 5
        assert Metadata.objects.latest("creation_date").get_value() == "13.37"

        set_metadata(
            custom_key="decimal_6",
            field_type=MetadataFieldType.DECIMAL,
            value="0",
        )
        assert Metadata.objects.count() == 6
        assert Metadata.objects.latest("creation_date").get_value() == "0"

        set_metadata(
            custom_key="decimal_7",
            field_type=MetadataFieldType.DECIMAL,
            value="1337",
        )
        assert Metadata.objects.count() == 7
        assert Metadata.objects.latest("creation_date").get_value() == "1337"

        set_metadata(
            custom_key="decimal_8",
            field_type=MetadataFieldType.DECIMAL,
            value="-7331",
        )
        assert Metadata.objects.count() == 8
        assert Metadata.objects.latest("creation_date").get_value() == "-7331"

        set_metadata(
            custom_key="decimal_9",
            field_type=MetadataFieldType.DECIMAL,
            value="0.0",
        )
        assert Metadata.objects.count() == 9
        assert Metadata.objects.latest("creation_date").get_value() == "0.0"

        set_metadata(
            custom_key="decimal_10",
            field_type=MetadataFieldType.DECIMAL,
            value="13.37",
        )
        assert Metadata.objects.count() == 10
        assert Metadata.objects.latest("creation_date").get_value() == "13.37"

        set_metadata(
            custom_key="decimal_11",
            field_type=MetadataFieldType.DECIMAL,
            value="1e10",
        )
        assert Metadata.objects.count() == 11
        assert Metadata.objects.latest("creation_date").get_value() == "1e10"

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="decimal_12",
                field_type=MetadataFieldType.DECIMAL,
                value="Text",
            )
        assert Metadata.objects.count() == 11

        set_metadata(
            custom_key="decimal_13",
            field_type=MetadataFieldType.DECIMAL,
            value=None,
        )
        assert Metadata.objects.count() == 12

        set_metadata(
            custom_key="decimal_14",
            field_type=MetadataFieldType.DECIMAL,
            value="",
        )
        assert Metadata.objects.count() == 13

    def test_validate_datetime(self):
        """
        Ensure we get a correct validation of a datetime value.
        """
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_1",
                field_type=MetadataFieldType.DATETIME,
                value=1337,
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_2",
                field_type=MetadataFieldType.DATETIME,
                value=13.37,
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_3",
                field_type=MetadataFieldType.DATETIME,
                value="18-02-2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_4",
                field_type=MetadataFieldType.DATETIME,
                value="02-18-2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_5",
                field_type=MetadataFieldType.DATETIME,
                value="18.02.2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_6",
                field_type=MetadataFieldType.DATETIME,
                value="02.18.2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_7",
                field_type=MetadataFieldType.DATETIME,
                value="18/02/2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_8",
                field_type=MetadataFieldType.DATETIME,
                value="02/18/2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_9",
                field_type=MetadataFieldType.DATETIME,
                value="2025-18-02",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_10",
                field_type=MetadataFieldType.DATETIME,
                value="2025-02-18",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_11",
                field_type=MetadataFieldType.DATETIME,
                value="2025.18.02",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_12",
                field_type=MetadataFieldType.DATETIME,
                value="2025.02.18",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_13",
                field_type=MetadataFieldType.DATETIME,
                value="2025/18/02",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_14",
                field_type=MetadataFieldType.DATETIME,
                value="2025/02/18",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_15",
                field_type=MetadataFieldType.DATETIME,
                value="2025 Feb 18",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_16",
                field_type=MetadataFieldType.DATETIME,
                value="Feb 18 2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_17",
                field_type=MetadataFieldType.DATETIME,
                value="2025 February 18",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_18",
                field_type=MetadataFieldType.DATETIME,
                value="February 18 2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_19",
                field_type=MetadataFieldType.DATETIME,
                value="2025-2-18",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_20",
                field_type=MetadataFieldType.DATETIME,
                value="2025-2-2",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_21",
                field_type=MetadataFieldType.DATETIME,
                value="25-2-2",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_22",
                field_type=MetadataFieldType.DATETIME,
                value="1900-02-29",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_23",
                field_type=MetadataFieldType.DATETIME,
                value="1900-02-29 00:00",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_24",
                field_type=MetadataFieldType.DATETIME,
                value="1900-02-29 00:00:00",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_25",
                field_type=MetadataFieldType.DATETIME,
                value="2000-02-29",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_26",
                field_type=MetadataFieldType.DATETIME,
                value="2000-02-29 00:00",
            )
        assert Metadata.objects.count() == 0

        set_metadata(
            custom_key="datetime_27",
            field_type=MetadataFieldType.DATETIME,
            value="2000-02-29 00:00:00",
        )
        assert Metadata.objects.count() == 1

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_28",
                field_type=MetadataFieldType.DATETIME,
                value="2004-02-29",
            )
        assert Metadata.objects.count() == 1

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_29",
                field_type=MetadataFieldType.DATETIME,
                value="2004-02-29 00:00",
            )
        assert Metadata.objects.count() == 1

        set_metadata(
            custom_key="datetime_30",
            field_type=MetadataFieldType.DATETIME,
            value="2004-02-29 00:00:00",
        )
        assert Metadata.objects.count() == 2

        set_metadata(
            custom_key="datetime_31",
            field_type=MetadataFieldType.DATETIME,
            value="2025-02-18 20:00:00",
        )
        assert Metadata.objects.count() == 3

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_32",
                field_type=MetadataFieldType.DATETIME,
                value="2025-02-18 24:00:00",
            )
        assert Metadata.objects.count() == 3

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_33",
                field_type=MetadataFieldType.DATETIME,
                value="10:00",
            )
        assert Metadata.objects.count() == 3

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_34",
                field_type=MetadataFieldType.DATETIME,
                value="10:00:00",
            )
        assert Metadata.objects.count() == 3

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_35",
                field_type=MetadataFieldType.DATETIME,
                value="10:00:00.0000",
            )
        assert Metadata.objects.count() == 3

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_36",
                field_type=MetadataFieldType.DATETIME,
                value="2025-02-18 00:00:00.0000",
            )
        assert Metadata.objects.count() == 3

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="datetime_37",
                field_type=MetadataFieldType.DATETIME,
                value="Text",
            )
        assert Metadata.objects.count() == 3

        set_metadata(
            custom_key="datetime_38",
            field_type=MetadataFieldType.DATETIME,
            value=None,
        )
        assert Metadata.objects.count() == 4

        set_metadata(
            custom_key="datetime_39",
            field_type=MetadataFieldType.DATETIME,
            value="",
        )
        assert Metadata.objects.count() == 5

    def test_validate_date(self):
        """
        Ensure we get a correct validation of a date value.
        """
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_1",
                field_type=MetadataFieldType.DATE,
                value=1337,
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_2",
                field_type=MetadataFieldType.DATE,
                value=13.37,
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_3",
                field_type=MetadataFieldType.DATE,
                value="18-02-2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_4",
                field_type=MetadataFieldType.DATE,
                value="02-18-2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_5",
                field_type=MetadataFieldType.DATE,
                value="18.02.2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_6",
                field_type=MetadataFieldType.DATE,
                value="02.18.2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_7",
                field_type=MetadataFieldType.DATE,
                value="18/02/2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_8",
                field_type=MetadataFieldType.DATE,
                value="02/18/2025",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_9",
                field_type=MetadataFieldType.DATE,
                value="2025-18-02",
            )
        assert Metadata.objects.count() == 0

        set_metadata(
            custom_key="date_10",
            field_type=MetadataFieldType.DATE,
            value="2025-02-18",
        )
        assert Metadata.objects.count() == 1

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_11",
                field_type=MetadataFieldType.DATE,
                value="2025.18.02",
            )
        assert Metadata.objects.count() == 1

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_12",
                field_type=MetadataFieldType.DATE,
                value="2025.02.18",
            )
        assert Metadata.objects.count() == 1

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_13",
                field_type=MetadataFieldType.DATE,
                value="2025/18/02",
            )
        assert Metadata.objects.count() == 1

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_14",
                field_type=MetadataFieldType.DATE,
                value="2025/02/18",
            )
        assert Metadata.objects.count() == 1

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_15",
                field_type=MetadataFieldType.DATE,
                value="2025 Feb 18",
            )
        assert Metadata.objects.count() == 1

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_16",
                field_type=MetadataFieldType.DATE,
                value="Feb 18 2025",
            )
        assert Metadata.objects.count() == 1

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_17",
                field_type=MetadataFieldType.DATE,
                value="2025 February 18",
            )
        assert Metadata.objects.count() == 1

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_18",
                field_type=MetadataFieldType.DATE,
                value="February 18 2025",
            )
        assert Metadata.objects.count() == 1

        set_metadata(
            custom_key="date_19",
            field_type=MetadataFieldType.DATE,
            value="2025-2-18",
        )
        assert Metadata.objects.count() == 2

        set_metadata(
            custom_key="date_20",
            field_type=MetadataFieldType.DATE,
            value="2025-2-2",
        )
        assert Metadata.objects.count() == 3

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_21",
                field_type=MetadataFieldType.DATE,
                value="25-2-2",
            )
        assert Metadata.objects.count() == 3

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_22",
                field_type=MetadataFieldType.DATE,
                value="1900-02-29",
            )
        assert Metadata.objects.count() == 3

        set_metadata(
            custom_key="date_23",
            field_type=MetadataFieldType.DATE,
            value="2000-02-29",
        )
        assert Metadata.objects.count() == 4

        set_metadata(
            custom_key="date_24",
            field_type=MetadataFieldType.DATE,
            value="2004-02-29",
        )
        assert Metadata.objects.count() == 5

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_25",
                field_type=MetadataFieldType.DATE,
                value="2004-02-29 00:00",
            )
        assert Metadata.objects.count() == 5

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_26",
                field_type=MetadataFieldType.DATE,
                value="2004-02-29 00:00:00",
            )
        assert Metadata.objects.count() == 5

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="date_27",
                field_type=MetadataFieldType.DATE,
                value="Text",
            )
        assert Metadata.objects.count() == 5

        set_metadata(
            custom_key="date_28",
            field_type=MetadataFieldType.DATE,
            value=None,
        )
        assert Metadata.objects.count() == 6

        set_metadata(
            custom_key="date_29",
            field_type=MetadataFieldType.DATE,
            value="",
        )
        assert Metadata.objects.count() == 7

    def test_validate_time(self):
        """
        Ensure we get a correct validation of a time value.
        """
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="time_1",
                field_type=MetadataFieldType.TIME,
                value=1337,
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="time_2",
                field_type=MetadataFieldType.TIME,
                value=13.37,
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="time_3",
                field_type=MetadataFieldType.TIME,
                value="2025-02-18",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="time_4",
                field_type=MetadataFieldType.TIME,
                value="2025-02-18 00:00",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="time_5",
                field_type=MetadataFieldType.TIME,
                value="2025-02-18 00:00:00",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="time_6",
                field_type=MetadataFieldType.TIME,
                value="10:00",
            )
        assert Metadata.objects.count() == 0

        set_metadata(
            custom_key="time_7",
            field_type=MetadataFieldType.TIME,
            value="10:00:00",
        )
        assert Metadata.objects.count() == 1

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="time_8",
                field_type=MetadataFieldType.TIME,
                value="20:00",
            )
        assert Metadata.objects.count() == 1

        set_metadata(
            custom_key="time_9",
            field_type=MetadataFieldType.TIME,
            value="20:00:00",
        )
        assert Metadata.objects.count() == 2

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="time_10",
                field_type=MetadataFieldType.TIME,
                value="20:00:00.0000",
            )
        assert Metadata.objects.count() == 2

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="time_11",
                field_type=MetadataFieldType.TIME,
                value="2004-02-29 00:00",
            )
        assert Metadata.objects.count() == 2

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="time_12",
                field_type=MetadataFieldType.TIME,
                value="2004-02-29 00:00:00",
            )
        assert Metadata.objects.count() == 2

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="time_13",
                field_type=MetadataFieldType.TIME,
                value="2004-02-29 00:00:00.0000",
            )
        assert Metadata.objects.count() == 2

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="time_14",
                field_type=MetadataFieldType.TIME,
                value="Text",
            )
        assert Metadata.objects.count() == 2

        set_metadata(
            custom_key="time_15",
            field_type=MetadataFieldType.TIME,
            value=None,
        )
        assert Metadata.objects.count() == 3

        set_metadata(
            custom_key="time_16",
            field_type=MetadataFieldType.TIME,
            value="",
        )
        assert Metadata.objects.count() == 4

    def test_validate_selection(self):
        """
        Ensure we get a correct validation of a selection value.
        """
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="selection_1",
                field_type=MetadataFieldType.SELECTION,
                value="Option 1",
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="selection_2",
                field_type=MetadataFieldType.SELECTION,
                value="Option 1",
                config=dict(
                    key="value",
                ),
            )
        assert Metadata.objects.count() == 0

        with pytest.raises(ValidationError):
            set_metadata(
                custom_key="selection_3",
                field_type=MetadataFieldType.SELECTION,
                value="Option 1",
                config=dict(
                    options="Option 1",
                ),
            )
        assert Metadata.objects.count() == 0

        set_metadata(
            custom_key="selection_4",
            field_type=MetadataFieldType.SELECTION,
            value="Option 1",
            config=dict(
                options=[
                    "Option 1",
                ],
            ),
        )
        assert Metadata.objects.count() == 1

        metadata = set_metadata(
            custom_key="selection_5",
            field_type=MetadataFieldType.SELECTION,
            value="Option 2",
            config=dict(
                options=[
                    "Option 1",
                    "Option 2",
                    "Option 3",
                ],
            ),
        )
        assert Metadata.objects.count() == 2
        assert metadata.get_value() == "Option 2"
        assert metadata.config is not None
        assert "options" in metadata.config
        assert len(metadata.config["options"]) == 3
        assert all(
            option
            in [
                "Option 1",
                "Option 2",
                "Option 3",
            ]
            for option in metadata.config["options"]
        )

        set_metadata(
            custom_key="selection_6",
            field_type=MetadataFieldType.SELECTION,
            value="",
            config=dict(
                options=[
                    "",
                    "Option 1",
                    "Option 2",
                    "Option 3",
                ],
            ),
        )
        assert Metadata.objects.count() == 3

        set_metadata(
            custom_key="selection_7",
            field_type=MetadataFieldType.SELECTION,
            value=None,
            config=dict(
                options=[
                    "",
                    "Option 1",
                    "Option 2",
                    "Option 3",
                ],
            ),
        )
        assert Metadata.objects.count() == 4

        set_metadata(
            custom_key="selection_8",
            field_type=MetadataFieldType.SELECTION,
            value=1,
            config=dict(
                options=[
                    "1",
                ],
            ),
        )
        assert Metadata.objects.count() == 5

    def test_delete(self):
        """
        Ensure we can delete a metadata field if it is not in use.
        """
        assert MetadataField.objects.count() == 1

        self.metadata_field_1.delete()
        assert MetadataField.objects.count() == 0

    def test_delete_protection_due_to_linked_metadata(self):
        """
        Ensure we can't delete a metadata field if it is in use.
        """
        set_metadata(
            field=self.metadata_field_1,
            value="custom_value_1",
        )

        with pytest.raises(PermissionDenied):
            self.metadata_field_1.delete()

    def test_delete_protection_due_to_linked_metadata_field(self):
        """
        Ensure we can't delete a metadata field if it is in use.
        """
        metadata_template_1 = MetadataTemplate.objects.create(
            name="Metadata template 1",
        )

        MetadataTemplateField.objects.create(
            metadata_template=metadata_template_1,
            field=self.metadata_field_1,
        )

        with pytest.raises(PermissionDenied):
            self.metadata_field_1.delete()

    def test_field_type_protection_due_to_linked_metadata(self):
        """
        Ensure we can't change the field type of a metadata field if it is in use.
        """
        self.metadata_field_1.field_type = MetadataFieldType.DECIMAL
        self.metadata_field_1.save()

        set_metadata(
            field=self.metadata_field_1,
            value=13.37,
        )

        with pytest.raises(PermissionDenied):
            self.metadata_field_1.field_type = MetadataFieldType.INTEGER
            self.metadata_field_1.save()

    def test_field_type_protection_due_to_linked_metadata_field(self):
        """
        Ensure we can't change the field type of a metadata field if it is in use.
        """
        self.metadata_field_1.field_type = MetadataFieldType.DECIMAL
        self.metadata_field_1.save()

        metadata_template_1 = MetadataTemplate.objects.create(
            name="Metadata template 1",
        )

        MetadataTemplateField.objects.create(
            metadata_template=metadata_template_1,
            field=self.metadata_field_1,
        )

        with pytest.raises(PermissionDenied):
            self.metadata_field_1.field_type = MetadataFieldType.INTEGER
            self.metadata_field_1.save()


@pytest.mark.django_db
class TestMetadataTemplateModel:
    @pytest.fixture(autouse=True)
    def _setup(self, initial_users):
        set_request_for_user(initial_users["user_1"])

        self.project_1 = Project.objects.create(
            name="Project 1",
        )

    def test_creation_helper(self, initial_users):
        """
        Ensure we can create a new metadata template with a helper function.
        """
        metadata_template = create_metadata_template_for_object(
            metadata_template_data={
                "name": "Metadata template 1",
            },
            metadata_template_fields=[
                {
                    "custom_key": "custom_key_1",
                    "value": "custom value",
                    "mandatory": True,
                },
                {
                    "custom_key": "custom_key_2",
                    "mandatory": False,
                },
            ],
            assigned_to_object=self.project_1,
        )
        assert metadata_template is not None
        assert MetadataTemplate.objects.count() == 1

        metadata_template = create_metadata_template_for_object(
            metadata_template_data={
                "name": "Metadata template 2",
            },
            metadata_template_fields=[
                {
                    "custom_key": "custom_key_1",
                    "value": "custom value",
                    "mandatory": True,
                },
                {
                    "custom_key": "custom_key_2",
                    "mandatory": False,
                },
            ],
            assigned_to_object=self.project_1.folders.first(),
        )
        assert metadata_template is not None
        assert MetadataTemplate.objects.count() == 2

        metadata_template = create_metadata_template_for_object(
            metadata_template_data={
                "name": "Metadata template 3",
            },
            metadata_template_fields=[
                {
                    "custom_key": "custom_key_1",
                    "value": "custom value",
                    "mandatory": True,
                },
                {
                    "custom_key": "custom_key_2",
                    "mandatory": False,
                },
            ],
            assigned_to_object=self.project_1.folders.first(),
            user=initial_users["user_1"],
        )
        assert metadata_template is not None
        assert MetadataTemplate.objects.count() == 3

        with transaction.atomic():
            with pytest.raises(PermissionDenied):
                create_metadata_template_for_object(
                    metadata_template_data={
                        "name": "Metadata template 4",
                    },
                    metadata_template_fields=[
                        {
                            "custom_key": "custom_key_1",
                            "value": "custom value",
                            "mandatory": True,
                        },
                        {
                            "custom_key": "custom_key_2",
                            "mandatory": False,
                        },
                    ],
                    assigned_to_object=self.project_1.folders.first(),
                    user=initial_users["user_2"],
                )

        assert MetadataTemplate.objects.count() == 3

    def test_permission_helper(self, initial_users):
        """
        Ensure we can check the permissions for creating a new metadata template with a helper function.
        """
        check_metadata_template_permissions_for_object(
            content_type=get_content_type_for_object(self.project_1.get_content_type()),
            object_id=self.project_1.pk,
            user=initial_users["user_1"],
        )

        with pytest.raises(PermissionDenied):
            check_metadata_template_permissions_for_object(
                content_type=get_content_type_for_object(self.project_1.get_content_type()),
                object_id=self.project_1.pk,
                user=initial_users["user_2"],
            )


@pytest.mark.django_db
class TestMetadataTemplateLockMixin:
    @pytest.fixture(autouse=True)
    def _setup(self, initial_users):
        set_request_for_user(initial_users["user_1"])

        self.metadata_template_1 = MetadataTemplate.objects.create(
            name="Metadata template 1",
        )

    def test_lock(self, initial_users):
        """
        Ensure we have an expected lock behavior.
        """
        metadata_template = MetadataTemplate.objects.get(pk=self.metadata_template_1.pk)
        metadata_template.name = "Metadata template 1"
        metadata_template.save()

        metadata_template.refresh_from_db()
        assert metadata_template.name == "Metadata template 1"
        assert metadata_template.locked is False
        assert metadata_template.locked_by is None
        assert metadata_template.locked_at is None

        metadata_template.lock()

        metadata_template.refresh_from_db()
        assert metadata_template.name == "Metadata template 1"
        assert metadata_template.locked is True
        assert metadata_template.locked_by == initial_users["user_1"]
        assert metadata_template.locked_at is not None

        last_lock_time = metadata_template.locked_at

        metadata_template.lock()

        metadata_template.refresh_from_db()
        assert metadata_template.name == "Metadata template 1"
        assert metadata_template.locked is True
        assert metadata_template.locked_by == initial_users["user_1"]
        assert metadata_template.locked_at is not None
        assert metadata_template.locked_at > last_lock_time

        metadata_template.name = "Metadata template 1 - Edit #1"
        metadata_template.save()

        metadata_template.refresh_from_db()
        assert metadata_template.name == "Metadata template 1 - Edit #1"
        assert metadata_template.locked is False
        assert metadata_template.locked_by is None
        assert metadata_template.locked_at is None

        metadata_template.lock()

        metadata_template.refresh_from_db()
        assert metadata_template.name == "Metadata template 1 - Edit #1"
        assert metadata_template.locked is True
        assert metadata_template.locked_by == initial_users["user_1"]
        assert metadata_template.locked_at is not None

        metadata_template.unlock()

        metadata_template.refresh_from_db()
        assert metadata_template.name == "Metadata template 1 - Edit #1"
        assert metadata_template.locked is False
        assert metadata_template.locked_by is None
        assert metadata_template.locked_at is None

        metadata_template.lock()
        last_lock_time = metadata_template.locked_at

        metadata_template.name = "Metadata template 1 - Edit #2"
        metadata_template.save(auto_unlock=False)

        metadata_template.refresh_from_db()
        assert metadata_template.name == "Metadata template 1 - Edit #2"
        assert metadata_template.locked is True
        assert metadata_template.locked_by == initial_users["user_1"]
        assert metadata_template.locked_at is not None
        assert metadata_template.locked_at == last_lock_time

        last_lock_time = metadata_template.locked_at

        set_request_for_user(initial_users["user_2"])

        with pytest.raises(PermissionDenied):
            metadata_template.name = "Metadata template 1 - Edit #3"
            metadata_template.save()

        metadata_template.refresh_from_db()
        assert metadata_template.name == "Metadata template 1 - Edit #2"
        assert metadata_template.locked_at == last_lock_time

        metadata_template.name = "Metadata template 1 - Edit #3"
        metadata_template.locked_at = timezone.now() - timezone.timedelta(minutes=settings.MAX_LOCK_TIME)
        metadata_template.save()

        metadata_template.refresh_from_db()
        assert metadata_template.name == "Metadata template 1 - Edit #3"
        assert metadata_template.locked is False
        assert metadata_template.locked_by is None
        assert metadata_template.locked_at is None
