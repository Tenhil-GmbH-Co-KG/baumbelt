from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.timezone import make_naive
from storages.backends.s3boto3 import S3Boto3Storage
from storages.utils import clean_name, setting


from .utils import (
    BucketDict,
    CleanName,
    BucketItem,
    build_tree_from_files_list,
    is_dir_in_tree,
    get_content_at_path,
    wait_for_tasks,
)


class DirectoryCheckS3Storage(S3Boto3Storage):
    """
    Subclass to enable check for 'directory' existence.

    Imagine your bucket containing a key "<location>/myfolder/myfile.txt".

    When using the base class, the following will be returned:
        exists("myfolder/myfile.txt") -> True
        exists("myfolder/") -> False
        exists("myfolder") -> False
        exists("myfol") -> False

    When using this class, it looks like this:
        exists("myfolder/myfile.txt") -> True
        exists("myfolder/") -> True
        exists("myfolder") -> True
        exists("myfol") -> False
    """

    def exists(self, name):
        if super().exists(name):
            return True

        name = self._normalize_name(clean_name(name))
        dir_name = name if name.endswith("/") else f"{name}/"
        object_list = self.connection.meta.client.list_objects(
            Bucket=self.bucket_name,
            Prefix=dir_name,
            MaxKeys=1,
        )
        if object_list.get("Contents"):
            # there are files with this directory-like prefix -> consider it a directory
            return True

        return False


class PublicMediaStorage(DirectoryCheckS3Storage):
    @property
    def bucket_name(self):
        if not hasattr(settings, "AWS_PUBLIC_BUCKET"):
            raise ImproperlyConfigured("settings must contain AWS_PUBLIC_BUCKET when using PublicMediaStorage")
        return settings.AWS_PUBLIC_BUCKET

    @property
    def location(self):
        if not hasattr(settings, "PUBLIC_MEDIA_LOCATION"):
            raise ImproperlyConfigured("settings must contain PUBLIC_MEDIA_LOCATION when using PublicMediaStorage")
        return settings.PUBLIC_MEDIA_LOCATION

    @property
    def custom_domain(self):
        if not hasattr(settings, "MEDIA_DOMAIN"):
            raise ImproperlyConfigured("settings must contain MEDIA_DOMAIN when using PublicMediaStorage")
        return settings.MEDIA_DOMAIN


class PrivateMediaStorage(DirectoryCheckS3Storage):
    @property
    def bucket_name(self):
        if not hasattr(settings, "AWS_PRIVATE_BUCKET"):
            raise ImproperlyConfigured("settings must contain AWS_PRIVATE_BUCKET when using PrivateMediaStorage")
        return settings.AWS_PRIVATE_BUCKET

    @property
    def location(self):
        if not hasattr(settings, "PRIVATE_MEDIA_LOCATION"):
            raise ImproperlyConfigured("settings must contain PRIVATE_MEDIA_LOCATION when using PrivateMediaStorage")
        return settings.PRIVATE_MEDIA_LOCATION

    custom_domain = None  # private


class StaticStorage(DirectoryCheckS3Storage):
    querystring_auth = False  # see storages.backends.s3boto3.S3StaticStorage

    @property
    def bucket_name(self):
        if not hasattr(settings, "AWS_PUBLIC_BUCKET"):
            raise ImproperlyConfigured("settings must contain AWS_PUBLIC_BUCKET when using StaticStorage")
        return settings.AWS_PUBLIC_BUCKET

    @property
    def location(self):
        if not hasattr(settings, "STATIC_LOCATION"):
            raise ImproperlyConfigured("settings must contain STATIC_LOCATION when using StaticStorage")
        return settings.STATIC_LOCATION

    @property
    def custom_domain(self):
        if not hasattr(settings, "STATIC_DOMAIN"):
            raise ImproperlyConfigured("settings must contain STATIC_DOMAIN when using StaticStorage")
        return settings.STATIC_DOMAIN


