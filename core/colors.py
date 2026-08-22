"""The characteristic ManimGL/3Blue1Brown color palette as RGBA tuples."""

from __future__ import annotations


def _rgba(hex_color: str):
    value = hex_color.lstrip("#")
    if len(value) != 6:
        raise ValueError("Expected a six-digit RGB hex color")
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)) + (1.0,)


_PALETTE = {
    "BLUE_E": "#1C758A", "BLUE_D": "#29ABCA", "BLUE_C": "#58C4DD", "BLUE_B": "#9CDCEB", "BLUE_A": "#C7E9F1",
    "TEAL_E": "#49A88F", "TEAL_D": "#55C1A7", "TEAL_C": "#5CD0B3", "TEAL_B": "#76DDC0", "TEAL_A": "#ACEAD7",
    "GREEN_E": "#699C52", "GREEN_D": "#77B05D", "GREEN_C": "#83C167", "GREEN_B": "#A6CF8C", "GREEN_A": "#C9E2AE",
    "YELLOW_E": "#E8C11C", "YELLOW_D": "#F4D345", "YELLOW_C": "#FFFF00", "YELLOW_B": "#FFEA94", "YELLOW_A": "#FFF1B6",
    "GOLD_E": "#C78D46", "GOLD_D": "#E1A158", "GOLD_C": "#F0AC5F", "GOLD_B": "#F9B775", "GOLD_A": "#F7C797",
    "RED_E": "#CF5044", "RED_D": "#E65A4C", "RED_C": "#FC6255", "RED_B": "#FF8080", "RED_A": "#F7A1A3",
    "MAROON_E": "#94424F", "MAROON_D": "#A24D61", "MAROON_C": "#C55F73", "MAROON_B": "#EC92AB", "MAROON_A": "#ECABC1",
    "PURPLE_E": "#644172", "PURPLE_D": "#715582", "PURPLE_C": "#9A72AC", "PURPLE_B": "#B189C6", "PURPLE_A": "#CAA3E8",
    "GREY_E": "#222222", "GREY_D": "#444444", "GREY_C": "#888888", "GREY_B": "#BBBBBB", "GREY_A": "#DDDDDD",
    "WHITE": "#FFFFFF", "BLACK": "#000000", "GREY_BROWN": "#736357", "DARK_BROWN": "#8B4513",
    "LIGHT_BROWN": "#CD853F", "PINK": "#D147BD", "LIGHT_PINK": "#DC75CD", "GREEN_SCREEN": "#00FF00",
    "ORANGE": "#FF862F", "PURE_RED": "#FF0000", "PURE_GREEN": "#00FF00", "PURE_BLUE": "#0000FF",
}

globals().update({name: _rgba(value) for name, value in _PALETTE.items()})

BLUE = BLUE_C
TEAL = TEAL_C
GREEN = GREEN_C
YELLOW = YELLOW_C
GOLD = GOLD_C
RED = RED_C
MAROON = MAROON_C
PURPLE = PURPLE_C
GREY = GREY_C

# Common American-spelling aliases, while preserving ManimGL's GREY names.
GRAY_A, GRAY_B, GRAY_C, GRAY_D, GRAY_E, GRAY = GREY_A, GREY_B, GREY_C, GREY_D, GREY_E, GREY

MANIM_COLORS = tuple(globals()[name] for name in _PALETTE)
COLORMAP_3B1B = (BLUE_E, GREEN, YELLOW, RED)

__all__ = [
    *_PALETTE,
    "BLUE", "TEAL", "GREEN", "YELLOW", "GOLD", "RED", "MAROON", "PURPLE", "GREY",
    "GRAY_A", "GRAY_B", "GRAY_C", "GRAY_D", "GRAY_E", "GRAY",
    "MANIM_COLORS", "COLORMAP_3B1B",
]
