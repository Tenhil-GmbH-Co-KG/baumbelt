import os
import time
from typing import TypedDict

import psutil


class RunningManagementCommand(TypedDict):
    pid: int
    cmd_name: str
    running_seconds: int


def list_running_management_commands() -> list[RunningManagementCommand]:
    """Scan the process table for `manage.py <command>` children, e.g. running cronjobs.

    Source of truth for "is a cronjob still running" when there's no k8s API to ask instead
    (e.g. a long-lived container on plain EC2/docker compose that spawns cronjobs as children).
    """
    own_pid = os.getpid()
    now = time.time()
    running: list[RunningManagementCommand] = []

    for proc in psutil.process_iter(["pid", "cmdline", "create_time"]):
        if proc.info["pid"] == own_pid:
            continue

        cmdline = proc.info["cmdline"] or []
        idx = next((i for i, part in enumerate(cmdline) if "manage.py" in part), None)
        if idx is None or len(cmdline) <= idx + 1:
            continue

        running.append(
            RunningManagementCommand(
                pid=proc.info["pid"],
                cmd_name=cmdline[idx + 1],
                running_seconds=round(now - proc.info["create_time"]),
            )
        )

    return running
