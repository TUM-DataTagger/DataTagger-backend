from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

import pytest
from PIL import Image

from fdm.file_parser.models import ChecksumParser, ExifParser, FileInformationParser, FileParser, MimeTypeParser
from fdm.metadata.models import Metadata
from fdm.uploads.models import UploadsVersionFile


def get_dummy_image() -> Image:
    image_data = BytesIO()

    with Image.new("RGB", (1, 1), (0, 0, 0)) as image_file:
        exif_data = image_file.getexif()
        exif_data[0x9286] = "User comment"
        image_file.save(image_data, format="PNG", exif=exif_data)

    image_data.seek(0)

    return image_data.read()


def get_dummy_textfile() -> bytes:
    text_data = BytesIO(b"Random string")
    text_data.seek(0)

    return text_data.read()


@pytest.mark.django_db
class TestFileParserModel:
    @pytest.fixture(autouse=True)
    def _setup(self):
        current_date = timezone.now()

        self.random_filename = f"{current_date.strftime('%Y-%m-%dT%H-%M-%S-%f')}.png"

        sample_file = SimpleUploadedFile(
            self.random_filename,
            get_dummy_image(),
            content_type="image/png",
        )

        self.uploads_version_file_1 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

    def test_read_file_checksums(self):
        """
        Ensure we can read the checksums of a file.
        """
        parser = ChecksumParser(file=self.uploads_version_file_1)

        checksum = parser.parse(algorithm=FileParser.Type.CHECKSUM_SHA256)
        assert checksum == "a91ad0f59364078f0513a3172236721fdedfcd030b2d9157a13bbd7e26e834eb"

        metadata = Metadata.objects.filter(
            assigned_to_content_type=self.uploads_version_file_1.get_content_type(),
            assigned_to_object_id=self.uploads_version_file_1.pk,
        )
        assert metadata.count() == 0

        parser.parse(algorithm=FileParser.Type.CHECKSUM_SHA256, set_metadata=True)
        assert metadata.count() == 1

    def test_read_file_checksum_with_invalid_algorithm(self):
        """
        Ensure we get an error if we try to read the checksum of a file with an invalid algorithm.
        """
        parser = ChecksumParser(file=self.uploads_version_file_1)

        with pytest.raises(NotImplementedError):
            parser.parse(algorithm="NotImplementedAlgorithm")

    def test_read_file_exif_data(self):
        """
        Ensure we can read the exif data of a file.
        """
        parser = ExifParser(file=self.uploads_version_file_1)
        exif_data = parser.parse()
        assert exif_data["UserComment"] == "User comment"

        metadata = Metadata.objects.filter(
            assigned_to_content_type=self.uploads_version_file_1.get_content_type(),
            assigned_to_object_id=self.uploads_version_file_1.pk,
        )
        assert metadata.count() == 0

        parser.parse(set_metadata=True)
        assert metadata.count() == 1

    def test_read_file_exif_data_from_ineligible_file(self):
        """
        Ensure we get an empty dict if we try to read the Exif data from an ineligible file.
        """
        sample_file = SimpleUploadedFile(
            "dummy.txt",
            get_dummy_textfile(),
            content_type="text/plain",
        )

        self.uploads_version_file_2 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        parser = ExifParser(file=self.uploads_version_file_2)
        exif_data = parser.parse()
        assert exif_data == {}

    def test_read_file_mime_type(self):
        """
        Ensure we can read the mime type of a file.
        """
        parser = MimeTypeParser(file=self.uploads_version_file_1)
        mime_type = parser.parse()
        assert mime_type == "image/png"

        metadata = Metadata.objects.filter(
            assigned_to_content_type=self.uploads_version_file_1.get_content_type(),
            assigned_to_object_id=self.uploads_version_file_1.pk,
        )
        assert metadata.count() == 0

        parser.parse(set_metadata=True)
        assert metadata.count() == 1

    def test_read_file_information(self):
        """
        Ensure we can read the essential information of a file.
        """
        parser = FileInformationParser(file=self.uploads_version_file_1)

        information = parser.parse()
        assert self.uploads_version_file_1.name == self.random_filename
        assert information["file_name"] == self.uploads_version_file_1.name
        assert information["file_size"] == self.uploads_version_file_1.file_size
        assert information["file_relative_path"] == self.uploads_version_file_1.relative_path

        metadata = Metadata.objects.filter(
            assigned_to_content_type=self.uploads_version_file_1.get_content_type(),
            assigned_to_object_id=self.uploads_version_file_1.pk,
        )
        assert metadata.count() == 0

        parser.parse(set_metadata=True)
        assert metadata.count() == 3

        # Run this test again. There can still only be 3 metadata entries because the old ones have to be deleted first.
        parser.parse(set_metadata=True)
        assert metadata.count() == 3
