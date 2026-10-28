# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Documentation check (CPython 3, development tool).

Usage (from the root of the repo):
    python TestFiles/Tools/check_docs.py            # all checks
    python TestFiles/Tools/check_docs.py --parity   # also NL/EN numbers per section

What it checks (output: one line per finding, exit code 1 if there are
findings):
- settings: every key of CONFIG_BRIDGE (also per analysis) is in
  GENERAL_SPECS/ANALYSIS_SPECS (bridge_gui.py) and has a tooltip in
  bridge_glossary.SETTING_HELP in both languages; the default in the tooltip
  ("Standaard x" / "Default x") and in the tables of
  Standaardinstellingen_en_aannames.md (+ EN) equals CONFIG_BRIDGE;
- setting names in the docs (`snake_case` between backticks) exist in the
  code;
- links and anchors (GitHub slugs) between the docs, README and CHANGELOG;
- references KNOWN_BUGS n / KBn exist in KNOWN_BUGS.md (except in a
  sentence with "opgelost"/"fixed"/"solved"/"resolved");
- verification cases (LS-07a, TH-04c, ...) exist in TestFiles/Verificatie;
- "voorbeeld n" / "example n" exists in ASTER_regels_voorbeelden.md (+ EN);
- "§n.m" refers to an existing numbered heading;
- images: in docs/img, alt text, the same images in NL and EN, every file
  in docs/img used, no user folder in an SVG;
- NL/EN parity per pair from bridge_docs.DOCS: headings, tables and rows,
  KNOWN_BUGS numbers, cases, links, `code` words per document.
The bridge itself is not called; the start screen is not opened.
"""
from __future__ import print_function

import ast
import io
import os
import re
import sys
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS = os.path.join(ROOT, "Scripts")
DOCS = os.path.join(ROOT, "docs")
sys.path.insert(0, SCRIPTS)

PROBLEMS = []


def report(where, msg):
    PROBLEMS.append(u"{0}: {1}".format(where, msg))


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def rel(path):
    return os.path.relpath(path, ROOT).replace("\\", "/")


# ------------------------------------------------------------------
# Markdown helpers
# ------------------------------------------------------------------
def strip_code_blocks(text):
    """Replace lines in ``` blocks by empty lines (line numbers are kept)."""
    out, inside = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return "\n".join(out)


def headings(text):
    """[(level, text, line number)] outside code blocks."""
    res = []
    for i, line in enumerate(strip_code_blocks(text).split("\n"), 1):
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            res.append((len(m.group(1)), m.group(2), i))
    return res


def slug(title):
    """GitHub anchor of a heading."""
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", title)   # link -> text
    t = t.replace("`", "").lower()
    out = []
    for ch in t:
        cat = unicodedata.category(ch)
        if ch in " -_" or cat[0] in "LN" or cat == "Mn":
            out.append(ch)
    return "".join(out).replace(" ", "-")


def anchors(text):
    seen, res = {}, set()
    for _lvl, title, _ln in headings(text):
        s = slug(title)
        if s in seen:
            seen[s] += 1
            res.add("{0}-{1}".format(s, seen[s]))
        else:
            seen[s] = 0
            res.add(s)
    for m in re.finditer(r'<a\s+(?:name|id)="([^"]+)"', text):
        res.add(m.group(1))
    return res


def section_numbers(text):
    nums = set()
    for _lvl, title, _ln in headings(text):
        m = re.match(r"(\d+(?:\.\d+)*)\.?\s", title)
        if m:
            nums.add(m.group(1))
    return nums


def md_files():
    files = [os.path.join(ROOT, f) for f in ("README.md", "CHANGELOG.md",
                                             "KNOWN_BUGS.md")]
    for d in (DOCS, os.path.join(DOCS, "en")):
        files += [os.path.join(d, f) for f in sorted(os.listdir(d))
                  if f.endswith(".md")]
    return [f for f in files if os.path.exists(f)]


# ------------------------------------------------------------------
# 1. Settings
# ------------------------------------------------------------------
def _literal(src, name):
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


