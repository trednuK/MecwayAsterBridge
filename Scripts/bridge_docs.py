# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_docs.py
# Documentatie in het hoofdvenster (bridge_gui, pagina "Documentatie"):
# de lijst met documenten in docs/ (of docs/en/) en een eenvoudige omzetting
# van Markdown naar HTML voor het ingebouwde browserelement. Plus de
# woordenlijst (bridge_glossary) als HTML-pagina.
#
# De omzetting kent alleen wat in docs/ gebruikt wordt: koppen (#..####),
# alinea's, opsommingen (-, *, 1.) met inspringing, tabellen (| a | b |),
# codeblokken (```), inline code, vet/cursief, links en horizontale lijnen.
# Geen pip-pakketten (AGENTS.md). Compatibel met IronPython 2.7.9 en
# Python 3.

import io
import os
import re

import bridge_glossary

# Volgorde in de lijst: (bestand nl, bestand en, titel nl, titel en)
DOCS = [
    ("Handleiding.md", "en/UserGuide.md", u"Handleiding", u"User guide"),
    ("Mecway_functionaliteit.md", "en/Mecway_features.md",
     u"Mecway-functionaliteit: wat wel en niet",
     u"Mecway features: what is and is not translated"),
    ("Standaardinstellingen_en_aannames.md",
     "en/Default_settings_and_assumptions.md",
     u"Standaardinstellingen en aannames",
     u"Default settings and assumptions"),
    ("Instellingen_contact_en_nietlineair.md",
     "en/Settings_contact_and_nonlinear.md",
     u"Instellingen contact en niet-lineair",
     u"Settings contact and nonlinear"),
    ("Bezwijken.md", "en/Failure.md", u"Bezwijken van elementen",
     u"Element failure"),
    ("Thermisch.md", "en/Thermal.md", u"Thermische analyses",
     u"Thermal analyses"),
    ("Lassen.md", "en/Welding.md", u"Lassen: warmtebron en restspanning",
     u"Welding: heat source and residual stress"),
    ("Modaal_en_knik.md", "en/Modal_and_buckling.md",
     u"Modale analyse en knik", u"Modal analysis and buckling"),
    ("Respons_op_modale_basis.md", "en/Mode_superposition.md",
     u"Respons op modale basis (D30) en harmonisch",
     u"Mode superposition (D30) and harmonic"),
    ("Akoestiek.md", "en/Acoustics.md", u"Akoestiek (holtemodes, "
     u"harmonisch, vibro-akoestiek)", u"Acoustics (cavity modes, harmonic, "
     u"vibroacoustics)"),
    ("Spectrumanalyse.md", "en/Response_spectrum.md",
     u"Responsspectrum (aardbeving, schok)",
     u"Response spectrum (earthquake, shock)"),
    ("Foutschatter.md", "en/Error_estimator.md",
     u"Foutschatter (discretisatiefout)",
     u"Error estimator (discretisation error)"),
    ("Breukmechanica.md", "en/Fracture_mechanics.md",
     u"Breukmechanica (K en G langs een scheur)",
     u"Fracture mechanics (K and G along a crack)"),
    ("Vermoeiing.md", "en/Fatigue.md",
     u"Vermoeiing (schade en levensduur, Miner)",
     u"Fatigue (damage and life, Miner)"),
    ("ASTER_regels_voorbeelden.md", "en/ASTER_lines_examples.md",
     u"#ASTER-regels met voorbeelden", u"#ASTER lines with examples"),
    ("Foutmeldingen_CodeAster.md", "en/CodeAster_error_messages.md",
     u"Foutmeldingen van Code-Aster", u"Code-Aster error messages"),
    ("Verificatie.md", "en/Verification.md",
     u"Verificatie (FEM tegen analytisch)",
     u"Verification (FEM vs analytical)"),
]

GLOSSARY_PAGE = "woordenlijst"     # pseudo-bestand voor de woordenlijst

# Merkenvermelding onderaan de pagina Documentatie (bridge_gui); dezelfde
# tekst staat in README.md, docs/Handleiding.md en docs/en/UserGuide.md.
TRADEMARK_NOTICE = (
    u"Mecway is een product van Mecway Ltd. Code_Aster is een handelsmerk "
    u"van EDF. Dit project is niet verbonden aan en niet goedgekeurd door "
    u"Mecway Ltd of EDF.",
    u"Mecway is a product of Mecway Ltd. Code_Aster is a trademark of EDF. "
    u"This project is not affiliated with or endorsed by Mecway Ltd or EDF.")

