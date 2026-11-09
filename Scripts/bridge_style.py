# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_style.py
# Colours and font of the bridge windows, shared by the Windows Forms
# windows (bridge_gui.py, IronPython 2.7) and the convergence window
# (aster_convergence_monitor.py, tkinter in Code-Aster's Python 3), so that
# both have the same look. Plain data, no imports: works in 2.7 and 3.

# Font of the windows (Windows default).
FONT = ("Segoe UI", 9.0)

# Colours (R, G, B): calm grey-white with a blue accent colour.
COLOURS = {
    "header_bg": (36, 54, 75),       # dark bar at the top
    "header_fg": (255, 255, 255),
    "header_sub": (190, 202, 216),   # subtitle in the dark bar
    "accent": (31, 111, 178),        # primary button, selection
    "accent_hover": (24, 92, 150),
    "window_bg": (243, 245, 248),
    "page_bg": (255, 255, 255),
    "line": (218, 223, 230),         # borders and separators
    "muted": (96, 106, 120),
    "status_bg": (236, 240, 245),    # status box; hover of a button
    "button_bg": (255, 255, 255),
    "scroll_thumb": (160, 170, 184),  # also the text of a disabled button
    "scroll_thumb_drag": (120, 132, 148),
}


def hex_colour(key):
    """Colour as '#rrggbb' (tkinter)."""
    return "#%02x%02x%02x" % COLOURS[key]