# Fixed keys per analysis that are not on the start screen
# (Standaardinstellingen §3.1).
FIXED_KEYS = {"template", "solver_command", "type_resu", "phenomene",
              "vibroacoustic", "type_calcul"}


def _norm_value(v):
    """Value from a doc/tooltip -> comparable form."""
    s = v.strip().strip("`*").strip()
    s = s.replace(u"−", "-").replace(u" ", " ")
    low = s.lower()
    if low in ("aan", "on", "true", "ja", "yes"):
        return True
    if low in ("uit", "off", "false", "nee", "no"):
        return False
    m = re.match(r"^(-?\d+(?:[.,]\d+)?(?:e-?\d+)?)\s*(%|s|mb|hz|n|m|m/s|pa|k)?$",
                 low.replace(" ", ""))
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    return s.strip('"')


def _same(doc_value, real):
    d = _norm_value(doc_value)
    if isinstance(real, bool):
        return d is real
    if isinstance(real, (int, float)):
        return isinstance(d, float) and abs(d - float(real)) <= 1e-12 * max(
            1.0, abs(real))
    if isinstance(real, (list, tuple)):
        return True          # do not compare lists (fields)
    if real == "":
        return True          # empty default: described in words
    if isinstance(d, float):  # text value "0" (harm_freq_list)
        d = doc_value.strip().strip("`*").strip()
    return isinstance(d, str) and d.strip('"').lower() == str(real).lower()