class BulkStaticStorage(StaticStorage):
    """
    When working on many static files, a significant IO overhead is paid.
    To enable a "bulk" strategy with S3, we do the following:

        - defer saving files
        - prefetch bucket contents for fast `exists` and `modified_time` lookups
        - build a local tree-structure of the bucket's contents for `listdir` lookups

    Only on "post_process", which `collectstatic` calls after iterating over
    local files, we spawn a bunch of threads to upload/delete the files.

    To properly support the `--clear` flag, we needed to hack around with the `listdir`
    function.
    """

    # This dict maps absolute file paths (eg `static/admin/css/dropdown.css`) to a
    # BucketItem dictionary, containing meta information.
    _fetched_bucket: BucketDict | None = None
    # The file_tree mirrors a filesystem-structure, with nested dicts mirroring
    # folders containing files and other folders.
    _bucket_file_tree: dict | None = None

    _files_to_save: list[tuple[str, BytesIO]] = []
    _files_to_delete: set[str] = set()

    # >7 threads tend to cause hangs on API calls.
    S3_API_THREADS = 7

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._real_delete_fn = super().delete

    def _fetch_bucket(self):
        client = self.connection.meta.client
        iterator = client.get_paginator("list_objects_v2").paginate(Bucket=self.bucket_name, Prefix=self.location)
        items: BucketDict = {}
        for page in iterator:
            item: BucketItem
            for item in page.get("Contents", []):
                items[item["Key"]] = item

        return items

    @property
    def bucket_contents(self) -> BucketDict:
        if self._fetched_bucket is None:
            self._fetched_bucket = self._fetch_bucket()
        return self._fetched_bucket

    @property
    def bucket_tree(self):
        if self._bucket_file_tree is None:
            self._bucket_file_tree = build_tree_from_files_list(files=self.bucket_contents.keys())
        return self._bucket_file_tree

    def _prepare_name(self, name: str) -> CleanName:
        return self._normalize_name(clean_name(name))

    def exists(self, name: str):
        # Special case for `--clear` and root-directory.
        if name == "":
            return True

        cleaned_name = self._prepare_name(name)
        exists_in_bucket = cleaned_name in self.bucket_contents
        if exists_in_bucket:
            return True

        return is_dir_in_tree(tree=self.bucket_tree[self.location], name=name)

    def listdir(self, name):
        cleaned_name = self._prepare_name(name)
        dirs, files = get_content_at_path(path=cleaned_name, tree=self.bucket_tree)
        return dirs, files

    def get_modified_time(self, name: str):
        cleaned_name = self._prepare_name(name)
        item: BucketItem = self.bucket_contents[cleaned_name]

        # Mirrors super().get_modified_time(name) behaviour.
        if setting("USE_TZ"):
            return item["LastModified"]
        else:
            return make_naive(item["LastModified"])

    def delete(self, name):
        self._files_to_delete.add(name)
        cleaned_name = self._prepare_name(name)
        # Remove our local reference to that file, so that we can act like we never saw it later.
        del self.bucket_contents[cleaned_name]

    def save(self, name, fileobj, max_length=None):
        # have to read the file's content here, otherwise it is closed again once we need it.
        self._files_to_save.append((name, BytesIO(fileobj.read())))

        try:
            # If file is also marked to be deleted on S3, we remove that again.
            # Essentially overwriting what S3 holds. Only relevant in `--clear` scenario.
            self._files_to_delete.remove(name)
        except KeyError:
            pass

    def _upload_deferred_save_calls(self):
        with ThreadPoolExecutor(max_workers=self.S3_API_THREADS) as executor:
            futures = [executor.submit(self._save, name=name, content=content) for name, content in self._files_to_save]

        exceptions = wait_for_tasks(futures, desc="s3 upload")

        print(f"Upload-Executor done, {len(self._files_to_save)} tasks submitted.")
        if exceptions:
            print(f"{len(exceptions)} exceptions occurred. Here's the last one. Enjoy!")
            raise AssertionError("Uploading failed") from exceptions[-1]

    def _flush_deferred_delete_calls(self):
        with ThreadPoolExecutor(max_workers=self.S3_API_THREADS) as executor:
            futures = [executor.submit(self._real_delete_fn, name=name) for name in self._files_to_delete]

        exceptions = wait_for_tasks(futures, desc="s3 delete")

        print(f"Delete-Executor done, {len(self._files_to_save)} tasks submitted.")
        if exceptions:
            print(f"{len(exceptions)} exceptions occurred. Here's the last one. Enjoy!")
            raise AssertionError("Deleting failed") from exceptions[-1]

    def post_process(self, file_paths: list[str], dry_run: bool = False):
        if not dry_run:
            self._upload_deferred_save_calls()
            self._flush_deferred_delete_calls()

        return []


class CdnBulkStaticStorage(BulkStaticStorage):
    """
    When configuring a CDN (eg AWS Cloudfront), it's likely that it serves
    from a private bucket. The default BulkStaticStorage requires a public bucket.
    """

    @property
    def bucket_name(self):
        if not hasattr(settings, "AWS_PRIVATE_BUCKET"):
            raise ImproperlyConfigured("settings must contain AWS_PRIVATE_BUCKET when using CdnBulkStaticStorage")
        return settings.AWS_PRIVATE_BUCKET
