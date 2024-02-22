import os
from rich import print as rich_print


RED = "\33[1m"
DARK_RED = "\x1b[38;5;1m"
BLUE = "\33[94m"
DARK_BLUE = "\x1b[38;5;20m"
GREEN = "\033[32m"
YELLOW = "\033[93m"
PURPLE = "\033[0;35m"
DARK_PURPLE = "\x1b[38;5;92m"
CYAN = "\033[36m"
END = "\033[0m"


_BANNER = """
 ██████╗ █████╗ ██╗     ██████╗ ███████╗██████╗  █████╗
██╔════╝██╔══██╗██║     ██╔══██╗██╔════╝██╔══██╗██╔══██╗
██║     ███████║██║     ██║  ██║█████╗  ██████╔╝███████║
██║     ██╔══██║██║     ██║  ██║██╔══╝  ██╔══██╗██╔══██║
╚██████╗██║  ██║███████╗██████╔╝███████╗██║  ██║██║  ██║
 ╚═════╝╚═╝  ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
"""


_BANNER_SECTION_1 = "\n\
 ██████╗ █████╗ ██╗     ██████╗ ███████╗██████╗  █████╗\n\
██╔════╝██╔══██╗██║     ██╔══██╗██╔════╝██╔══██╗██╔══██╗\n\
"


_BANNER_SECTION_2 = "\
██║     ███████║██║     ██║  ██║█████╗  ██████╔╝███████║\n\
██║     ██╔══██║██║     ██║  ██║██╔══╝  ██╔══██╗██╔══██║\n\
"


BANNER_SECTION_3 = "\
╚██████╗██║  ██║███████╗██████╔╝███████╗██║  ██║██║  ██║\n\
 ╚═════╝╚═╝  ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝\n\
"


def no_color():
    return int(os.environ.get("NO_COLOR", 0)) == 1


if no_color():
    ASCII_BANNER = _BANNER
else:
    ASCII_BANNER = f"{DARK_BLUE}{_BANNER_SECTION_1}{DARK_PURPLE}{_BANNER_SECTION_2}{DARK_RED}{BANNER_SECTION_3}{END}"


def print_rich_banner():
    """Print banner using Python Rich library"""
    if no_color():
        rich_print(f"{_BANNER_SECTION_1}{_BANNER_SECTION_2}{BANNER_SECTION_3}")
    else:
        rich_print(
            f"[blue]{_BANNER_SECTION_1}[/blue][purple]{_BANNER_SECTION_2}[/purple][red]{BANNER_SECTION_3}[/red]"
        )