def check_settings():
    import bridge_utils as u
    import bridge_glossary as g
    cfg = u.CONFIG_BRIDGE
    gui_src = read(os.path.join(SCRIPTS, "bridge_gui.py"))
    gspecs = {s[0] for s in _literal(gui_src, "GENERAL_SPECS")}
    aspecs = {s[0] for s in _literal(gui_src, "ANALYSIS_SPECS")}
    help_ = g.SETTING_HELP

    # values per key (general + per analysis)
    values = {}
    for k, v in cfg.items():
        if k == "analyses":
            continue
        values.setdefault(k, {})["*"] = v
        if k not in gspecs:
            report("bridge_gui.GENERAL_SPECS", "key missing: " + k)
    for an, ad in cfg["analyses"].items():
        for k, v in ad.items():
            if k in FIXED_KEYS:
                continue
            values.setdefault(k, {})[an] = v
            if k not in aspecs:
                report("bridge_gui.ANALYSIS_SPECS",
                       "key missing: {0} ({1})".format(k, an))
    for k in sorted(gspecs | aspecs):
        if k not in values:
            report("bridge_gui", "spec without CONFIG_BRIDGE key: " + k)

    # tooltips
    for k in sorted(values):
        h = help_.get(k)
        if not h:
            report("bridge_glossary.SETTING_HELP", "no tooltip: " + k)
            continue
        if not (isinstance(h, tuple) and len(h) == 2 and h[0] and h[1]):
            report("bridge_glossary.SETTING_HELP",
                   "tooltip not in both languages: " + k)
            continue
        reals = list(values[k].values())
        for lang, txt, word in (("nl", h[0], u"standaard"),
                                ("en", h[1], u"default")):
            found = [m.group(1) for m in re.finditer(
                r"(?i)(?<![-\w])(?<!Code-Aster )" + word + r"\s+(?:is\s+)?(-?\d+(?:[.,]\d+)?"
                r"(?:e-?\d+)?(?!\w)|[^\s.;,()]+)", txt)]
            # "On/Off by default"
            found += [m.group(1) for m in re.finditer(
                r"(?i)\b(on|off)\s+by\s+default", txt)]
            for val in found:
                if not re.match(r"^[-\w.\"%]+$", val, re.U):
                    continue
                d = _norm_value(val)
                if isinstance(d, bool) and not isinstance(reals[0], bool):
                    continue
                if isinstance(d, str) and not isinstance(reals[0], str):
                    continue          # "Standaard leeg", "Default the ..."
                if isinstance(d, str) and d.lower() in (
                        "de", "het", "een", "the", "a", "an", "per", "in",
                        "leeg", "empty", "voor", "for", "bij", "with",
                        "met", "zoals", "as", "and", "en", "of", "or"):
                    continue
                if not any(_same(val, r) for r in reals):
                    report("tooltip " + k, u"{0}: '{1} {2}' but CONFIG_BRIDGE "
                           u"{3}".format(lang, word, val, values[k]))
    # tables in Standaardinstellingen (+ EN)
    for name, analysis_word in (("Standaardinstellingen_en_aannames.md", None),
                                ("en/Default_settings_and_assumptions.md",
                                 None)):
        path = os.path.join(DOCS, name)
        text = strip_code_blocks(read(path))
        current = "*"
        for i, line in enumerate(text.split("\n"), 1):
            m = re.match(r"^#{2,4}\s.*\(`(\w+)`", line)
            if m and m.group(1) in cfg["analyses"]:
                current = m.group(1)
            elif re.match(r"^##\s", line):
                current = "*"
            if not line.startswith("| `"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2:
                continue
            # only settings (lower case); not Code-Aster words
            keys = re.findall(r"`([a-z]\w*)`", cells[0].split("(")[0])
            dvals = [x.strip() for x in re.split(r"\s/\s|,\s", cells[1])]
            if len(keys) != len(dvals):
                dvals = [cells[1]] * len(keys)
            for key, dv in zip(keys, dvals):
                if key not in values:
                    report("{0}:{1}".format(name, i),
                           "unknown setting `{0}`".format(key))
                    continue
                vals = values[key]
                real = vals.get(current, vals.get("*"))
                if real is None:
                    reals = list(vals.values())
                else:
                    reals = [real]
                dv0 = re.split(r"\s+\(|\s+\[", dv)[0]
                if re.search(r"\d.*\(", dv) or "," in dv0 and re.search(
                        r"\(\w", dv):
                    continue          # "600 (statisch), 1800 (...)"
                if not any(_same(dv0, r) for r in reals):
                    report("{0}:{1}".format(name, i),
                           u"`{0}` default '{1}' but CONFIG_BRIDGE {2}"
                           .format(key, dv, vals))
    return values


# Names outside the code: Mecway API and example names in the text
EXTRA_NAMES = {"node_value", "element_node_value", "verbinding_balk",
               "b_3d_pou", "cqc_array"}


def check_setting_names_in_docs(values):
    """`snake_case` in the docs must occur in the code."""
    code = []
    for d in (SCRIPTS, os.path.join(ROOT, "TestFiles", "Verificatie"),
              os.path.join(ROOT, "TestFiles", "Tools")):
        for f in os.listdir(d):
            if f.endswith((".py", ".comm")):
                code.append(read(os.path.join(d, f)))
    code = "\n".join(code)
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", code))
    for path in md_files():
        full = read(path)
        text = strip_code_blocks(full)
        # names the document itself uses in a code block (selections
        # in an example)
        local = set(w.lower() for w in re.findall(
            r"[A-Za-z_][A-Za-z0-9_]*", "\n".join(
                a for a, b in zip(full.split("\n"), text.split("\n"))
                if a != b)))
        for i, line in enumerate(text.split("\n"), 1):
            for w in re.findall(r"`([a-z][a-z0-9]*_[a-z0-9_]+)`", line):
                # Code-Aster source (`x.py`, catalogue) or own example
                if w in words or w in local or w in EXTRA_NAMES or re.search(
                        r"\.py`|\.F90|catalog", line):
                    continue
                if True:
                    report("{0}:{1}".format(rel(path), i),
                           "`{0}` does not occur in the code".format(w))


# ------------------------------------------------------------------
# 2. Links, anchors, references
# ------------------------------------------------------------------
LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)\)")


