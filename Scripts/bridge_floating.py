# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_floating.py
# Responsibility: before the run, find parts of the mesh that are held in
# place only by contact (no support, bonded contact, coupling, spring or
# constraint of their own) in a nonlinear static analysis, and say how to
# fix the model. Called by bridge_mesh.write_mesh.
#
# Why (Samples/BoltedJoint, Code-Aster 17.4, 28 Oct 2026): plate B is only
# held by friction contact against plate A and by frictionless contact
# against the nut. Code-Aster's STAT_NON_LINE starts with the tangent
# matrix of the undeformed state: the contact (CONTINUE) and its Coulomb
# friction give no stiffness in the tangential directions at a zero
# contact pressure, so the part has a free rigid-body motion and MUMPS
# stops in the first step with a zero pivot on a physical DOF of that
# part (MECANONLINE9_4, "matrice non inversible"; pivot on DZ of a plate-B
# node). Mecway's CCX penalty contact (*SURFACE BEHAVIOR, PRESSURE-
# OVERCLOSURE=LINEAR with a stick slope) carries it from the start, so
# Mecway computes the model. The same holds for the side of a bolt behind a
# pre-tension section with a force (bridge_pretension): that force is a
# load, the tie gives no stiffness along the axis; with CONTACT_INIT='NON'
# or FORMULATION='DISCRETE' Code-Aster then stops with a zero pivot on DY
# of a bolt node. A weak Elastic support on a large face of each such part
# removes these pivots (checked on BoltedJoint, KNOWN_BUGS 43).
# Mecway's own tutorial AssemblyWithContact (manual v34 par. 17.7) shows the
# same: its Naive configuration fails in Mecway too (parts held only by
# frictionless contact); its remedies are a fixed support, friction, a weak
# elastic support and a gentler load ramp. This check reports Naive as well.
# The bridge does not add supports itself (user's choice: clear messages,
# no automatic fixes); it reports the part with the remedies (WARNING).
#
# Compatible with IronPython 2.7.9.

from collections import OrderedDict

from bridge_utils import log, tr, get_active_analysis

# Conditions that hold a node (fully or partly); compression only is
# one-sided like contact and does not count.
_SUPPORT_BCS = frozenset(["fixed", "pinnedsupport", "displacement",
                          "frictionless", "symmetry", "velocity",
                          "elasticsupport", "noderotation"])


def _parent(par, a):
    while par[a] != a:
        par[a] = par[par[a]]
        a = par[a]
    return a


def _union(par, a, b):
    ra, rb = _parent(par, a), _parent(par, b)
    if ra != rb:
        par[rb] = ra


def _nid(value):
    s = str(value)
    return int(s[1:]) if s.startswith("N") else int(s)


def check(model_data, nodes, conn, cells, elements, group_face_list):
    """
    WARNING per part (connected set of nodes over elements, bonded
    contact, couplings and constraint equations) without any support that
    touches a contact face, in STAT_NON_LINE with contact. A pre-tension
    section with a force does not connect its two sides (the force is a
    load). Sets model_data["floating_parts"] ([{"elements", "elsets",
    "contacts", "pretension"}]) and returns it.

    nodes: Mecway nodes {nid: xyz}; conn: {eid: (aster_type, [nid])};
    cells: {eid: [nid]} as written to the mesh (with the copies of a
    pre-tension section, bridge_pretension);
    elements: [(eid, shape, nodes, elset)]; group_face_list: {Mecway face
    selection: [{"nodes", "eid", ...}]} (bridge_mesh.write_mesh, step 2).
    """
    model_data["floating_parts"] = []
    contacts = [c for c in model_data.get("contacts", [])
                if c.get("master") and c.get("slave")]
    try:
        cmd = get_active_analysis().get("solver_command")
    except (KeyError, TypeError, AttributeError):
        cmd = None
    if not contacts or cmd != "STAT_NON_LINE":
        return []
    node_groups = model_data.get("node_groups", {})
    elem_sel = model_data.get("element_selections", {})

    def sel_nodes(name):
        if name in group_face_list:
            return set(n for f in group_face_list[name] for n in f["nodes"])
        if name in node_groups:
            return set(_nid(i) for i in node_groups[name])
        if name in elem_sel:
            return set(n for e in elem_sel[name] if e in conn
                       for n in conn[e][1])
        return set()

    par = {}

    def add(n):
        if n not in par:
            par[n] = n

    for eid, cn in cells.items():
        for n in cn:
            add(n)
        for n in cn[1:]:
            _union(par, cn[0], n)
    for b in model_data.get("bonded", []):
        ns = sel_nodes(b.get("master")) | sel_nodes(b.get("slave"))
        ns = [n for n in ns if n in par]
        for n in ns[1:]:
            _union(par, ns[0], n)
    for c in model_data.get("couplings", []):
        ns = list(sel_nodes(c.get("master_group")) |
                  sel_nodes(c.get("slave_group")))
        for n in ns:
            add(n)
        for n in ns[1:]:
            _union(par, ns[0], n)
    for ce in model_data.get("constraint_equations", []):
        if ce.get("pretension_force"):
            continue        # a force across the section: no stiffness
        ns = [t[0] for t in ce.get("terms", [])]
        for n in ns:
            add(n)
        for n in ns[1:]:
            _union(par, ns[0], n)
    supported = set()
    for bc in model_data.get("bcs", []):
        if bc.get("type") not in _SUPPORT_BCS:
            continue
        if bc.get("type") == "elasticsupport":
            # translated as springs to ground (bridge_mesh._build_discretes
            # sets skip); only with a stiffness
            p = bc.get("params", {})
            if not (p.get("kn", 0.0) > 0.0 or p.get("kt", 0.0) > 0.0):
                continue
        elif bc.get("skip"):
            continue
        for n in sel_nodes(bc.get("selection")):
            if n in par:
                supported.add(_parent(par, n))
    touching = OrderedDict()            # root -> [contact selection names]
    for c in contacts:
        for key in ("master", "slave"):
            for n in sel_nodes(c[key]):
                if n in par:
                    r = _parent(par, n)
                    names = touching.setdefault(r, [])
                    if c[key] not in names:
                        names.append(c[key])
    friction = dict((c[k], c.get("friction", 0.0) or 0.0)
                    for c in contacts for k in ("master", "slave"))
    elsets = dict((e[0], e[3]) for e in elements)
    pret_sides = set()
    for ce in model_data.get("constraint_equations", []):
        if ce.get("pretension_force"):
            for t in ce.get("terms", []):
                if t[0] in par:
                    pret_sides.add(_parent(par, t[0]))
    parts = OrderedDict()
    for eid, cn in cells.items():
        parts.setdefault(_parent(par, cn[0]), []).append(eid)
    found = []
    for root, eids in parts.items():
        if root in supported or root not in touching:
            continue
        eids = sorted(eids)
        pts = [nodes[n] for e in eids for n in conn[e][1] if n in nodes]
        box = [(min(p[k] for p in pts), max(p[k] for p in pts))
               for k in range(3)]
        info = {"elements": eids,
                "elsets": sorted(set(elsets.get(e, "?") for e in eids)),
                "contacts": touching[root],
                "friction": any(friction.get(s, 0.0) > 0.0
                                for s in touching[root]),
                "pretension": root in pret_sides, "box": box}
        found.append(info)
        _report(info)
    model_data["floating_parts"] = found
    return found


