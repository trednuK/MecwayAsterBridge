# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of images and HTML comments on the Documentation page
# (bridge_docs.markdown_to_html): an image becomes a data URI (the page is
# loaded as about:blank), a missing image shows its alt text, a comment
# such as <!-- FIGURE: ... --> is not shown, and links still work.
#
#   python tests/test_bridge_docs_images.py

from __future__ import print_function

import base64
import io
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_docs as d  # noqa: E402

FAILED = []


def check(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        FAILED.append(name)


def main():
    tmp = tempfile.mkdtemp(prefix="mab_docimg_")
    try:
        os.makedirs(os.path.join(tmp, "img"))
        os.makedirs(os.path.join(tmp, "en"))
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'
        f = io.open(os.path.join(tmp, "img", "a.svg"), "wb")
        f.write(svg)
        f.close()
        text = (u"# Title\n\n![Axis *r* and z](../img/a.svg)\n\n"
                u"1. marker one\n\n<!-- FIGURE: page Static,\n markers -->\n"
                u"See [the guide](UserGuide.md) and ![gone](../img/none.png)."
                u"\n\n| a | ![t](../img/a.svg) |\n|---|---|\n| 1 | 2 |\n")
        html = d.markdown_to_html(text, u"t", os.path.join(tmp, "en"))
        data = base64.b64encode(svg).decode("ascii")
        check("svg as data URI",
              u'src="data:image/svg+xml;base64,{0}"'.format(data) in html)
        check("alt text escaped, no italic markup in alt",
              u'alt="Axis *r* and z"' in html)
        check("image in a table cell too", html.count(u"data:image/svg") == 2)
        check("missing image shows alt text", u"[gone]" in html)
        check("comment left out", u"FIGURE" not in html)
        check("link still a link", u'<a href="UserGuide.md">' in html)
        check("numbered list kept", u"<ol><li>\nmarker one" in html)
        plain = d.markdown_to_html(u"![x](img/a.svg)", u"t")
        check("without base_dir: alt text only",
              u"<img" not in plain and u"x" in plain)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("{0} failure(s)".format(len(FAILED)))
    return 1 if FAILED else 0


if main():
    sys.exit(1)