def check_links():
    cache = {}
    for path in md_files():
        text = strip_code_blocks(read(path))
        base = os.path.dirname(path)
        for i, line in enumerate(text.split("\n"), 1):
            for m in LINK_RE.finditer(line):
                target = m.group(2)
                if re.match(r"^[a-z]+:", target):
                    continue
                file_part, _, anchor = target.partition("#")
                tpath = os.path.normpath(os.path.join(base, file_part)) \
                    if file_part else path
                if not os.path.exists(tpath):
                    report("{0}:{1}".format(rel(path), i),
                           "link to missing file " + target)
                    continue
                if anchor and tpath.endswith(".md"):
                    if tpath not in cache:
                        cache[tpath] = anchors(read(tpath))
                    if anchor not in cache[tpath]:
                        report("{0}:{1}".format(rel(path), i),
                               "anchor does not exist: " + target)


IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
IMG_DIR = os.path.join(DOCS, "img")
# personal data in an image (the repo is public): a user folder in a path
PRIVATE_RE = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+(?!Public\b)\w", re.I)


def _image_key(path):
    """Image name without a language suffix (_nl / _en), for NL/EN parity."""
    stem, ext = os.path.splitext(os.path.basename(path))
    return re.sub(r"_(nl|en)$", "", stem) + ext


def check_images():
    """Images: the file exists and lies in docs/img, has alt text, NL and EN
    use the same images (a screenshot may differ by _nl/_en), every file in
    docs/img is used, and an SVG contains no user folder."""
    import bridge_docs
    used = set()
    per_doc = {}
    for path in md_files():
        text = strip_code_blocks(read(path))
        base = os.path.dirname(path)
        keys = []
        for i, line in enumerate(text.split("\n"), 1):
            for m in IMG_RE.finditer(line):
                if re.match(r"^[a-z]+:", m.group(2)):
                    continue  # web image (badge in the README)
                where = "{0}:{1}".format(rel(path), i)
                target = os.path.normpath(os.path.join(base, m.group(2)))
                if not m.group(1).strip():
                    report(where, "image without alt text: " + m.group(2))
                if not os.path.exists(target):
                    report(where, "image missing: " + m.group(2))
                    continue
                if os.path.dirname(target) != IMG_DIR:
                    report(where, "image not in docs/img: " + m.group(2))
                used.add(os.path.normcase(target))
                keys.append(_image_key(target))
        per_doc[os.path.normcase(path)] = keys
    for nl_name, en_name, _a, _b in bridge_docs.DOCS:
        nl = per_doc.get(os.path.normcase(os.path.join(DOCS, nl_name)), [])
        en = per_doc.get(os.path.normcase(os.path.join(DOCS, en_name)), [])
        if nl != en:
            report(u"{0} <> {1}".format(nl_name, en_name),
                   u"images differ: NL {0}, EN {1}".format(nl, en))
    if os.path.isdir(IMG_DIR):
        for name in sorted(os.listdir(IMG_DIR)):
            full = os.path.join(IMG_DIR, name)
            if os.path.normcase(full) not in used:
                report("docs/img/" + name, "image not used in any document")
            if name.lower().endswith(".svg") and PRIVATE_RE.search(read(full)):
                report("docs/img/" + name, "user folder in the image")


def known_bug_numbers():
    text = read(os.path.join(ROOT, "KNOWN_BUGS.md"))
    return set(int(n) for n in re.findall(r"^(\d+)\\\.", text, re.M))


KB_RE = re.compile(
    r"(?:KNOWN_BUGS(?:\.md)?|KB)(?:[- ]?(?:punt|punten|item|items))?"
    r"[\s:#]*((?:\d+(?:\s*(?:,|en|and|/|–|-|tot|to)\s*)?)+)")
SOLVED_RE = re.compile(r"opgelost|fixed|solved|resolved|vervallen|removed|"
                       r"verwijderd|was\b", re.I)


