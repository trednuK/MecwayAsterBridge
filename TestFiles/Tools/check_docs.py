# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Controle van de documentatie (CPython 3, ontwikkelgereedschap).

Gebruik (vanuit de hoofdmap van de repo):
    python TestFiles/Tools/check_docs.py            # alle controles
    python TestFiles/Tools/check_docs.py --parity   # ook NL/EN-getallen per sectie

Wat het controleert (uitvoer: een regel per bevinding, exitcode 1 als er
bevindingen zijn):
- instellingen: elke sleutel van CONFIG_BRIDGE (ook per analyse) staat in
  GENERAL_SPECS/ANALYSIS_SPECS (bridge_gui.py) en heeft een tooltip in
  bridge_glossary.SETTING_HELP in beide talen; de standaard in de tooltip
  ("Standaard x" / "Default x") en in de tabellen van
  Standaardinstellingen_en_aannames.md (+ EN) is gelijk aan CONFIG_BRIDGE;
- instellingsnamen in de docs (`snake_case` tussen backticks) bestaan in de
  code;
- links en ankers (GitHub-slugs) tussen de docs, README en CHANGELOG;
- verwijzingen KNOWN_BUGS n / KBn bestaan in KNOWN_BUGS.md (behalve in een
  zin met "opgelost"/"fixed"/"solved"/"resolved");
- verificatiecases (LS-07a, TH-04c, ...) bestaan in TestFiles/Verificatie;
- "voorbeeld n" / "example n" bestaat in ASTER_regels_voorbeelden.md (+ EN);
- "§n.m" verwijst naar een bestaande genummerde kop;
- NL/EN-pariteit per paar uit bridge_docs.DOCS: koppen, tabellen en rijen,
  KNOWN_BUGS-nummers, cases, links, `code`-woorden per document.
De bridge zelf wordt niet aangeroepen; het startscherm wordt niet geopend.
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
# Markdown-hulpjes
# ------------------------------------------------------------------
def strip_code_blocks(text):
    """Vervang regels in ``` blokken door lege regels (regelnummers blijven)."""
    out, inside = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return "\n".join(out)


def headings(text):
    """[(niveau, tekst, regelnummer)] buiten codeblokken."""
    res = []
    for i, line in enumerate(strip_code_blocks(text).split("\n"), 1):
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            res.append((len(m.group(1)), m.group(2), i))
    return res


def slug(title):
    """GitHub-anker van een kop."""
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", title)   # link -> tekst
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
# 1. Instellingen
# ------------------------------------------------------------------
def _literal(src, name):
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


# Vaste sleutels per analyse die niet op het startscherm staan
# (Standaardinstellingen §3.1).
FIXED_KEYS = {"template", "solver_command", "type_resu", "phenomene",
              "vibroacoustic", "type_calcul"}


def _norm_value(v):
    """Waarde uit een doc/tooltip -> vergelijkbare vorm."""
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
        return True          # lijsten (fields) niet vergelijken
    if real == "":
        return True          # lege standaard: beschrijving in woorden
    if isinstance(d, float):  # tekstwaarde "0" (harm_freq_list)
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

    # waarden per sleutel (algemeen + per analyse)
    values = {}
    for k, v in cfg.items():
        if k == "analyses":
            continue
        values.setdefault(k, {})["*"] = v
        if k not in gspecs:
            report("bridge_gui.GENERAL_SPECS", "sleutel ontbreekt: " + k)
    for an, ad in cfg["analyses"].items():
        for k, v in ad.items():
            if k in FIXED_KEYS:
                continue
            values.setdefault(k, {})[an] = v
            if k not in aspecs:
                report("bridge_gui.ANALYSIS_SPECS",
                       "sleutel ontbreekt: {0} ({1})".format(k, an))
    for k in sorted(gspecs | aspecs):
        if k not in values:
            report("bridge_gui", "spec zonder CONFIG_BRIDGE-sleutel: " + k)

    # tooltips
    for k in sorted(values):
        h = help_.get(k)
        if not h:
            report("bridge_glossary.SETTING_HELP", "geen tooltip: " + k)
            continue
        if not (isinstance(h, tuple) and len(h) == 2 and h[0] and h[1]):
            report("bridge_glossary.SETTING_HELP",
                   "tooltip niet in beide talen: " + k)
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
                    report("tooltip " + k, u"{0}: '{1} {2}' maar CONFIG_BRIDGE "
                           u"{3}".format(lang, word, val, values[k]))
    # tabellen in Standaardinstellingen (+ EN)
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
            # alleen instellingen (kleine letters); Code-Aster-woorden niet
            keys = re.findall(r"`([a-z]\w*)`", cells[0].split("(")[0])
            dvals = [x.strip() for x in re.split(r"\s/\s|,\s", cells[1])]
            if len(keys) != len(dvals):
                dvals = [cells[1]] * len(keys)
            for key, dv in zip(keys, dvals):
                if key not in values:
                    report("{0}:{1}".format(name, i),
                           "onbekende instelling `{0}`".format(key))
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
                           u"`{0}` standaard '{1}' maar CONFIG_BRIDGE {2}"
                           .format(key, dv, vals))
    return values


