# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Draai de verificatietests van de MecwayAsterBridge (CPython 3).

    python run_verificatie.py                 alle tests
    python run_verificatie.py LS NL-02        alleen ids die zo beginnen
    python run_verificatie.py --models        alleen de .liml-modellen maken
    python run_verificatie.py --report        alleen het rapport opnieuw maken
    python run_verificatie.py --mecway-opslaan [ids]
                                              elk model eerst door Mecway
                                              laten opslaan (zie onder)
    python run_verificatie.py --mecway-opslaan --vergelijk
                                              alleen de vergelijking met de
                                              gewone run opnieuw maken

Per case: model -> modellen/<id>.liml, bridge + Code-Aster in een werkmap
(standaard %TEMP%/mab_verificatie/<id>), vergelijking met de referentie.
Resultaten: resultaten/resultaten.json (per case bijgewerkt, zodat een deel
opnieuw gedraaid kan worden), resultaten/resultaten.md en .csv, en de
gegenereerde .comm per case in resultaten/comm/.
Code-Aster: CONFIG_BRIDGE["exe_aster"] (bridge_utils.exe_aster_path()) uit Scripts/bridge_utils.py.

--mecway-opslaan (of VERIF_MECWAY=1): Mecway opent elk gegenereerd model en
slaat het zelf weer op (mecway.exe <model> script TestFiles/Tools/
mw_save_as.py, zonder venster en zonder solve); de bridge leest dan het
bestand zoals Mecway het schrijft. Uitvoer in resultaten/mecway/ (de gewone
resultaten blijven ongewijzigd), plus vergelijking.md: per controle status
en FEM-waarde naast die van de gewone run (resultaten/resultaten.json) en
of de .comm gelijk is.
"""
import sys
import os
import io
import re
import csv
import json
import math
import glob
import time
import shutil
import tempfile
import importlib
import subprocess
import datetime
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verif_lib as V

RAW = os.path.join(V.RESULTS, "resultaten.json")
# uitvoermap (resultaten/ of resultaten/mecway/), zie main()
OUT = V.RESULTS
MECWAY_EXE = os.environ.get("MECWAY_EXE",
                            r"C:\Program Files\Mecway\mecway.exe")
MW_SAVE = os.path.join(V.REPO, "TestFiles", "Tools", "mw_save_as.py")


def load_cases():
    cases = []
    for path in sorted(glob.glob(os.path.join(HERE, "tests_*.py"))):
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            mod = importlib.import_module(name)
            cases += mod.TESTS
        except Exception as e:
            # een (half afgemaakte) module mag de rest niet tegenhouden
            print("WAARSCHUWING: %s overgeslagen: %r" % (name, e))
    ids = [c.id for c in cases]
    dup = set(i for i in ids if ids.count(i) > 1)
    if dup:
        raise SystemExit("dubbele test-id's: %s" % sorted(dup))
    return cases


def mecway_resave(liml, model, root):
    """
    Laat Mecway liml openen en zelf opslaan naar <root>/_mecway/<naam>
    (mw_save_as.py via "mecway.exe <bestand> script <script>", Mecway-
    handleiding par. 16.1). Returns (pad of None, [fouten]). Controleert dat
    Mecway de knoopnummers, coordinaten en knoopselecties niet veranderd
    heeft: Results zoekt die op in het gegenereerde Model.
    """
    d = os.path.join(root, "_mecway")
    if not os.path.isdir(d):
        os.makedirs(d)
    dst = os.path.join(d, os.path.basename(liml))
    if os.path.isfile(dst):
        os.remove(dst)
    env = dict(os.environ, MAB_MW_OUT=dst)
    # hidden, with the dialog watchdog (verif_lib.run_mecway)
    state, _rc, wins = V.run_mecway([MECWAY_EXE, liml, "script", MW_SAVE],
                                    env=env, timeout=600)
    if state == "timeout":
        return None, ["MECWAY_TIMEOUT (opslaan)"]
    if state != "ok":
        label = "MECWAY_DIALOOG" if state == "dialog" else "MECWAY_VENSTER"
        return None, ["%s (opslaan): %s" % (label, "; ".join(
            " / ".join([w[0]] + list(w[2][:8])) for w in wins))]
    if not os.path.isfile(dst):
        return None, ["Mecway heeft het model niet opgeslagen"]
    errors = []
    root_el = ET.parse(dst).getroot()
    nodes = {}
    for n in root_el.findall("node"):
        nodes[int(n.get("nid"))] = tuple(float(n.get(k)) for k in "xyz")
    if sorted(nodes) != list(range(1, len(model.nodes) + 1)):
        errors.append("Mecway-kopie: andere knoopnummers")
    else:
        for i, p in enumerate(model.nodes):
            q = nodes[i + 1]
            if any(abs(p[k] - q[k]) > 1e-9 * max(1.0, abs(p[k]))
                   for k in range(3)):
                errors.append("Mecway-kopie: knoop %d op een andere plek"
                              % (i + 1))
                break
    for sel in root_el.findall("nodeselection"):
        name = sel.get("name")
        if name in model.nodesel and \
                set(int(n.get("nid")) for n in sel.findall("node")) != \
                set(model.nodesel[name]):
            errors.append("Mecway-kopie: knoopselectie %s anders" % name)
    return dst, errors


# ------------------------------------------------------------------
# Paden anonimiseren in de bijgehouden resultaten (resultaten/comm/*.comm,
# resultaten.json): de werkmap wordt <WORKDIR>, de repo <REPO> en het
# gebruikersprofiel %LOCALAPPDATA% / %USERPROFILE%. Zo staan er geen
# machine- of persoonsgebonden paden in de repo.
# ------------------------------------------------------------------
def _path_variants(path):
    """Schrijfwijzen van een pad zoals ze in een .comm of log staan:
    met \\, met / en met verdubbelde \\ (Python-tekst)."""
    p = os.path.normpath(path).rstrip("\\/")
    back = p.replace("/", "\\")
    return sorted(set([back, back.replace("\\", "/"),
                       back.replace("\\", "\\\\")]), key=len, reverse=True)


def _replace_root(text, root, token):
    for v in _path_variants(root):
        text = re.sub(re.escape(v) + r"(?=[\\/'\"\s]|$)",
                      lambda m, t=token: t, text, flags=re.I)
    return text


def anonymize(text, case_id=None, work_root=None):
    """Vervang absolute paden in text door <WORKDIR>, <REPO> of een
    omgevingsvariabele. Eerst de werkmap en de repo van deze run; daarna
    (voor resultaten van een andere map of machine) elk absoluut pad tot de
    laatste map <case_id> (-> <WORKDIR>) of tot de laatste map
    Scripts/TestFiles (-> <REPO>), met de scheidingstekens erachter; als
    laatste het gebruikersprofiel (%LOCALAPPDATA%, %USERPROFILE%)."""
    if not text:
        return text
    if work_root:
        text = _replace_root(text, work_root, "<WORKDIR>")
    text = _replace_root(text, V.REPO, "<REPO>")
    # voorvoegsel: absoluut pad dat niet op een scheidingsteken eindigt
    prefix = r"[A-Za-z]:[\\/](?:[^'\"\r\n<>]*[^\\/'\"\r\n<>])?"
    if case_id:
        text = re.sub(prefix + r"(?=[\\/]+%s[\\/])" % re.escape(case_id),
                      "<WORKDIR>", text)
    text = re.sub(prefix + r"(?=[\\/]+(?:Scripts|TestFiles)(?:[\\/'\"]|$))",
                  "<REPO>", text)
    for var in ("LOCALAPPDATA", "USERPROFILE"):
        if os.environ.get(var):
            text = _replace_root(text, os.environ[var], "%" + var + "%")
    return text


def _anonymize_obj(obj, case_id, work_root=None):
    """anonymize() op alle teksten in een rij van resultaten.json."""
    if isinstance(obj, dict):
        return dict((k, _anonymize_obj(v, case_id, work_root))
                    for k, v in obj.items())
    if isinstance(obj, list):
        return [_anonymize_obj(v, case_id, work_root) for v in obj]
    if isinstance(obj, str):
        return anonymize(obj, case_id, work_root)
    return obj


def _copy_comm_anonymized(src, dst, case_id, work_root):
    text = io.open(src, encoding="utf-8", errors="replace",
                   newline="").read()
    io.open(dst, "w", encoding="utf-8", newline="").write(
        anonymize(text, case_id, work_root))


def anonymize_existing(rows):
    """--report: ook de al bijgehouden .comm-bestanden en rijen
    anonimiseren (bijv. resultaten van voor deze functie). Returns True als
    er iets veranderd is in rows."""
    d = os.path.join(OUT, "comm")
    for path in glob.glob(os.path.join(d, "*.comm")):
        cid = os.path.splitext(os.path.basename(path))[0]
        old = io.open(path, encoding="utf-8", errors="replace",
                      newline="").read()
        new = anonymize(old, cid)
        if new != old:
            io.open(path, "w", encoding="utf-8", newline="").write(new)
    changed = False
    for cid in list(rows):
        new = _anonymize_obj(rows[cid], cid)
        if new != rows[cid]:
            rows[cid] = new
            changed = True
    return changed


def run_case(case, root, mecway=False):
    model = case.build()
    liml = model.write(case.liml_path())
    pre_errors = []
    if mecway:
        liml, pre_errors = mecway_resave(liml, model, root)
    work = os.path.join(root, case.id)
    cfg = os.path.join(root, case.id + ".json")
    json.dump({"settings": case.settings, "general": case.general,
               "timeout": case.timeout}, open(cfg, "w"))
    t0 = time.time()
    if liml:
        subprocess.call([sys.executable, os.path.join(HERE, "_run_one.py"),
                         work, liml, case.analysis, cfg])
    elif os.path.isdir(work):
        shutil.rmtree(work)
    run = {}
    if os.path.isfile(os.path.join(work, "run.json")):
        run = json.load(io.open(os.path.join(work, "run.json"),
                                encoding="utf-8"))
    row = {"id": case.id, "group": case.group, "title": case.title,
           "analysis": case.analysis, "series": case.series, "h": case.h,
           "note": case.note, "seconds": round(time.time() - t0, 1),
           "diagnostic": run.get("diagnostic", ""),
           "errors": pre_errors + run.get("errors", []), "checks": [],
           "n_nodes": len(model.nodes), "n_elem": model.n_elem,
           "settings": case.settings, "general": case.general}
    if run.get("export"):
        comm = run["export"][:-len(".export")] + ".comm"
        if os.path.isfile(comm):
            d = os.path.join(OUT, "comm")
            if not os.path.isdir(d):
                os.makedirs(d)
            _copy_comm_anonymized(comm, os.path.join(d, case.id + ".comm"),
                                  case.id, root)
    if run.get("results"):
        try:
            r = V.Results(run["results"], model)
            # .mess van de run (o.a. de globale foutschatting,
            # verif_lib.error_summary)
            r.mess = run.get("mess")
            for chk in case.checks:
                try:
                    row["checks"].append(chk.evaluate(r))
                except Exception as e:
                    row["checks"].append({"name": chk.name, "error": repr(e),
                                          "ok": False, "ref": chk.ref,
                                          "unit": chk.unit,
                                          "source": chk.source,
                                          "known": chk.known})
        except Exception as e:
            row["errors"].append("resultaten niet gelezen: %r" % e)
    if not row["checks"]:
        row["checks"] = [{"name": c.name, "ok": False, "ref": c.ref,
                          "unit": c.unit, "source": c.source,
                          "known": c.known,
                          "error": "geen resultaten"} for c in case.checks]
    return _anonymize_obj(row, case.id, root)


def _num(v):
    if v is None:
        return ""
    if v == 0:
        return "0"
    a = abs(v)
    if a >= 1e5 or a < 1e-3:
        return "%.4e" % v
    return "%.5g" % v


def _status(chk):
    if chk.get("ok"):
        return "OK"
    if chk.get("known"):
        return "BEKEND (%s)" % chk["known"]
    return "FOUT" if "error" in chk else "NOK"


def _richardson(rs, name):
    """
    Orde en limiet uit de laatste drie meshes (onafhankelijk van de
    referentie): p = ln((f1-f2)/(f2-f3)) / ln(r), limiet f3 + (f3-f2) /
    (r^p - 1), bij een vaste verfijningsfactor r = h1/h2 = h2/h3.
    """
    pts = []
    for r in rs:
        c = [x for x in r["checks"] if x["name"] == name and "fem" in x]
        if c and r.get("h"):
            pts.append((r["h"], c[0]["fem"], c[0].get("ref")))
    if len(pts) < 3:
        return []
    (h1, f1, _), (h2, f2, _), (h3, f3, ref) = pts[-3:]
    r1, r2 = h1 / h2, h2 / h3
    d1, d2 = f1 - f2, f2 - f3
    if max(abs(d1), abs(d2)) <= 1e-7 * max(abs(f3), 1e-300):
        return [u"", u"Richardson: op alle meshes gelijk (exact, geen "
                     u"discretisatiefout)."]
    if abs(r1 - r2) > 1e-6 * r1 or d1 == 0 or d2 == 0 or d1 * d2 < 0:
        return [u"", u"Richardson: niet monotoon of geen vaste "
                     u"verfijningsfactor."]
    p = math.log(d1 / d2) / math.log(r1)
    lim = f3 + (f3 - f2) / (r1 ** p - 1.0) if abs(r1 ** p - 1.0) > 1e-12         else f3
    txt = u"Richardson (laatste drie meshes): orde p = %.2f, limiet %s" % (
        p, _num(lim))
    if ref:
        txt += u" (%+.3f%% t.o.v. de referentie)" % (100 * (lim - ref) / abs(ref))
    return [u"", txt + u"."]


def write_report(rows):
    rows = sorted(rows.values(), key=lambda r: r["id"])
    try:
        rev = subprocess.check_output(["git", "-C", HERE, "rev-parse",
                                       "--short", "HEAD"]).decode().strip()
    except Exception:
        rev = "?"
    n_chk = sum(len(r["checks"]) for r in rows)
    n_ok = sum(1 for r in rows for c in r["checks"] if c.get("ok"))
    n_known = sum(1 for r in rows for c in r["checks"]
                  if not c.get("ok") and c.get("known"))
    out = [u"# Verificatieresultaten MecwayAsterBridge", u"",
           u"Gemaakt door `run_verificatie.py` op %s (bridge %s, Code-Aster "
           u"17.4). Toelichting en bronnen: `docs/Verificatie.md`." % (
               datetime.date.today().isoformat(), rev), u"",
           u"**%d van %d controles binnen de tolerantie** (%d testcases); "
           u"%d buiten de tolerantie door een bekende beperking (BEKEND, "
           u"zie `KNOWN_BUGS.md`), %d onverwacht (NOK/FOUT)."
           % (n_ok, n_chk, len(rows), n_known, n_chk - n_ok - n_known), u""]
    if OUT != V.RESULTS:
        out[2:2] = [u"Modus `--mecway-opslaan`: elk model is eerst door "
                    u"Mecway geopend en opgeslagen; vergelijking met de "
                    u"gewone run in `vergelijking.md`.", u""]
    groups = []
    for r in rows:
        if r["group"] not in groups:
            groups.append(r["group"])
    for g in groups:
        out += [u"## " + g, u"",
                u"| ID | Test | Grootheid | Referentie | FEM | Afwijking | "
                u"Tolerantie | Status |", u"|---|---|---|---|---|---|---|---|"]
        for r in [x for x in rows if x["group"] == g]:
            for c in r["checks"]:
                dev = (u"%+.2f%%" % (100 * c["rel"]) if c.get("rel") is not None
                       else _num(c.get("dev")))
                tol = (u"%g %s" % (c["tol_abs"], c.get("unit", ""))
                       if c.get("tol_abs") is not None
                       else (u"%g%%" % (100 * c["tol"]) if c.get("tol") else ""))
                out.append(u"| %s | %s | %s | %s %s | %s | %s | %s | %s |" % (
                    r["id"], r["title"], c["name"], _num(c.get("ref")),
                    c.get("unit", ""), _num(c.get("fem")) if "fem" in c
                    else c.get("error", ""), dev if "fem" in c else "",
                    tol, _status(c)))
        problems = [r for r in rows if r["group"] == g and
                    (r["errors"] or r["diagnostic"] not in ("OK", "<A>_ALARM"))]
        for r in problems:
            out.append(u"\n*%s: diagnose %s; %s*" % (
                r["id"], r["diagnostic"] or "-",
                "; ".join(r["errors"][:5]) or "-"))
        out.append(u"")
    # mesh-convergentiereeksen
    series = []
    for r in rows:
        if r.get("series") and r["series"] not in series:
            series.append(r["series"])
    if series:
        out += [u"## Mesh-convergentie", u""]
    for s in series:
        rs = sorted([r for r in rows if r.get("series") == s],
                    key=lambda r: -(r["h"] or 0))
        # geen discretisatiefout: opt-out per check of referentie 0
        # (vergelijking met een replica van hetzelfde schema)
        names = [c["name"] for c in rs[0]["checks"]
                 if c.get("in_series", True) and c.get("ref")]
        for name in names:
            out += [u"**%s – %s**" % (s, name), u"",
                    u"| ID | h | knopen | FEM | fout | orde p |",
                    u"|---|---|---|---|---|---|"]
            prev = None
            for r in rs:
                c = [x for x in r["checks"] if x["name"] == name]
                c = c[0] if c else {}
                err = abs(c["rel"]) if c.get("rel") is not None else None
                p = ""
                if prev and err and prev[1] and r["h"] and prev[0] and \
                        err > 1e-7 and prev[1] > 1e-7 and r["h"] != prev[0]:
                    p = u"%.2f" % (math.log(prev[1] / err) /
                                   math.log(prev[0] / r["h"]))
                out.append(u"| %s | %s | %d | %s | %s | %s |" % (
                    r["id"], _num(r["h"]), r["n_nodes"], _num(c.get("fem")),
                    (u"%.3f%%" % (100 * err)) if err is not None else "", p))
                prev = (r["h"], err)
            out += _richardson(rs, name)
            out.append(u"")
    io.open(os.path.join(OUT, "resultaten.md"), "w", encoding="utf-8",
            newline="\n").write(u"\n".join(out) + u"\n")
    with io.open(os.path.join(OUT, "resultaten.csv"), "w",
                 encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["id", "groep", "test", "grootheid", "referentie", "fem",
                    "rel_afwijking", "tolerantie", "eenheid", "status",
                    "knopen", "elementen", "seconden", "bron"])
        for r in rows:
            for c in r["checks"]:
                w.writerow([r["id"], r["group"], r["title"], c["name"],
                            c.get("ref"), c.get("fem"), c.get("rel"),
                            c.get("tol") if c.get("tol_abs") is None
                            else c.get("tol_abs"), c.get("unit"), _status(c),
                            r["n_nodes"], r["n_elem"], r["seconds"],
                            c.get("source")])


def _comm_text(path):
    """Inhoud van een .comm zonder commentaarregels (daar staan o.a. de
    modelnaam en het tijdstempel van de run in) en met absolute paden
    (werkmap, scripts) vervangen door <pad>."""
    if not os.path.isfile(path):
        return None
    pat = re.compile(r"""(['"])[A-Za-z]:[\\/][^'"]*\1""")
    return [pat.sub("<pad>", l.rstrip())
            for l in io.open(path, encoding="utf-8", errors="replace")
            if not l.lstrip().startswith("#")]


_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _same_but_rounding(a, b, rel=1e-12):
    """True als twee .comm-teksten alleen in de laatste cijfers van getallen
    verschillen (Mecway schrijft waarden met 15 significante cijfers)."""
    ta, tb = "\n".join(a), "\n".join(b)
    if _NUM.sub("#", ta) != _NUM.sub("#", tb):
        return False
    for x, y in zip(_NUM.findall(ta), _NUM.findall(tb)):
        x, y = float(x), float(y)
        if abs(x - y) > rel * max(abs(x), abs(y)):
            return False
    return True


def write_comparison(rows, base_rows):
    """
    vergelijking.md in OUT: per controle de Mecway-run (rows) naast de
    gewone run (base_rows, resultaten/resultaten.json). Identiek = zelfde
    status en |FEM verschil| <= 1e-6 x max(|FEM gewoon|, tol_abs)
    (afronding van de getallen in het bestand, ruis rond 0); anders =
    andere status of een groter verschil; niet
    mogelijk = de case kon niet door Mecway (fout bij opslaan).
    """
    lines, same, diff, impossible, comm_diff, comm_round = [], 0, 0, 0, [], []
    for cid in sorted(rows):
        r = rows[cid]
        b = base_rows.get(cid)
        mw_err = [e for e in r["errors"] if "Mecway" in e or "MECWAY" in e]
        cm = _comm_text(os.path.join(OUT, "comm", cid + ".comm"))
        cb = _comm_text(os.path.join(V.RESULTS, "comm", cid + ".comm"))
        if cm is not None and cb is not None and cm != cb:
            if _same_but_rounding(cm, cb):
                comm_round.append(cid)
            else:
                comm_diff.append(cid)
        seen = {}
        for c in r["checks"]:
            if mw_err:
                impossible += 1
                lines.append((cid, c["name"], "", "", "", "niet mogelijk: "
                              + "; ".join(mw_err)))
                continue
            # zelfde naam kan vaker voorkomen (afgeronde referentie in de
            # naam): de k-de met die naam
            k = seen[c["name"]] = seen.get(c["name"], -1) + 1
            cb_ = [x for x in (b or {}).get("checks", [])
                   if x["name"] == c["name"]]
            if len(cb_) <= k:
                diff += 1
                lines.append((cid, c["name"], "-", _status(c), "",
                              "niet in de gewone run"))
                continue
            cb_ = cb_[k]
            fm, fb = c.get("fem"), cb_.get("fem")
            # verschil relatief t.o.v. de waarde, of t.o.v. de absolute
            # tolerantie als die groter is (grootheden rond 0, bijv.
            # |Im| / |Re| = 3e-17: ruis)
            d = None
            if fm is not None and fb is not None:
                d = abs(fm - fb) / max(abs(fb), c.get("tol_abs") or 0.0,
                                       1e-300)
            ok = _status(c) == _status(cb_) and (
                (fm is None and fb is None) or (d is not None and d <= 1e-6))
            if ok:
                same += 1
                continue
            diff += 1
            lines.append((cid, c["name"], _status(cb_), _status(c),
                          "%.3g" % d if d is not None else "",
                          "%s -> %s" % (_num(fb), _num(fm))))
    out = [u"# Mecway-route: vergelijking met de gewone run", u"",
           u"Gemaakt door `run_verificatie.py --mecway-opslaan` op %s. Elk "
           u"model is eerst door Mecway geopend en opgeslagen "
           u"(`TestFiles/Tools/mw_save_as.py`), daarna door de bridge en "
           u"Code-Aster gerekend en vergeleken met `../resultaten.json`."
           % datetime.date.today().isoformat(), u"",
           u"**%d controles identiek** (zelfde status, FEM-waarde gelijk tot "
           u"1e-6 relatief, of tot 1e-6 x de absolute tolerantie bij "
           u"grootheden rond 0), **%d anders**, **%d niet mogelijk** (%d "
           u"testcases)." % (same, diff, impossible, len(rows)), u"",
           u".comm (zonder commentaarregels en paden) anders dan in de "
           u"gewone run: " + (u", ".join(comm_diff) if comm_diff else u"geen")
           + u"; alleen in de laatste cijfers van getallen (Mecway schrijft "
           u"15 significante cijfers): " + (u", ".join(comm_round)
                                           if comm_round else u"geen")
           + u".", u""]
    if lines:
        out += [u"| ID | Controle | Gewoon | Mecway | rel. verschil | "
                u"Toelichting |", u"|---|---|---|---|---|---|"]
        out += [u"| %s |" % u" | ".join(l) for l in lines]
    io.open(os.path.join(OUT, "vergelijking.md"), "w", encoding="utf-8",
            newline="\n").write(u"\n".join(out) + u"\n")
    print("vergelijking: %d identiek, %d anders, %d niet mogelijk; .comm "
          "anders: %s; alleen afronding: %s" % (
              same, diff, impossible, comm_diff or "geen",
              comm_round or "geen"))


def main(argv):
    global RAW, OUT
    mecway = "--mecway-opslaan" in argv or \
        os.environ.get("VERIF_MECWAY") == "1"
    base_raw = RAW
    if mecway:
        OUT = os.path.join(V.RESULTS, "mecway")
        RAW = os.path.join(OUT, "resultaten.json")
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    rows = {}
    if os.path.isfile(RAW):
        rows = json.load(io.open(RAW, encoding="utf-8"))

    def compare():
        if mecway and os.path.isfile(base_raw):
            write_comparison(rows, json.load(io.open(base_raw,
                                                     encoding="utf-8")))
    if "--report" in argv or "--vergelijk" in argv:
        if anonymize_existing(rows):
            json.dump(rows, io.open(RAW, "w", encoding="utf-8"), indent=1)
        write_report(rows)
        compare()
        return
    cases = load_cases()
    sel = [a for a in argv if not a.startswith("--")]
    if sel:
        cases = [c for c in cases if any(c.id.startswith(s) for s in sel)]
    if "--models" in argv:
        for c in cases:
            c.build().write(c.liml_path())
            print("model", c.liml_path())
        return
    root = os.environ.get("VERIF_WORK") or os.path.join(
        tempfile.gettempdir(), "mab_verificatie")
    if not os.path.isdir(root):
        os.makedirs(root)
    for c in cases:
        print("== %s %s ..." % (c.id, c.title))
        sys.stdout.flush()
        row = run_case(c, root, mecway)
        for chk in row["checks"]:
            print("   %-28s ref %-12s fem %-12s %s" % (
                chk["name"], _num(chk.get("ref")), _num(chk.get("fem")),
                _status(chk)))
        # opnieuw inlezen: een andere run kan intussen cases toegevoegd hebben
        if os.path.isfile(RAW):
            rows = json.load(io.open(RAW, encoding="utf-8"))
        rows[c.id] = row
        json.dump(rows, io.open(RAW, "w", encoding="utf-8"), indent=1)
    write_report(rows)
    compare()


if __name__ == "__main__":
    main(sys.argv[1:])
