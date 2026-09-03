import contextlib
import logging
from collections import defaultdict
from datetime import datetime
from typing import Iterable, TypeVar, TypedDict

import boto3
from django.db.models import FileField
from storages.backends.s3 import S3Storage

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

logger = logging.getLogger(__name__)

FILE_MARKER = "<files>"
CleanName = TypeVar("CleanName", bound=str)
_DELETE_BATCH_SIZE = 1000


class BucketItem(TypedDict):
    ETag: str
    Key: CleanName
    LastModified: datetime
    Size: int


BucketDict = dict[CleanName, BucketItem]


def prettify_tree(d, indent=0):
    for key, value in d.items():
        if key == FILE_MARKER:
            if value:
                for f in value:
                    print("  " * indent + f)
        else:
            print("  " * indent + str(key))
            if isinstance(value, dict):
                prettify_tree(value, indent + 1)
            else:
                print("  " * (indent + 1) + str(value))


def _attach(branch, trunk):
    parts = branch.split("/", 1)
    if len(parts) == 1:  # branch is a file
        trunk[FILE_MARKER].append(parts[0])
    else:
        node, others = parts
        if node not in trunk:
            trunk[node] = defaultdict(dict)
            trunk[node][FILE_MARKER] = []
        _attach(others, trunk[node])


def build_tree_from_files_list(files: Iterable[str]) -> dict:
    """
    Tree building is heavily inspired by https://stackoverflow.com/a/8496834/2547281

    It builds a dictionary, that mirrors a file tree, based on a list of file paths. Eg:

        ["root/sub1/baum.txt", "root/sub1/sub11/foo.txt", "root/bar.json"]

    yields:

        root:
            <files>: [bar.json]
            sub1:
                <files>: [baum.txt]
                sub11:
                    <files>: [foo.txt]

    """
    directory_tree = defaultdict(list)
    directory_tree[FILE_MARKER] = []

    for filepath in files:
        _attach(filepath, directory_tree)

    return directory_tree


def get_content_at_path(path: str, tree: dict) -> tuple[list[str], list[str]]:
    d = tree
    if path.endswith("/"):
        path = path[:-1]

    for part in path.split("/"):
        if part not in d:
            return [], []
        d = d[part]

    files = d[FILE_MARKER]
    directories = [_d for _d in d if _d != FILE_MARKER]
    return directories, files


def is_dir_in_tree(tree: dict, name: str) -> bool:
    d = tree
    res = None
    for part in name.split("/"):
        if part not in d:
            res = False
            break
        d = d[part]
    if res is None:
        res = True

    return res


def wait_for_tasks(futures: list, desc):
    exceptions = []
    cm = tqdm(total=len(futures), desc=desc) if tqdm else contextlib.nullcontext()
    with cm as pbar:
        for fut in futures:
            try:
                _ = fut.result(timeout=60)
            except Exception as e:
                exceptions.append(e)
            if pbar:
                pbar.update(1)
    return exceptions


def _fetch_all_file_keys(s3_client, bucket: str, prefix: str) -> set[str]:
    logger.debug(f"listing files in bucket '{bucket}' with prefix '{prefix}' ..")
    file_keys: set[str] = set()
    marker = ""
    done = False
    while not done:
        response: dict = s3_client.list_objects(Bucket=bucket, Prefix=prefix, MaxKeys=_DELETE_BATCH_SIZE, Marker=marker)
        files: list[dict] = response.get("Contents", [])
        file_keys.update(file["Key"] for file in files)
        if response["IsTruncated"]:
            logger.debug(f"listed {len(files)} files, but there's more ..")
            marker = files[-1]["Key"]
        else:
            logger.debug(f"listed {len(files)} files, done")
            done = True

    return file_keys


def _delete_file_keys(s3_client, bucket: str, file_keys: list[str], dry_run: bool) -> tuple[int, int]:
    deleted_count, error_count = 0, 0
    for start_idx in range(0, len(file_keys), _DELETE_BATCH_SIZE):
        file_key_batch = file_keys[start_idx : start_idx + _DELETE_BATCH_SIZE]
        payload = [{"Key": key} for key in file_key_batch]
        if dry_run:
            logger.debug(f"would delete batch of {len(payload)} files (if not in a dry-run)")
            deleted_count += len(payload)
            continue

        logger.debug(f"deleting batch of {len(payload)} files ..")
        response: dict = s3_client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": payload},
        )
        if deletions := response.get("Deleted"):
            deleted_count += len(deletions)
        if errors := response.get("Errors"):
            error_count += len(errors)
            for err in errors:
                logger.warning(f"deletion failed: {err}")

    return deleted_count, error_count


def delete_unreferenced_files(field: FileField, filename_prefix: str, dry_run: bool = False) -> None:
    model = field.model
    verbose_name = f"{model.__name__}.{field.name}"
    logger.debug(f"going to delete files that are no longer referenced by {verbose_name}")

    if dry_run:
        logger.debug("no worries, this is just a dry run")

    storage = field.storage
    if not isinstance(storage, S3Storage):
        logger.warning(f"storage of {verbose_name} is not an S3Storage, but {type(storage)}, won't delete anything")
        return

    used_filenames = set(model.objects.values_list(field.name, flat=True))
    logger.debug(f"{len(used_filenames)} files are referenced in the db and won't be deleted")

    s3_client = boto3.client(service_name="s3")

    # if it's an S3Storage, it must be a PublicMediaStorage or PrivateMediaStorage (from s3utils)
    # so we can expect it to have specific properties
    bucket = storage.bucket_name
    s3_prefix = f"{storage.location}/"

    s3_prefix_length = len(s3_prefix)
    full_prefix = f"{s3_prefix}{filename_prefix}"

    all_file_keys = _fetch_all_file_keys(s3_client, bucket, full_prefix)
    logger.debug(f"fetched {len(all_file_keys)} file keys in total")

    file_keys_to_delete, file_keys_to_keep = [], []
    for key in all_file_keys:
        filename = key[s3_prefix_length:]
        if filename in used_filenames:
            file_keys_to_keep.append(key)
        else:
            file_keys_to_delete.append(key)

    logger.debug(
        f"going to delete {len(file_keys_to_delete)} unused files from S3 "
        f"({len(file_keys_to_keep)} files will be left untouched)"
    )

    deleted_count, error_count = _delete_file_keys(s3_client, bucket, file_keys_to_delete, dry_run)

    if error_count:
        raise AssertionError(f"could not delete {error_count} files from S3")

    if deleted_count != (expected := len(file_keys_to_delete)):
        raise AssertionError(f"{deleted_count} files were deleted from S3, but we expected {expected}")

    if dry_run:
        logger.info(f"would have deleted {deleted_count} files from S3 (if not in a dry-run)")
    else:
        logger.info(f"successfully deleted {deleted_count} files from S3")