# Namen buiten de code: Mecway-API en voorbeeldnamen in de tekst
EXTRA_NAMES = {"node_value", "element_node_value", "verbinding_balk",
               "b_3d_pou", "cqc_array"}


def check_setting_names_in_docs(values):
    """`snake_case` in de docs moet in de code voorkomen."""
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
        # namen die het document zelf in een codeblok gebruikt (selecties
        # in een voorbeeld)
        local = set(w.lower() for w in re.findall(
            r"[A-Za-z_][A-Za-z0-9_]*", "\n".join(
                a for a, b in zip(full.split("\n"), text.split("\n"))
                if a != b)))
        for i, line in enumerate(text.split("\n"), 1):
            for w in re.findall(r"`([a-z][a-z0-9]*_[a-z0-9_]+)`", line):
                # Code-Aster-bron (`x.py`, catalogus) of eigen voorbeeld
                if w in words or w in local or w in EXTRA_NAMES or re.search(
                        r"\.py`|\.F90|catalog", line):
                    continue
                if True:
                    report("{0}:{1}".format(rel(path), i),
                           "`{0}` komt niet voor in de code".format(w))


# ------------------------------------------------------------------
# 2. Links, ankers, verwijzingen
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
                           "link naar ontbrekend bestand " + target)
                    continue
                if anchor and tpath.endswith(".md"):
                    if tpath not in cache:
                        cache[tpath] = anchors(read(tpath))
                    if anchor not in cache[tpath]:
                        report("{0}:{1}".format(rel(path), i),
                               "anker bestaat niet: " + target)


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
            continue          # historie: verwijst ook naar opgeloste punten
        text = read(path)
        for i, line in enumerate(text.split("\n"), 1):
            if path.endswith("KNOWN_BUGS.md"):
                # binnen KNOWN_BUGS.md: "(punt 16)"
                for m in re.finditer(r"\bpunt(?:en)?\s+((?:\d+(?:\s*(?:,|en|/)"
                                     r"\s*)?)+)", line):
                    for n in re.findall(r"\d+", m.group(1)):
                        if int(n) not in nums:
                            report("{0}:{1}".format(rel(path), i),
                                   "punt {0} bestaat niet".format(n))
            for m in KB_RE.finditer(line):
                refs = [int(x) for x in re.findall(r"\d+", m.group(1))]
                for n in refs:
                    if n in nums:
                        continue
                    if SOLVED_RE.search(line):
                        continue
                    report("{0}:{1}".format(rel(path), i),
                           "KNOWN_BUGS {0} bestaat niet".format(n))


CASE_RE = re.compile(r"\b((?:AD|AH|AI|AK|BR|BU|CY|DY|FS|HR|LS|MC|MD|MO|MP|"
                     r"MT|NK|NL|SP|TH|VA|VH|VM|WE|FO|RV|OF)-\d+[a-z]?)\b")


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
                # ook als voorvoegsel: TH-02d -> TH-02d1, of "MO-2" als
                # selectie voor run_verificatie.py
                if not re.search(re.escape(cid), blob):
                    # formaat "LS-%02d" of "SP-06%s"
                    pref, num = cid.split("-")
                    n = re.match(r"\d+", num).group(0)
                    if re.search(r'"{0}-%0{1}d'.format(pref, len(n)), blob) \
                            or re.search(r'"{0}-{1}%s'.format(pref, n), blob):
                        continue
                    report("{0}:{1}".format(rel(path), i),
                           "verificatiecase {0} niet gevonden".format(cid))


def check_examples():
    nl = read(os.path.join(DOCS, "ASTER_regels_voorbeelden.md"))
    en = read(os.path.join(DOCS, "en", "ASTER_lines_examples.md"))
    have_nl = set(re.findall(r"^###\s+Voorbeeld\s+(\d+)", nl, re.M))
    have_en = set(re.findall(r"^###\s+Example\s+(\d+)", en, re.M))
    if have_nl != have_en:
        report("ASTER-voorbeelden", "NL {0} / EN {1}".format(
            sorted(have_nl - have_en), sorted(have_en - have_nl)))
    for path in md_files():
        text = strip_code_blocks(read(path))
        is_en = "/en/" in path.replace("\\", "/") or path.endswith(
            ("README.md", "CHANGELOG.md"))
        for i, line in enumerate(text.split("\n"), 1):
            for m in re.finditer(r"\b(?:[Vv]oorbeeld(?:en)?|[Ee]xamples?)\s+"
                                 r"(\d+(?:\s*(?:,|en|and|of|or)\s*\d+)*)",
                                 line):
                # alleen als de regel naar de ASTER-regels verwijst of in dat
                # document staat
                if not ("ASTER" in line or "voorbeelden" in path
                        or "examples" in path):
                    continue
                have = have_en if ("Example" in m.group(0) or "example"
                                   in m.group(0)) else have_nl
                for n in re.findall(r"\d+", m.group(1)):
                    if n not in have:
                        report("{0}:{1}".format(rel(path), i),
                               "voorbeeld {0} bestaat niet".format(n))