def _report(info):
    eids = info["elements"]
    ids = ", ".join(str(e) for e in eids[:8]) + (" ..." if len(eids) > 8
                                                 else "")
    box = ", ".join("%s %.4g..%.4g m" % (ax, lo, hi)
                    for ax, (lo, hi) in zip("xyz", info["box"]))
    sels = ", ".join("'{0}'".format(s) for s in info["contacts"])
    comps = ", ".join("'{0}'".format(s) for s in info["elsets"])
    pret_nl = pret_en = ""
    if info["pretension"]:
        pret_nl = (u" en door de kracht van een pre-tension section (een "
                   u"last, geen stijfheid langs de bout)")
        pret_en = (u" and by the force of a pre-tension section (a load, "
                   u"no stiffness along the bolt)")
    fric_nl = fric_en = ""
    if info["friction"]:
        fric_nl = (u" Met wrijving convergeert Code-Aster's Coulomb-"
                   u"wrijving (CONTINUE) op Samples/BoltedJoint ook met "
                   u"deze steun niet (KNOWN_BUGS 43); zonder wrijving wel.")
        fric_en = (u" With friction, Code-Aster's Coulomb friction "
                   u"(CONTINUE) does not converge on Samples/BoltedJoint "
                   u"even with this support (KNOWN_BUGS 43); without "
                   u"friction it runs.")
    log(tr(u"WARNING: Een deel van {0} element(en) (component {1}; elementen "
           u"{2}; {3}) wordt alleen door contact op zijn plaats gehouden "
           u"({4}){5}: het heeft geen eigen oplegging, verlijmd contact, "
           u"koppeling of veer. Code-Aster begint met de stijfheid zonder "
           u"contactdruk; dat deel kan dan vrij bewegen en de berekening "
           u"stopt in de eerste stap met MECANONLINE9_4 (pivot nul). "
           u"Mecway's penalty-contact (CCX) houdt het wel vast. Pas het "
           u"model in Mecway aan: (1) een zwakke Elastic support op een "
           u"groot vlak van dit deel (stijfheid x oppervlak orde 1e-5 .. "
           u"1e-4 van E x A / L van het deel, op een groot vlak zodat ook "
           u"de rotaties vastliggen), (2) een oplegging waar het deel echt "
           u"vastzit (Fixed, Frictionless, Displacement), of (3) verlijmd "
           u"contact als het niet mag schuiven of loskomen{6}. Zie "
           u"docs/Instellingen_contact_en_nietlineair.md par. 3.11.{7}",
           u"WARNING: A part of {0} element(s) (component {1}; elements "
           u"{2}; {3}) is held in place only by contact ({4}){5}: it has "
           u"no support, bonded contact, coupling or spring of its own. "
           u"Code-Aster starts with the stiffness at zero contact pressure; "
           u"that part can then move freely and the analysis stops in the "
           u"first step with MECANONLINE9_4 (zero pivot). Mecway's penalty "
           u"contact (CCX) does hold it. Adapt the model in Mecway: (1) a "
           u"weak Elastic support on a large face of this part (stiffness "
           u"x area of the order 1e-5 .. 1e-4 of E x A / L of the part, on "
           u"a large face so that the rotations are held too), (2) a "
           u"support where the part is really held (Fixed, Frictionless, "
           u"Displacement), or (3) bonded contact if it may not slide or "
           u"separate{6}. See docs/en/Settings_contact_and_nonlinear.md "
           u"par. 3.11.{7}").format(
               len(eids), comps, ids, box, sels,
               pret_nl if tr("nl", "en") == "nl" else pret_en,
               tr(u"; bij een pre-tension section ook: kies Length "
                  u"adjustment in plaats van Force",
                  u"; with a pre-tension section also: choose Length "
                  u"adjustment instead of Force")
               if info["pretension"] else "",
               fric_nl if tr("nl", "en") == "nl" else fric_en))
