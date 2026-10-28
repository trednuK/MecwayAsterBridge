# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Numbered markers on a screenshot for the documentation (IronPython with
# System.Drawing, no extra packages). Each marker is a red circle with a
# white number, the same style as the markers in the SVG schematics
# (docs/img, #c0392b); the text that explains a number goes in the
# numbered list below the image in the document, not in the image.
#
# usage (Mecway's IronPython via run_ipy.ps1):
#   powershell -File TestFiles/Tools/run_ipy.ps1 -Script TestFiles/Tools/annotate.py
#       -ScriptArgs in.png,out.png,[crop=x:y:w:h],[box=x:y:w:h],x:y,x:y,...
# Markers are numbered 1, 2, ... in the order of the x:y points (pixels of
# the input image). crop= cuts the image first (marker and box
# coordinates stay in input pixels); box= draws a red rectangle around an
# area. A point x:y:n uses number n instead of the next one.
import sys

import clr
clr.AddReference("System.Drawing")
from System.Drawing import (Bitmap, Graphics, Pen, SolidBrush, Color, Font,
                            FontStyle, StringFormat, StringAlignment,
                            RectangleF, Rectangle, GraphicsUnit)
from System.Drawing.Drawing2D import SmoothingMode
from System.Drawing.Text import TextRenderingHint
from System.Drawing.Imaging import ImageFormat

RED = Color.FromArgb(0xC0, 0x39, 0x2B)
RADIUS = 13


def _nums(text):
    return [int(float(v)) for v in text.split(":")]


def main(args):
    if len(args) < 3:
        print(__doc__ or "usage: annotate.py in.png out.png x:y ...")
        return 2
    src, dst = args[0], args[1]
    crop = None
    boxes, points = [], []
    n = 0
    for a in args[2:]:
        if a.startswith("crop="):
            crop = _nums(a[5:])
        elif a.startswith("box="):
            boxes.append(_nums(a[4:]))
        else:
            v = _nums(a)
            n = v[2] if len(v) > 2 else n + 1
            points.append((v[0], v[1], n))
    image = Bitmap(src)
    ox, oy = 0, 0
    if crop:
        ox, oy = crop[0], crop[1]
        cut = Bitmap(crop[2], crop[3])
        g = Graphics.FromImage(cut)
        g.DrawImage(image, Rectangle(0, 0, crop[2], crop[3]),
                    Rectangle(crop[0], crop[1], crop[2], crop[3]),
                    GraphicsUnit.Pixel)
        g.Dispose()
        image.Dispose()
        image = cut
    else:
        # copy, so the input file is not locked while saving over it
        copy = Bitmap(image)
        image.Dispose()
        image = copy
    g = Graphics.FromImage(image)
    g.SmoothingMode = SmoothingMode.AntiAlias
    g.TextRenderingHint = TextRenderingHint.AntiAliasGridFit
    pen = Pen(RED, 2.5)
    for x, y, w, h in boxes:
        g.DrawRectangle(pen, x - ox, y - oy, w, h)
    brush = SolidBrush(RED)
    white = SolidBrush(Color.White)
    edge = Pen(Color.White, 2.0)
    font = Font("Segoe UI", 11.0, FontStyle.Bold, GraphicsUnit.Pixel)
    fmt = StringFormat()
    fmt.Alignment = StringAlignment.Center
    fmt.LineAlignment = StringAlignment.Center
    for x, y, k in points:
        cx, cy = x - ox, y - oy
        g.FillEllipse(brush, cx - RADIUS, cy - RADIUS, 2 * RADIUS, 2 * RADIUS)
        g.DrawEllipse(edge, cx - RADIUS, cy - RADIUS, 2 * RADIUS, 2 * RADIUS)
        g.DrawString(str(k), font, white,
                     RectangleF(cx - RADIUS, cy - RADIUS + 0.5,
                                2 * RADIUS, 2 * RADIUS), fmt)
    g.Dispose()
    image.Save(dst, ImageFormat.Png)
    image.Dispose()
    print("annotate: {0} marker(s), {1} box(es) -> {2}".format(
        len(points), len(boxes), dst))
    return 0


sys.exit(main(sys.argv[1:]))