def check_known_bugs():
    nums = known_bug_numbers()
    files = md_files() + [os.path.join(SCRIPTS, f)
                          for f in os.listdir(SCRIPTS) if f.endswith(".py")]
    for path in files:
        if path.endswith("CHANGELOG.md"):
            continue          # history: also refers to solved items
        text = read(path)
        for i, line in enumerate(text.split("\n"), 1):
            if path.endswith("KNOWN_BUGS.md"):
                # within KNOWN_BUGS.md: "(item 16)", "items 3 and 4"
                # (the older Dutch wording "punt 16" is accepted too)
                for m in re.finditer(r"\b(?:items?|punt(?:en)?)\s+((?:\d+"
                                     r"(?:\s*(?:,|and|en|/)\s*)?)+)", line):
                    for n in re.findall(r"\d+", m.group(1)):
                        if int(n) not in nums:
                            report("{0}:{1}".format(rel(path), i),
                                   "item {0} does not exist".format(n))
            for m in KB_RE.finditer(line):
                refs = [int(x) for x in re.findall(r"\d+", m.group(1))]
                for n in refs:
                    if n in nums:
                        continue
                    if SOLVED_RE.search(line):
                        continue
                    report("{0}:{1}".format(rel(path), i),
                           "KNOWN_BUGS {0} does not exist".format(n))


CASE_RE = re.compile(r"\b((?:AD|AH|AI|AK|BR|BU|CY|DY|FS|HR|LS|MC|MD|MO|MP|"
                     r"MT|NK|NL|SP|TH|VA|VH|VM|WE|FO|RV|OF|PL)-\d+[a-z]?)\b")


def check_cases():
    vdir = os.path.join(ROOT, "TestFiles", "Verificatie")
    blob = "\n".join(read(os.path.join(vdir, f)) for f in os.listdir(vdir)
                     if f.startswith("tests_") and f.endswith(".py"))
    for path in md_files():
        if path.endswith("CHANGELOG.md"):
            continue
        text = read(path)
        for i, line in enumerate(text.split("\n"), 1):
            for cid in CASE_RE.findall(line):
                # also as a prefix: TH-02d -> TH-02d1, or "MO-2" as a
                # selection for run_verificatie.py
                if not re.search(re.escape(cid), blob):
                    # format "LS-%02d" or "SP-06%s"
                    pref, num = cid.split("-")
                    n = re.match(r"\d+", num).group(0)
                    if re.search(r'"{0}-%0{1}d'.format(pref, len(n)), blob) \
                            or re.search(r'"{0}-{1}%s'.format(pref, n), blob):
                        continue
                    report("{0}:{1}".format(rel(path), i),
                           "verification case {0} not found".format(cid))


def check_examples():
    nl = read(os.path.join(DOCS, "ASTER_regels_voorbeelden.md"))
    en = read(os.path.join(DOCS, "en", "ASTER_lines_examples.md"))
    have_nl = set(re.findall(r"^###\s+Voorbeeld\s+(\d+)", nl, re.M))
    have_en = set(re.findall(r"^###\s+Example\s+(\d+)", en, re.M))
    if have_nl != have_en:
        report("ASTER examples", "NL {0} / EN {1}".format(
            sorted(have_nl - have_en), sorted(have_en - have_nl)))
    for path in md_files():
        text = strip_code_blocks(read(path))
        is_en = "/en/" in path.replace("\\", "/") or path.endswith(
            ("README.md", "CHANGELOG.md"))
        for i, line in enumerate(text.split("\n"), 1):
            for m in re.finditer(r"\b(?:[Vv]oorbeeld(?:en)?|[Ee]xamples?)\s+"
                                 r"(\d+(?:\s*(?:,|en|and|of|or)\s*\d+)*)",
                                 line):
                # only if the line refers to the ASTER lines or is in that
                # document
                if not ("ASTER" in line or "voorbeelden" in path
                        or "examples" in path):
                    continue
                have = have_en if ("Example" in m.group(0) or "example"
                                   in m.group(0)) else have_nl
                for n in re.findall(r"\d+", m.group(1)):
                    if n not in have:
                        report("{0}:{1}".format(rel(path), i),
                               "example {0} does not exist".format(n))


SEC_RE = re.compile(r"§\s?(\d+(?:\.\d+)*)")
# [text with §n](file.md) or [..](file.md) §n / par. n
SEC_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s#]*\.md)(?:#[^)]*)?\)"
                         r"((?:[\s,]*(?:§\s?|par\.\s)\d+(?:\.\d+)*)*)")