_CSS = (u"body{font-family:Segoe UI,Arial,sans-serif;font-size:10pt;"
        u"margin:12px 18px;color:#1f2933;line-height:1.45}"
        u"h1{font-size:16pt;color:#24364b}"
        u"h2{font-size:13pt;color:#24364b;border-bottom:2px solid #dadfe6;"
        u"padding-bottom:2px;margin-top:18px}"
        u"h3{font-size:11pt;color:#1f6fb2}h4{font-size:10pt}"
        u"a{color:#1f6fb2}"
        u"table{border-collapse:collapse;margin:8px 0}"
        u"td,th{border:1px solid #dadfe6;padding:4px 8px;vertical-align:top}"
        u"th{background:#eef2f6;text-align:left}"
        u"code{background:#eef2f6;padding:0 3px;"
        u"font-family:Consolas,monospace}"
        u"pre{background:#f3f5f8;border-left:3px solid #1f6fb2;padding:8px;"
        u"font-family:Consolas,monospace;white-space:pre-wrap}"
        u"dt{font-weight:bold;margin-top:8px;color:#24364b}"
        u"dd{margin-left:18px}")


def docs_dir():
    """docs/ naast de map Scripts/."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "docs")


def doc_list(tr):
    """[(titel, relatief pad of GLOSSARY_PAGE)] in de gekozen taal."""
    items = [(tr(u"Uitleg van codes en namen (woordenlijst)",
                 u"Explanation of codes and names (glossary)"),
              GLOSSARY_PAGE)]
    for nl, en, tnl, ten in DOCS:
        items.append((tr(tnl, ten), tr(nl, en)))
    return items


# ==========================================
# MARKDOWN -> HTML
# ==========================================
def _esc(text):
    return (text.replace(u"&", u"&amp;").replace(u"<", u"&lt;")
            .replace(u">", u"&gt;"))


_CODE_RE = re.compile(u"`([^`]+)`")
_LINK_RE = re.compile(u"\\[([^\\]]+)\\]\\(([^)\\s]+)\\)")
_BOLD_RE = re.compile(u"\\*\\*(.+?)\\*\\*")
_ITAL_RE = re.compile(u"(?<![\\w*])\\*([^*\\s][^*]*?)\\*(?![\\w*])")


def _inline(text):
    """Inline-opmaak: code, links, vet, cursief. Code eerst als
    plaatshouder, zodat * in code niet als cursief telt en vet of een link
    om code heen ook werkt (**`x`-regel**, [`a.md`](a.md))."""
    codes = []

    def keep(m):
        codes.append(u"<code>{0}</code>".format(_esc(m.group(1))))
        return u"\u0001{0}\u0001".format(len(codes) - 1)
    text = _esc(_CODE_RE.sub(keep, text))
    text = _LINK_RE.sub(lambda m: u'<a href="{0}">{1}</a>'.format(
        m.group(2), m.group(1)), text)
    text = _BOLD_RE.sub(u"<b>\\1</b>", text)
    text = _ITAL_RE.sub(u"<i>\\1</i>", text)
    return re.sub(u"\u0001(\\d+)\u0001", lambda m: codes[int(m.group(1))],
                  text)


_LIST_RE = re.compile(u"^(\\s*)([-*]|\\d+\\.)\\s+(.*)$")


def _cells(line):
    line = line.strip()
    if line.startswith(u"|"):
        line = line[1:]
    if line.endswith(u"|"):
        line = line[:-1]
    return [c.strip() for c in line.split(u"|")]


def markdown_to_html(text, title=u""):
    """HTML-pagina uit Markdown-tekst (zie de kop van dit bestand)."""
    lines = text.replace(u"\r\n", u"\n").split(u"\n")
    out = []
    para = []
    item = []           # tekst van het lopende lijstpunt (meerdere regels)
    lists = []          # stapel (inspringing, 'ul'/'ol')
    i = 0

    def flush_para():
        flush_item()
        if para:
            out.append(u"<p>{0}</p>".format(_inline(u" ".join(para))))
            del para[:]

    def flush_item():
        # In een keer door _inline: vet of code over een regelgrens heen.
        if item:
            out.append(_inline(u" ".join(item)))
            del item[:]

    def close_lists(indent=-1):
        flush_item()
        while lists and lists[-1][0] > indent:
            out.append(u"</li></{0}>".format(lists.pop()[1]))

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith(u"```"):
            flush_para()
            flush_item()
            # Een ingesprongen codeblok hoort bij het lopende lijstpunt.
            if not (lists and line.startswith(u" ")):
                close_lists()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(u"```"):
                code.append(lines[i])
                i += 1
            out.append(u"<pre>{0}</pre>".format(_esc(u"\n".join(code))))
            i += 1
            continue
        if not stripped:
            flush_para()
            i += 1
            continue
        m = re.match(u"^(#{1,4})\\s+(.*)$", stripped)
        if m:
            flush_para()
            close_lists()
            n = len(m.group(1))
            out.append(u'<h{0} id="{2}">{1}</h{0}>'.format(
                n, _inline(m.group(2)), slug(m.group(2))))
            i += 1
            continue
        if re.match(u"^-{3,}$", stripped):
            flush_para()
            close_lists()
            out.append(u"<hr>")
            i += 1
            continue
        if stripped.startswith(u"|") and i + 1 < len(lines) and \
                re.match(u"^\\|?[\\s:|-]+\\|?$", lines[i + 1].strip()) and \
                u"-" in lines[i + 1]:
            flush_para()
            close_lists()
            out.append(u"<table><tr>{0}</tr>".format(u"".join(
                u"<th>{0}</th>".format(_inline(c)) for c in _cells(line))))
            i += 2
            while i < len(lines) and lines[i].strip().startswith(u"|"):
                out.append(u"<tr>{0}</tr>".format(u"".join(
                    u"<td>{0}</td>".format(_inline(c))
                    for c in _cells(lines[i]))))
                i += 1
            out.append(u"</table>")
            continue
        m = _LIST_RE.match(line)
        if m:
            flush_para()
            flush_item()
            indent = len(m.group(1).replace(u"\t", u"    "))
            kind = u"ol" if m.group(2)[0].isdigit() else u"ul"
            if lists and indent < lists[-1][0]:
                close_lists(indent)
            if not lists or indent > lists[-1][0]:
                out.append(u"<{0}><li>".format(kind))
                lists.append((indent, kind))
            else:
                out.append(u"</li><li>")
            item.append(m.group(3))
            i += 1
            continue
        if lists and line.startswith(u" "):
            # vervolgregel van een lijstpunt
            item.append(stripped)
            i += 1
            continue
        if stripped.startswith(u">"):
            flush_para()
            close_lists()
            out.append(u"<blockquote>{0}</blockquote>".format(
                _inline(stripped.lstrip(u"> "))))
            i += 1
            continue
        close_lists()
        para.append(stripped)
        i += 1
    flush_para()
    close_lists()
    return _page(title, u"\n".join(out))


def _page(title, body):
    return (u"<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
            u"<meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\">"
            u"<title>{0}</title><style>{1}</style></head><body>{2}"
            u"</body></html>").format(_esc(title), _CSS, body)


def glossary_html(tr):
    """De woordenlijst (bridge_glossary) als HTML-pagina."""
    body = [u"<h1>{0}</h1>".format(tr(u"Uitleg van codes en namen",
                                      u"Explanation of codes and names")),
            u"<p>{0}</p>".format(tr(
                u"Ga op een pagina met instellingen met de muis over een "
                u"instelling voor uitleg; hieronder alle codes die op het "
                u"scherm en in de log voorkomen.",
                u"On the settings pages, hover over a setting for an "
                u"explanation; below are all codes that appear on the "
                u"screen and in the log."))]
    for title, items in bridge_glossary.glossary_items(tr):
        body.append(u"<h2>{0}</h2><dl>".format(_esc(title)))
        for term, text in items:
            body.append(u"<dt>{0}</dt><dd>{1}</dd>".format(_esc(term),
                                                           _esc(text)))
        body.append(u"</dl>")
    return _page(tr(u"Woordenlijst", u"Glossary"), u"\n".join(body))


def doc_html(rel_path, tr):
    """HTML van een document (rel_path t.o.v. docs/, of GLOSSARY_PAGE).
    Ontbreekt het bestand, dan een pagina met die melding."""
    if rel_path == GLOSSARY_PAGE:
        return glossary_html(tr)
    path = os.path.join(docs_dir(), rel_path.replace(u"/", os.sep))
    try:
        f = io.open(path, encoding="utf-8")
        try:
            text = f.read()
        finally:
            f.close()
    except (IOError, OSError) as e:
        return _page(rel_path, u"<p>{0}</p>".format(_esc(tr(
            u"Document niet gevonden: {0} ({1})",
            u"Document not found: {0} ({1})").format(path, e))))
    return markdown_to_html(text, rel_path)


def slug(heading):
    """Anker van een kop zoals GitHub: kleine letters, zonder Markdown en
    leestekens, spaties -> '-' (bijv. '4.4 Convergentiescherm' ->
    '44-convergentiescherm')."""
    text = _LINK_RE.sub(lambda m: m.group(1), heading)
    text = text.replace(u"`", u"").replace(u"*", u"").lower()
    text = re.sub(u"[^\\w\\- ]", u"", text, flags=re.UNICODE)
    return text.replace(u" ", u"-")


def resolve_link(current, href):
    """
    Doel van een link in een document: ("doc", relatief pad, anker),
    ("anchor", None, anker) voor een anker in hetzelfde document,
    ("web", url, None) of (None, None, None). current is het relatieve pad
    van het open document (t.o.v. docs/). README.md en KNOWN_BUGS.md naast
    docs/ zijn bereikbaar als '../README.md'. Links naar code (.py) of
    andere bestanden openen niet.
    """
    anchor = href.split(u"#", 1)[1] if u"#" in href else None
    href = href.split(u"#")[0]
    if href.startswith(u"http://") or href.startswith(u"https://"):
        return "web", href, None
    if not href:
        return ("anchor", None, anchor) if anchor else (None, None, None)
    if not href.lower().endswith(u".md"):
        return None, None, None
    base = os.path.dirname(current) if current != GLOSSARY_PAGE else u""
    rel = os.path.normpath(os.path.join(base, href)).replace(os.sep, u"/")
    if not os.path.exists(os.path.join(docs_dir(), rel)):
        return None, None, None
    return "doc", rel, anchor
