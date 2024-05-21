# coding=utf-8
import re


def strip_duration_and_seconds(timer_msg: str) -> str:
    """
    For a string like:
        "Finish 'cross-compile doom' in 0:00:00.000002 (0.000002s total)"

    this replaces the whobbly time parts, so it becomes:
        "Finish 'cross-compile doom' in <duration>"
    """

    timer_msg = re.sub(r"(.* in )0:00:.*", r"\1<duration>", timer_msg)
    return timer_msg
