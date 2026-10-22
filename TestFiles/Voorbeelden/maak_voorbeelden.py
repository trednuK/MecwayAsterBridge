# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Testmodellen A, C en S van docs/ASTER_regels_voorbeelden.md par. 5
(voorbeelden 1 tot 8) en model T (verlijmd contact tussen platen,
docs/Instellingen_contact_en_nietlineair.md), gebouwd met TestFiles/Verificatie/verif_lib.py
(CPython 3, ontwikkelgereedschap; draait niet in Mecway).

    python maak_voorbeelden.py          schrijft Voorbeeld_A/C/S/T.liml hier
                                        (zonder #ASTER-regels)
    python maak_voorbeelden.py --run [namen]
                                        rekent de varianten van de
                                        voorbeelden door (bridge + Code-Aster,
                                        zoals de verificatie: _run_one.py) en
                                        print de uitkomsten van de doc
                                        (namen: alleen de varianten die zo
                                        beginnen, bijv. C_)

Werkmap van --run: VERIF_WORK (of %TEMP%/mab_voorbeelden).
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VERIF = os.path.join(os.path.dirname(HERE), "Verificatie")
sys.path.insert(0, VERIF)
from verif_lib import (Model, Results, hexmesh, quadmesh, linemesh,  # noqa
                       box, HEX_FACE)
from tests_lineair_statisch import build_ls07_strip  # noqa

STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
DENS = '<density type="Simple" density="7850 kg/m³" />'
TS = {"timeperiod": "1 s", "stepsize": "0.1 s"}

# ------------------------------------------------------------------
# Model A: hex20-blok 20 x 20 x 20 mm (2 x 2 x 2), Root (x = 0) vast; een
# losse buis 8/6 mm, L = 50 mm (5 line2) vanuit het midden van het
# eindvlak Tip (x = 20 mm) in +x; 50 N in Y en -100 N in Z op BalkEind.
# Staal E = 210 GPa, nu = 0,3, rho = 7850 kg/m3.
# ------------------------------------------------------------------
LB, LA = 0.020, 0.050                    # blok, balk [m]


def model_a(analysis="S30", rigid=False, custom=None, attrs=None):
    ts = TS if analysis == "L30" else None
    m = Model(analysis, timesteps=ts, attrs=attrs)
    m.elset("Blok", "BlokStaal")
    blk = hexmesh(m, "Blok", 2, 2, 2, box(0, LB, 0, LB, 0, LB), order=2)
    m._index = {}                        # balk: eigen knopen (los)
    m.elset("Balk", "Buis")
    _eids, nids = linemesh(m, "Balk", 5, (LB, LB / 2, LB / 2),
                           (LB + LA, LB / 2, LB / 2))
    blok_e = ('<mechanical type="Isotropic" youngsmodulus="2.1e18 Pa" '
              'poissonratio="0.3" />') if rigid else STEEL
    m.mat("BlokStaal", blok_e, DENS)
    m.mat("Buis", '<geometric type="UniformCircularTube" roundod="8 mm" '
          'roundid="6 mm" />', STEEL, DENS)
    m.face_selection("Root", blk["faces"]["u0"])
    m.face_selection("Tip", blk["faces"]["u1"])
    m.node_selection("BalkStart", [nids[0]])
    m.node_selection("BalkEind", [nids[-1]])
    m.node_selection("02_Last-punt", [nids[-1]])
    m.add('<fixed selection="Root" />')
    m.add('<force selection="BalkEind"><x>0 N</x><y>50 N</y><z>-100 N</z>'
          '</force>')
    _custom(m, custom)
    return m


# ------------------------------------------------------------------
# Model C: twee hex8-blokken 20 x 20 x 10 mm (2 x 2 x 1) op elkaar, eigen
# knopen; Mecway-contact (unilateral elastic, normal stiffness
# 100000 GPa/m) tussen 01_Contact_onder (bovenvlak onder) en 02 Contact
# boven (ondervlak boven); Bodem (onderkant) vast, Top 0,01 mm omlaag (en
# in x en y vast).
# ------------------------------------------------------------------
def model_c(custom=None, stepsize=None):
    # stepsize: Mecway's Time step size (voorbeeld 6: 0,25 s = 4 stappen)
    ts = dict(TS, stepsize=stepsize) if stepsize else TS
    m = Model("L30", timesteps=ts)
    m.elset("Onder", "Staal")
    lo = hexmesh(m, "Onder", 2, 2, 1, box(0, 0.02, 0, 0.02, 0, 0.01))
    m._index = {}
    m.elset("Boven", "Staal")
    up = hexmesh(m, "Boven", 2, 2, 1, box(0, 0.02, 0, 0.02, 0.01, 0.02))
    m.mat("Staal", STEEL)
    m.face_selection("01_Contact_onder", lo["faces"]["w1"])
    m.face_selection("02_Contact_boven", up["faces"]["w0"])
    m.face_selection("Bodem", lo["faces"]["w0"])
    m.face_selection("Top", up["faces"]["w1"])
    m.add('<fixed selection="Bodem" />')
    m.add('<displacement selection="Top"><value>-0.01 mm</value><x>0</x>'
          '<y>0</y><z>1</z></displacement>')
    for d in ("<x>1</x><y>0</y>", "<x>0</x><y>1</y>"):
        m.add('<displacement selection="Top"><value>0 mm</value>%s<z>0</z>'
              '</displacement>' % d)
    m.add('<contact2 selectionmaster="01_Contact_onder" selectionslave='
          '"02_Contact_boven" type="unilateralelastic"><tolerance>0 m'
          '</tolerance><normalstiffness>100000 GPa/m</normalstiffness>'
          '<tangentialstiffness>0 GPa/m</tangentialstiffness>'
          '<frictioncoefficient>0</frictioncoefficient></contact2>')
    _custom(m, custom)
    return m


# ------------------------------------------------------------------
# Model S: hex8-blok 20 x 20 x 10 mm (4 x 4 x 2), Bodem (onderkant) vast;
# een losse quad4-plaat 20 x 20 mm, dikte 2 mm (4 x 4), rechtop in het
# vlak x = 10 mm op het blok (z = 10 .. 30 mm); Plaatvoet = de onderrand
# (op het bovenvlak van het blok), PlaatTop = de bovenrand, 10 N in X.
# ------------------------------------------------------------------
def model_s(analysis="S30", custom=None):
    ts = TS if analysis == "L30" else None
    m = Model(analysis, timesteps=ts)
    m.elset("Blok", "Staal")
    blk = hexmesh(m, "Blok", 4, 4, 2, box(0, 0.02, 0, 0.02, 0, 0.01))
    m._index = {}
    m.elset("Plaat", "Plaat2")
    pl = quadmesh(m, "Plaat", 4, 4,
                  lambda u, v: (0.01, 0.02 * u, 0.01 + 0.02 * v))
    m.mat("Staal", STEEL)
    m.mat("Plaat2", '<geometric type="Plate" thickness="2 mm" />', STEEL)
    m.face_selection("Bodem", blk["faces"]["w0"])
    m.node_selection("Plaatvoet", sorted(pl["nodes"]["v0"]))
    m.node_selection("PlaatTop", sorted(pl["nodes"]["v1"]))
    m.add('<fixed selection="Bodem" />')
    m.add('<force selection="PlaatTop"><x>10 N</x><y>0 N</y><z>0 N</z>'
          '</force>')
    _custom(m, custom)
    return m


# ------------------------------------------------------------------
# Model T: ingeklemde plaatstrook 200 x 20 mm, 2 mm (DKT quad4) uit twee
# delen met eigen knopen: Deel_A (x = 0 .. 100 mm, 10 x 4) en Deel_B
# (x = 100 .. 200 mm, 10 x 7), verlijmd langs de naad (bonded contact
# bondedtie: master Lijm_A = laatste rij schaalvlakken van A, slave
# Lijm_B = rand van B); Inklemming (x = 0) vast, 1 N in -Z op Vrij_eind.
# Zelfde model als verificatiecase LS-07a.
# ------------------------------------------------------------------
def model_t():
    return build_ls07_strip(True)()


def _custom(m, custom):
    for tag, lines in (custom or {}).items():
        text = "\n".join(lines).replace("&", "&amp;").replace(
            "<", "&lt;").replace(">", "&gt;")
        m.add("<{0}>{1}</{0}>".format(tag, text))


# ------------------------------------------------------------------
# De #ASTER-regels, letterlijk uit docs/ASTER_regels_voorbeelden.md
# ------------------------------------------------------------------
EX1 = ["#ASTER verb = AFFE_CHAR_MECA(MODELE=model,",
       "#ASTER     LIAISON_ELEM=_F(OPTION='3D_POU', GROUP_MA_1='<<Tip>>',",
       "#ASTER                     GROUP_NO_2='<<BalkStart>>'))",
       "#ASTER-EXCIT verb"]
EX2 = ["$ASTER nplaat = CREA_CHAMP(TYPE_CHAM='NOEU_GEOM_R', "
       "OPERATION='NORMALE',",
       "$ASTER     MODELE=model, GROUP_MA='<<Plaat>>')",
       "$ASTER lijm = AFFE_CHAR_MECA(MODELE=model,",
       "$ASTER     LIAISON_MAIL=_F(TYPE_RACCORD='COQUE_MASSIF',",
       "$ASTER         GROUP_MA_MAIT='<<Blok>>', GROUP_NO_ESCL='<<Plaatvoet>>',",
       "$ASTER         EPAIS=0.002, CHAM_NORMALE=nplaat))",
       "$ASTER-EXCIT lijm"]
EX3 = ["$ Extra last en blokkering voor Code-Aster (SI-eenheden: N, m)",
       "$ASTER extra = AFFE_CHAR_MECA(MODELE=model,",
       "$ASTER     FORCE_NODALE=_F(GROUP_NO='<<02_Last-punt>>', FX=200.0),",
       "$ASTER     DDL_IMPO=_F(GROUP_NO='<<02_Last-punt>>', DRX=0.0))",
       "$ASTER-EXCIT extra"]
EX4 = ["#ASTER f_ramp = DEFI_FONCTION(NOM_PARA='INST', VALE=(0.0, 0.0, 1.0, "
       "300.0),",
       "#ASTER                        PROL_GAUCHE='CONSTANT', "
       "PROL_DROITE='CONSTANT')",
       "#ASTER ramp = AFFE_CHAR_MECA_F(MODELE=model,",
       "#ASTER     FORCE_NODALE=_F(GROUP_NO='<<BalkEind>>', FX=f_ramp))",
       "#ASTER-EXCIT ramp"]
EX5 = ["#ASTER-ZONE ALGO_CONT='PENALISATION', COEF_PENA_CONT=1.0E14",
       "#ASTER-CONTACT ALGO_RESO_GEOM='NEWTON'"]
EX6 = ["#ASTER-ZONE CONTACT_INIT='OUI'",
       "#ASTER-CONTACT ALGO_RESO_CONT='POINT_FIXE', ITER_CONT_MAXI=50",
       "#ASTER-OPTIE newton_max_iter = 40",
       "#ASTER-OPTIE convergence_resi_rela = 1e-8",
       "#ASTER-OPTIE deformation = PETIT"]


def ex7(face, at="INST=t_res"):
    return ["#ASTER-POST mesh = DEFI_GROUP(reuse=mesh, MAILLAGE=mesh,",
            "#ASTER-POST     CREA_GROUP_NO=_F(NOM='bodem_n', "
            "GROUP_MA='<<%s>>'))" % face,
            "#ASTER-POST reac = POST_RELEVE_T(ACTION=_F("
            "OPERATION='EXTRACTION',",
            "#ASTER-POST     INTITULE='reactie', RESULTAT=res, "
            "NOM_CHAM='REAC_NODA',",
            "#ASTER-POST     GROUP_NO='bodem_n', RESULTANTE=('DX', 'DY', "
            "'DZ'),",
            "#ASTER-POST     %s))" % at,
            "#ASTER-POST IMPR_TABLE(TABLE=reac, UNITE=6)"]


EX8 = ["#ASTER-POST tmax = POST_RELEVE_T(ACTION=_F(OPERATION='EXTREMA',",
       "#ASTER-POST     INTITULE='vmis_max', RESULTAT=res, "
       "NOM_CHAM='SIEQ_NOEU',",
       "#ASTER-POST     NOM_CMP='VMIS', TOUT='OUI'))",
       "#ASTER-POST IMPR_TABLE(TABLE=tmax, UNITE=6)"]

RM, RE = "radiossmodeldefinition", "radiossengineinput"
MY = "nastranbulkdata"

# (naam, analyse, model, instellingen)
RUNS = [
    ("A_statisch", "lin_static_3d",
     lambda: model_a("S30", custom={RM: EX1, RE: EX8 + ex7(
         "Root", "NUME_ORDRE=1")}), {}),
    ("A_nietlin", "nonlin_static_3d",
     lambda: model_a("L30", custom={RM: EX1}), {}),
    ("A_modaal", "modal_3d",
     lambda: model_a("V30", custom={RM: EX1}, attrs={"maxmode": 4}), {}),
    ("A_knik", "buckling_3d",
     lambda: model_a("B30", custom={RM: EX1}, attrs={"maxmode": 4}), {}),
    ("A_modaal_star", "modal_3d",
     lambda: model_a("V30", rigid=True, custom={RM: EX1},
                     attrs={"maxmode": 4}), {}),
    ("A_zonder_excit", "lin_static_3d",
     lambda: model_a("S30", custom={RM: EX1[:-1]}), {}),
    ("A_zonder_excit_nl", "nonlin_static_3d",
     lambda: model_a("L30", custom={RM: EX1[:-1]}), {}),
    ("A_vb3", "lin_static_3d",
     lambda: model_a("S30", custom={RM: EX1, MY: EX3}), {}),
    ("A_vb4", "nonlin_static_3d",
     lambda: model_a("L30", custom={RM: EX1, RE: EX4}), {}),
    ("A_vb4_statisch", "lin_static_3d",
     lambda: model_a("S30", custom={RM: EX1, RE: EX4}), {}),
    ("S_statisch", "lin_static_3d",
     lambda: model_s("S30", custom={MY: EX2}), {}),
    ("S_nietlin", "nonlin_static_3d",
     lambda: model_s("L30", custom={MY: EX2}), {}),
    ("T_statisch", "lin_static_3d", model_t, {}),
    ("C_lagrange", "nonlin_static_3d",
     lambda: model_c(custom={RM: ex7("Bodem")}), {}),
    ("C_vb5", "nonlin_static_3d",
     lambda: model_c(custom={RM: EX5 + ex7("Bodem")}), {}),
    ("C_penalisation", "nonlin_static_3d",
     lambda: model_c(custom={RM: ex7("Bodem")}),
     {"contact_algo": "PENALISATION"}),
    ("C_vb6", "nonlin_static_3d",
     lambda: model_c(custom={RM: EX6 + ex7("Bodem")}, stepsize="0.25 s"),
     {}),
]


def _tables(mess):
    """Regels van de tabellen 'reactie' en 'vmis_max' uit de .mess."""
    out = []
    for line in io.open(mess, encoding="utf-8", errors="replace"):
        if re.match(r"(reactie|vmis_max)\s", line):
            out.append(line.rstrip())
    return out


def run_all(root, only=()):
    if not os.path.isdir(root):
        os.makedirs(root)
    for name, analysis, build, settings in RUNS:
        if only and not any(name.startswith(o) for o in only):
            continue
        model = build()
        liml = model.write(os.path.join(root, name + ".liml"))
        cfg = os.path.join(root, name + ".json")
        json.dump({"settings": settings, "general": {}, "timeout": 900},
                  open(cfg, "w"))
        work = os.path.join(root, name)
        subprocess.call([sys.executable, os.path.join(VERIF, "_run_one.py"),
                         work, liml, analysis, cfg])
        run = json.load(io.open(os.path.join(work, "run.json"),
                                encoding="utf-8"))
        print("== %s (%s): %s %s" % (name, analysis, run.get("diagnostic"),
                                     run.get("errors")))
        if not run.get("results"):
            continue
        r = Results(run["results"], model)
        if r.modes:
            print("   modes: %s" % ", ".join(
                "%d: %.6g" % kv for kv in sorted(r.modes.items())))
        if name.startswith("A_") and not r.modes:
            nid = model.nodesel["BalkEind"][0]
            for t, d in r.steps:
                print("   t=%g BalkEind DX %.4e DY %.4e DZ %.4e" % (
                    t, d["displx"][nid], d["disply"][nid],
                    d["displz"][nid]))
        if name.startswith("S_"):
            top = model.nodesel["PlaatTop"]
            d = r.step()
            print("   PlaatTop DX gemiddeld %.4e m" % (
                sum(d["displx"][n] for n in top) / len(top)))
        if name.startswith("T_"):
            print("   Tip DZ gemiddeld %.5e m, rotatie Y %.5e rad" % (
                r.mean("displz", "Tip"), r.mean("roty", "Tip")))
        if run.get("mess"):
            for line in _tables(run["mess"]):
                print("   " + line)


def main(argv):
    if "--run" in argv:
        run_all(os.environ.get("VERIF_WORK") or os.path.join(
            tempfile.gettempdir(), "mab_voorbeelden"),
            [a for a in argv if a != "--run"])
        return
    for name, build in (("A", model_a), ("C", model_c), ("S", model_s),
                        ("T", model_t)):
        path = build().write(os.path.join(HERE, "Voorbeeld_%s.liml" % name))
        print("model", path)


if __name__ == "__main__":
    main(sys.argv[1:])