def check_section_refs():
    """Only references attached to a link to a .md (a bare § can also be
    the Mecway manual or a U document)."""
    cache = {}
    for path in md_files():
        text = strip_code_blocks(read(path))
        base = os.path.dirname(path)
        for i, line in enumerate(text.split("\n"), 1):
            for m in SEC_LINK_RE.finditer(line):
                target = os.path.normpath(os.path.join(base, m.group(2)))
                if not os.path.exists(target):
                    continue
                refs = SEC_RE.findall(m.group(1)) + re.findall(
                    r"(\d+(?:\.\d+)*)", m.group(3))
                if target not in cache:
                    cache[target] = section_numbers(read(target))
                for r in refs:
                    if r not in cache[target]:
                        report("{0}:{1}".format(rel(path), i),
                               u"§{0} does not exist in {1}".format(
                                   r, rel(target)))


# ------------------------------------------------------------------
# 3. NL/EN parity
# ------------------------------------------------------------------
def _tables(text):
    """[(line number, number of rows)] of the tables."""
    res, start, rows = [], None, 0
    for i, line in enumerate(strip_code_blocks(text).split("\n"), 1):
        if re.match(r"^\|[\s:-]", line):
            if start is None:
                start, rows = i, 0
            rows += 1
        elif start is not None:
            res.append((start, rows))
            start = None
    if start is not None:
        res.append((start, rows))
    return res


def _sections(text):
    """Text per heading (in order)."""
    out, cur, buf = [], None, []
    for line in strip_code_blocks(text).split("\n"):
        if re.match(r"^#{1,6}\s", line):
            out.append((cur, "\n".join(buf)))
            cur, buf = line, []
        else:
            buf.append(line)
    out.append((cur, "\n".join(buf)))
    return out


def _numbers(text, lang):
    """Numbers as values (NL: 0,66 and 20 169; EN: 0.66 and 20,169)."""
    t = re.sub(r"`[^`]*`|\([^)]*\.md[^)]*\)|\[[^\]]*\]", " ", text)
    t = re.sub(r"(?<=\d)[ \xa0\u202f](?=\d{3}\b)", "", t)
    if lang == "nl":
        t = re.sub(r"(?<=\d),(?=\d)", ".", t)
    else:
        t = re.sub(r"(?<=\d),(?=\d{3})", "", t)
    nums = re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?(?:e-?\d+)?", t)
    out = []
    for n in nums:
        try:
            out.append(repr(abs(float(n))))
        except ValueError:
            pass
    return sorted(out)