SEC_RE = re.compile(r"§\s?(\d+(?:\.\d+)*)")
# [tekst met §n](bestand.md) of [..](bestand.md) §n / par. n
SEC_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s#]*\.md)(?:#[^)]*)?\)"
                         r"((?:[\s,]*(?:§\s?|par\.\s)\d+(?:\.\d+)*)*)")


def check_section_refs():
    """Alleen verwijzingen die aan een link naar een .md hangen (een kale
    § kan ook de Mecway-handleiding of een U-document zijn)."""
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
                               u"§{0} bestaat niet in {1}".format(
                                   r, rel(target)))


# ------------------------------------------------------------------
# 3. NL/EN-pariteit
# ------------------------------------------------------------------
def _tables(text):
    """[(regelnummer, aantal rijen)] van de tabellen."""
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
    """Tekst per kop (op volgorde)."""
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
    """Getallen als waarde (NL: 0,66 en 20 169; EN: 0.66 en 20,169)."""
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
            report(where, "koppen verschillen: NL {0}, EN {1}".format(
                len(hn), len(he)))
            for a, b in zip(hn, he):
                if a[0] != b[0]:
                    report(where, u"eerste afwijking NL r{0} '{1}' / EN r{2} "
                           u"'{3}'".format(a[2], a[1], b[2], b[1]))
                    break
        else:
            for a, b in zip(hn, he):
                na = re.match(r"(\d+(?:\.\d+)*)", a[1])
                nb = re.match(r"(\d+(?:\.\d+)*)", b[1])
                if (na and na.group(1)) != (nb and nb.group(1)):
                    report(where, u"kopnummer NL r{0} '{1}' / EN r{2} '{3}'"
                           .format(a[2], a[1], b[2], b[1]))
        tn, te = _tables(nl), _tables(en)
        if [t[1] for t in tn] != [t[1] for t in te]:
            for a, b in zip(tn, te):
                if a[1] != b[1]:
                    report(where, "tabel NL r{0} {1} rijen / EN r{2} {3} rijen"
                           .format(a[0], a[1], b[0], b[1]))
                    break
            if len(tn) != len(te):
                report(where, "aantal tabellen NL {0} / EN {1}".format(
                    len(tn), len(te)))
        for label, rx in (("KNOWN_BUGS", r"(?:KNOWN_BUGS|KB)\s*(\d+)"),
                          ("case", CASE_RE.pattern)):
            a, b = set(re.findall(rx, nl)), set(re.findall(rx, en))
            if a != b:
                report(where, u"{0}: alleen NL {1}, alleen EN {2}".format(
                    label, sorted(a - b), sorted(b - a)))
        # links: doelen naar paar vertalen
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
            report(where, u"links: alleen NL {0}, alleen EN {1}".format(
                sorted(ln - le), sorted(le - ln)))
        if numbers:
            sn, se = _sections(nl), _sections(en)
            if len(sn) == len(se):
                for (h1, t1), (h2, t2) in zip(sn, se):
                    a, b = _numbers(t1, "nl"), _numbers(t2, "en")
                    if a != b:
                        from collections import Counter
                        ca, cb = Counter(a), Counter(b)
                        report(where, u"getallen in '{0}': alleen NL {1}, "
                               u"alleen EN {2}".format(
                                   (h1 or "")[:50],
                                   sorted((ca - cb).elements())[:12],
                                   sorted((cb - ca).elements())[:12]))


# ------------------------------------------------------------------
# 4. Labels van het startscherm in de docs
# ------------------------------------------------------------------
def check_labels():
    """Een label tussen *..* (NL) of "..." (EN) dat bijna gelijk is aan een
    label van het startscherm, moet er precies gelijk aan zijn."""
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
                # ingekort label (zonder eenheid of toelichting) is goed
                if q in labels[lang] or any(l.startswith(q) for l in
                                            labels[lang]):
                    continue
                best = difflib.get_close_matches(q, labels[lang], 1, 0.75)
                if best:
                    report("{0}:{1}".format(rel(path), i),
                           u"label '{0}' wijkt af van het startscherm '{1}'"
                           .format(q, best[0]))


def main():
    numbers = "--parity" in sys.argv
    values = check_settings()
    check_setting_names_in_docs(values)
    check_links()
    check_known_bugs()
    check_cases()
    check_examples()
    check_section_refs()
    check_parity(numbers)
    check_labels()
    for p in PROBLEMS:
        print(p)
    print("{0} bevinding(en)".format(len(PROBLEMS)))
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
