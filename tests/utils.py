import re


def strip_duration_and_seconds(timer_msg: str) -> str:
    """
    For a string like:
        "Finish 'cross-compile doom' in 0:00:00.000002 (0.000002s total)"

    this replaces the wobbly time parts, so it becomes:
        "Finish 'cross-compile doom' in <duration>"
    """

    timer_msg = re.sub(r"(.* in )0:00:.*", r"\1<duration>", timer_msg)
    return timer_msg


def strip_after_seconds(msg: str) -> str:
    """
    For a string like "processing item 1/6 after 0.0s" or "processed all 6 items in 0.0s", this
    replaces the wobbly elapsed-time part, so it becomes "... after <t>s" / "... in <t>s".
    """
    return re.sub(r"(after|in) \d+\.\d+s", r"\1 <t>s", msg)