def check_parity(numbers):
    import bridge_docs
    for nl_name, en_name, _a, _b in bridge_docs.DOCS:
        nl = read(os.path.join(DOCS, nl_name))
        en = read(os.path.join(DOCS, en_name))
        where = u"{0} <> {1}".format(nl_name, en_name)
        hn, he = headings(nl), headings(en)
        if [h[0] for h in hn] != [h[0] for h in he]:
            report(where, "headings differ: NL {0}, EN {1}".format(
                len(hn), len(he)))
            for a, b in zip(hn, he):
                if a[0] != b[0]:
                    report(where, u"first difference NL r{0} '{1}' / EN r{2} "
                           u"'{3}'".format(a[2], a[1], b[2], b[1]))
                    break
        else:
            for a, b in zip(hn, he):
                na = re.match(r"(\d+(?:\.\d+)*)", a[1])
                nb = re.match(r"(\d+(?:\.\d+)*)", b[1])
                if (na and na.group(1)) != (nb and nb.group(1)):
                    report(where, u"heading number NL r{0} '{1}' / EN r{2} '{3}'"
                           .format(a[2], a[1], b[2], b[1]))
        tn, te = _tables(nl), _tables(en)
        if [t[1] for t in tn] != [t[1] for t in te]:
            for a, b in zip(tn, te):
                if a[1] != b[1]:
                    report(where, "table NL r{0} {1} rows / EN r{2} {3} rows"
                           .format(a[0], a[1], b[0], b[1]))
                    break
            if len(tn) != len(te):
                report(where, "number of tables NL {0} / EN {1}".format(
                    len(tn), len(te)))
        for label, rx in (("KNOWN_BUGS", r"(?:KNOWN_BUGS|KB)\s*(\d+)"),
                          ("case", CASE_RE.pattern)):
            a, b = set(re.findall(rx, nl)), set(re.findall(rx, en))
            if a != b:
                report(where, u"{0}: only NL {1}, only EN {2}".format(
                    label, sorted(a - b), sorted(b - a)))
        # links: map targets to their pair
        pair = {}
        for x in bridge_docs.DOCS:
            pair[os.path.basename(x[0])] = os.path.basename(x[1])
        ln = set()
        for m in LINK_RE.finditer(strip_code_blocks(nl)):
            f = os.path.basename(m.group(2).partition("#")[0])
            ln.add(pair.get(f, f))
        le = set(os.path.basename(m.group(2).partition("#")[0])
                 for m in LINK_RE.finditer(strip_code_blocks(en)))
        ln.discard(os.path.basename(en_name)); le.discard(
            os.path.basename(nl_name))
        ln.discard(""); le.discard("")
        if ln != le:
            report(where, u"links: only NL {0}, only EN {1}".format(
                sorted(ln - le), sorted(le - ln)))
        if numbers:
            sn, se = _sections(nl), _sections(en)
            if len(sn) == len(se):
                for (h1, t1), (h2, t2) in zip(sn, se):
                    a, b = _numbers(t1, "nl"), _numbers(t2, "en")
                    if a != b:
                        from collections import Counter
                        ca, cb = Counter(a), Counter(b)
                        report(where, u"numbers in '{0}': only NL {1}, "
                               u"only EN {2}".format(
                                   (h1 or "")[:50],
                                   sorted((ca - cb).elements())[:12],
                                   sorted((cb - ca).elements())[:12]))


# ------------------------------------------------------------------
# 4. Start screen labels in the docs
# ------------------------------------------------------------------
def check_labels():
    """A label between *..* (NL) or "..." (EN) that is almost equal to a
    start screen label must be exactly equal to it."""
    import difflib
    src = read(os.path.join(SCRIPTS, "bridge_gui.py"))
    labels = {"nl": set(), "en": set()}
    for name in ("GENERAL_SPECS", "ANALYSIS_SPECS"):
        for _k, lab, _kind, _x in _literal(src, name):
            nl, en = lab if isinstance(lab, tuple) else (lab, lab)
            labels["nl"].add(nl)
            labels["en"].add(en)
    for path in md_files():
        p = path.replace("\\", "/")
        lang = "en" if ("/en/" in p or p.endswith("README.md")) else "nl"
        if p.endswith(("CHANGELOG.md", "KNOWN_BUGS.md")):
            continue
        rx = r'"([^"]{6,90})"' if lang == "en" else \
            r"(?<![*\w])\*([^*]{6,90})\*(?![*\w])"
        text = strip_code_blocks(read(path))
        for i, line in enumerate(text.split("\n"), 1):
            for m in re.finditer(rx, line):
                q = m.group(1).strip()
                # shortened label (without unit or explanation) is fine
                if q in labels[lang] or any(l.startswith(q) for l in
                                            labels[lang]):
                    continue
                best = difflib.get_close_matches(q, labels[lang], 1, 0.75)
                if best:
                    report("{0}:{1}".format(rel(path), i),
                           u"label '{0}' differs from the start screen '{1}'"
                           .format(q, best[0]))


def main():
    numbers = "--parity" in sys.argv
    values = check_settings()
    check_setting_names_in_docs(values)
    check_links()
    check_images()
    check_known_bugs()
    check_cases()
    check_examples()
    check_section_refs()
    check_parity(numbers)
    check_labels()
    for p in PROBLEMS:
        print(p)
    print("{0} finding(s)".format(len(PROBLEMS)))
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
