import contextlib
from collections import defaultdict
from datetime import datetime
from typing import Iterable, TypeVar, TypedDict

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


FILE_MARKER = "<files>"
CleanName = TypeVar("CleanName", bound=str)


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
