from unittest import TestCase
from unittest.mock import MagicMock, patch

from storages.backends.s3 import S3Storage

from baumbelt.django.s3utils.utils import delete_unreferenced_files


def make_s3_storage(bucket_name="my-bucket", location="media"):
    storage = object.__new__(S3Storage)
    storage.bucket_name = bucket_name
    storage.location = location
    return storage


def make_field(storage, used_filenames, model_name="MyModel", field_name="file"):
    field = MagicMock()
    field.storage = storage
    field.name = field_name
    field.model.__name__ = model_name
    field.model.objects.values_list.return_value = used_filenames
    return field


class DeleteUnreferencedFilesTestCase(TestCase):
    def test_non_s3_storage_is_a_no_op(self):
        field = make_field(storage=MagicMock(), used_filenames=[])

        with patch("baumbelt.django.s3utils.utils.boto3") as boto3:
            delete_unreferenced_files(field, filename_prefix="uploads/")

        boto3.client.assert_not_called()

    @patch("baumbelt.django.s3utils.utils.boto3")
    def test_deletes_only_unreferenced_keys(self, boto3):
        storage = make_s3_storage()
        field = make_field(storage, used_filenames=["uploads/used.txt"])
        s3_client = boto3.client.return_value
        s3_client.list_objects.return_value = {
            "Contents": [{"Key": "media/uploads/used.txt"}, {"Key": "media/uploads/orphan.txt"}],
            "IsTruncated": False,
        }
        s3_client.delete_objects.return_value = {"Deleted": [{"Key": "media/uploads/orphan.txt"}]}

        delete_unreferenced_files(field, filename_prefix="uploads/")

        s3_client.delete_objects.assert_called_once_with(
            Bucket="my-bucket",
            Delete={"Objects": [{"Key": "media/uploads/orphan.txt"}]},
        )

    @patch("baumbelt.django.s3utils.utils.boto3")
    def test_dry_run_never_calls_delete_objects(self, boto3):
        storage = make_s3_storage()
        field = make_field(storage, used_filenames=[])
        s3_client = boto3.client.return_value
        s3_client.list_objects.return_value = {
            "Contents": [{"Key": "media/uploads/orphan.txt"}],
            "IsTruncated": False,
        }

        delete_unreferenced_files(field, filename_prefix="uploads/", dry_run=True)

        s3_client.delete_objects.assert_not_called()

    @patch("baumbelt.django.s3utils.utils.boto3")
    def test_raises_when_s3_reports_deletion_errors(self, boto3):
        storage = make_s3_storage()
        field = make_field(storage, used_filenames=[])
        s3_client = boto3.client.return_value
        s3_client.list_objects.return_value = {
            "Contents": [{"Key": "media/uploads/orphan.txt"}],
            "IsTruncated": False,
        }
        s3_client.delete_objects.return_value = {"Errors": [{"Key": "media/uploads/orphan.txt", "Message": "nope"}]}

        with self.assertRaises(AssertionError):
            delete_unreferenced_files(field, filename_prefix="uploads/")
