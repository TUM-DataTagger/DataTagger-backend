import pytest

from fdm.dbsettings.functions import get_dbsettings_value, set_dbsettings_value


@pytest.mark.django_db
class TestDBSettingsFunctions:
    def test_settings_functions(self):
        """
        Ensure we get the correct settings value, and we can change it too.
        """
        with pytest.raises(KeyError):
            get_dbsettings_value("test", None)

        setting = get_dbsettings_value("test", "default")
        assert setting == "default"

        set_dbsettings_value("test", "my value")
        setting = get_dbsettings_value("test", "default")
        assert setting == "my value"
