#!/usr/bin/env python

import re
import subprocess
from pathlib import Path


repo_root = Path(__file__).resolve().parent.parent
pyproject_path = repo_root / "pyproject.toml"


def ask_bump_type() -> int:
    while True:
        print("What kind of bump do you want?\n\n  (1) patch\n  (2) minor\n  (3) major\n")
        answer = input("[Default 1]: ")
        if answer == "":
            answer = 1
        else:
            try:
                answer = int(answer)
            except ValueError:
                continue
        break

    return answer


def get_new_version(current_version: str) -> str:
    print(f"Current version: {current_version}")
    bump_type = ask_bump_type()
    print()

    version_matches = re.search(r"(\d+)\.(\d+)\.(\d+)", current_version)
    if not version_matches:
        print("Current version looks funky, please fix before you continue")
        exit(1)
    cur_major, cur_minor, cur_patch = version_matches.groups()

    if bump_type == 1:
        cur_patch = int(cur_patch) + 1
    elif bump_type == 2:
        cur_minor = int(cur_minor) + 1
        cur_patch = 0
    elif bump_type == 3:
        cur_major = int(cur_major) + 1
        cur_patch = cur_minor = 0

    new_version = f"{cur_major}.{cur_minor}.{cur_patch}"
    print(f"\nnew version: {new_version}")
    if input("Does that look ok? [Yn]: ") == "n":
        exit(1)

    return new_version

def commit_version_change(version: str):
    answer = input("Do you want to commit the version bump and create a new tag? [Yn]")
    if answer == "n":
        return

    commit_msg = f"version: bump to {version}"
    tag_msg = f"Version {version}"
    output = subprocess.check_output(["git", "-P", "diff", "--name-only", "--cached"]).decode("utf-8")
    if output != "":
        print("The following files are staged, which is not expected.\n")
        print(output)
        print(
            "Make sure you have no staged files before using this script. "
            "For example by running 'git restore --staged -- .'"
        )
        exit(1)

    subprocess.run(
        [
            "git",
            "add",
            pyproject_path
        ],
        check=True,
    )
    subprocess.run(["git", "commit", "-m", commit_msg])

    subprocess.run(["git", "tag", "-a", version, "-m", tag_msg])

    print("Commit built, dont forget to push :)")
    print(f"To push the new created tag use the following command: \"git push origin tag {version}\"")


def get_current_version(pyproject_lines: list[str]) -> str:
    current_version = None
    for line in pyproject_lines:
        if line.startswith("version"):
            current_version = line.split("=")[1].strip()

    if not current_version:
        print("Found no line starting with \"version\" in the pyproject.toml. Please fix before you continue")
        exit(1)

    return current_version


def write_version(version: str, pyproject_lines: list[str]):
    with open(pyproject_path, "w") as pyproject_file:
        for line in pyproject_lines:
            if line.startswith("version"):
                line = f"version = \"{version}\"\n"
            pyproject_file.write(line)


def main():
    with open(pyproject_path, "r") as pyproject_file:
        pyproject_lines = pyproject_file.readlines()

    current_version = get_current_version(pyproject_lines)
    new_version = get_new_version(current_version)
    write_version(new_version, pyproject_lines)

    commit_version_change(new_version)


if __name__ == "__main__":
    main()
