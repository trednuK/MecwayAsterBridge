# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the model copy in <solution configuration="X">
# (Scripts/bridge_results_liml.py), Python 2.7 (IronPython) and 3:
#   - the model copy per configuration has the same element/attribute
#     structure as Mecway's own solution (no <configuration> definitions,
#     no <suppressed configuration=".."/> children, suppressed="true" on the
#     items suppressed in X, self-closing items without children);
#   - splice_results (IronPython 2.7.9 only: it works on byte strings)
#     writes that copy in the ULS solution and leaves the stub solutions of
#     the other configurations and the model byte-identical. Under CPython
#     this part runs through TestFiles/Tools/run_ipy.ps1 if Mecway is
#     installed (otherwise skipped).
#
# Fixtures in tests/data:
#   config_model.liml             LS-20a with configurations G, Q, ULS plus a
#                                 <fixed>, a named <force> and <group>s
#                                 suppressed per configuration, as Mecway 34
#                                 saves it (stub solution per configuration)
#   config_model_mecway_sol.liml  Mecway 34's own headless solution of that
#                                 model (mecway.exe <model> solve), result
#                                 values and <solutionfile> removed
#   config_model_results.xml      a result fragment (aster_results_export) of
#                                 the same mesh
#
#   python tests/test_results_configuration.py

from __future__ import print_function

import io
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
_SCRIPTS = os.path.join(_HERE, "..", "Scripts")
sys.path.insert(0, _SCRIPTS)
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
import bridge_results_liml as brl  # noqa: E402

DATA = os.path.join(_HERE, "data")
MODEL = os.path.join(DATA, "config_model.liml")
MECWAY_SOL = os.path.join(DATA, "config_model_mecway_sol.liml")
FRAGMENT = os.path.join(DATA, "config_model_results.xml")
IRONPYTHON = sys.platform == "cli"


def check(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        check.failed = True


check.failed = False


def _read(path):
    f = io.open(path, encoding="utf-8", newline="")
    try:
        return f.read()
    finally:
        f.close()


def _structure(elem):
    """(tag, attributes, children) without text, results and
    <solutionfile>."""
    return (elem.tag, sorted(elem.attrib.items()),
            [_structure(c) for c in elem
             if c.tag not in ("results", "solutionfile")])


def _solutions(text):
    """{configuration: structure of the solution body}."""
    root = ET.fromstring(text.encode("utf-8"))
    return dict((s.get("configuration"), _structure(s)[2])
                for s in root.findall("solution"))


def _copy_structure(text, configuration):
    """Structure of the model copy for configuration, as splice_results
    builds it (_solution_copy), parsed inside a <solution>."""
    head = text[:text.index("<solution")]
    nl = brl._newline(head)
    lines = brl._solution_copy(head, nl, configuration)
    body = nl.join(lines)
    elem = ET.fromstring((u"<solution>" + body + u"</solution>")
                         .encode("utf-8"))
    return _structure(elem)[2], body


model = _read(MODEL)
expected = _solutions(_read(MECWAY_SOL))
check("fixture: Mecway solution for G, Q and ULS",
      sorted(expected) == ["G", "Q", "ULS"])

# 1. The model copy per configuration equals Mecway's own solution
for conf in ("G", "Q", "ULS"):
    got, body = _copy_structure(model, conf)
    check("model copy {0} has Mecway's structure".format(conf),
          got == expected[conf])
    check("model copy {0} without <configuration>/<suppressed>".format(conf),
          "<configuration" not in body and "<suppressed" not in body)
    check("model copy {0} without empty lines".format(conf),
          all(l.strip() for l in body.split(brl._newline(body))))

# Exactly Mecway's lines for the items with suppressed children (ULS)
_got, body = _copy_structure(model, "ULS")
for line in ('    <gravity suppressed="true">',
             '    <traction selection="Eindvlak" suppressed="true">',
             '    <fixed selection="SymX" suppressed="true" />',
             '    <force selection="Eindknopen" name="extra" group="Grp" '
             'suppressed="true">',
             '    <group name="Grp" />'):
    check("ULS line {0}".format(line.strip()), line in body.split("\r\n"))

# 2. Without configurations: the copy is unchanged (byte-identical splice)
head = model[:model.index("<solution")]
nl = brl._newline(head)
check("no configuration: _solution_copy == _model_copy",
      brl._solution_copy(head, nl, None) == brl._model_copy(head, nl))
plain = (u'  <analysis type="S30" />\r\n  <gravity>\r\n    <x>1 m/s\u00b2</x>'
         u'\r\n  </gravity>\r\n  <group name="A" suppressed="true" />')
check("text without configurations unchanged",
      brl._configuration_copy(plain, "X", "\r\n") == plain)

# Hand-written style (TestFiles/Verificatie/modellen/LS-20a.liml): children
# on one line
inline = (u'  <configuration name="G" />\r\n  <configuration name="Q" />\r\n'
          u'  <gravity><x>9.81 m/s\u00b2</x><suppressed configuration="Q" />'
          u'</gravity>\r\n'
          u'  <fixed selection="A"><suppressed configuration="Q" /></fixed>'
          u'\r\n  <mat name="S" />')
check("one-line items",
      brl._configuration_copy(inline, "Q", "\r\n") ==
      u'  <gravity suppressed="true"><x>9.81 m/s\u00b2</x></gravity>\r\n'
      u'  <fixed selection="A" suppressed="true" />\r\n  <mat name="S" />')


# 3. splice_results itself (IronPython: byte strings)
def splice_check(work):
    """Splice into a copy of the fixture model with configuration ULS and
    check the result; returns the spliced text."""
    liml = os.path.join(work, "model.liml")
    shutil.copy(MODEL, liml)
    conf, warning = brl.pick_configuration(liml)
    ok, reason = brl.splice_results(liml, FRAGMENT, liml, "ULS")
    check("splice_results ok ({0})".format(reason), ok)
    text = _read(liml)
    got = _solutions(text)
    check("spliced ULS solution has Mecway's structure",
          got.get("ULS") == expected["ULS"])
    check("ULS solution contains the results",
          '<results precision="double">' in
          text[text.index('<solution configuration="ULS">'):])
    old = _read(MODEL)
    start = text.index('<solution configuration="ULS">')
    check("model and stub solutions G, Q unchanged",
          text[:start] == old[:old.index('<solution configuration="ULS">')])
    check("end of the file unchanged",
          text.endswith(u"  </solution>\r\n</liml>") and
          old.endswith(u"  </solution>\r\n</liml>"))
    return conf


if IRONPYTHON:
    work = tempfile.mkdtemp()
    try:
        splice_check(work)
    finally:
        shutil.rmtree(work, True)
else:
    ps = os.path.join(_HERE, "..", "TestFiles", "Tools", "run_ipy.ps1")
    if sys.platform == "win32" and os.path.isdir(
            r"C:\Program Files\Mecway") and os.path.exists(ps):
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", os.path.abspath(ps), "-Script",
             os.path.abspath(__file__)])
        out = out.decode("utf-8", "replace")
        print("--- IronPython 2.7.9 ---")
        print(out.strip())
        check("IronPython run without failures",
              "FAIL" not in out and "FOUT" not in out and
              "All tests passed." in out)
    else:
        print("SKIP splice_results (needs Mecway's IronPython)")

if check.failed:
    sys.exit(1)
print("All tests passed.")
