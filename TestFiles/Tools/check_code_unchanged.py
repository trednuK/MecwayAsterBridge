# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Check that a text-only change (comments, docstrings, INFO/SUCCESS log
messages, comment lines in .comm templates) did not change any code.

    python TestFiles/Tools/check_code_unchanged.py <git-ref> [files...]

Without files: every Scripts/*.py and Scripts/*.comm that differs from
<git-ref>. Exit code 0 = all files OK, 1 = at least one problem.

Python files: the abstract syntax tree of the old version (git show
<ref>:<file>) and the new version must be identical after
  - removing docstrings (module, class, function);
  - replacing every string constant inside a log(...) call whose text
    starts with "INFO" or "SUCCESS" by its signature (prefix,
    str.format placeholders, %-specifiers);
  - replacing every string constant that consists only of comment
    lines ("#...") by its signature (number of placeholders).
Also checked: the coding line is unchanged, the new file compiles, and
the number of backslashes and triple quotes is unchanged.

.comm templates: all non-comment code (lines with their trailing comment
removed, comment-only and empty lines skipped) must be identical, the
multiset of {placeholders} and the number of literal {{ and }} must be
unchanged, and str.format with every placeholder filled must succeed.
"""
import ast
import io
import os
import re
import subprocess
import sys

_FMT = re.compile(r"(?<!\{)\{([^{}]*)\}(?!\})")
_PCT = re.compile(r"%[-+ #0]*\d*(?:\.\d+)?[sdrfgeExXc%]")


def _git_show(ref, path):
    try:
        return subprocess.check_output(
            ["git", "show", "{0}:{1}".format(ref, path.replace("\\", "/"))],
            stderr=subprocess.DEVNULL).decode("utf-8")
    except subprocess.CalledProcessError:
        return None


def _signature(text, kind):
    if kind == "log":
        prefix = text.split(":", 1)[0] if ":" in text else text[:7]
        return "<{0}|{1}|{2}>".format(prefix, sorted(_FMT.findall(text)),
                                      sorted(_PCT.findall(text)))
    return "<comment|{0}|{1}>".format(sorted(_FMT.findall(text)),
                                      sorted(_PCT.findall(text)))


def _is_comment_string(text):
    lines = [l for l in text.splitlines() if l.strip()]
    return bool(lines) and all(l.lstrip().startswith("#") for l in lines)


class _Normalize(ast.NodeTransformer):
    def _strip_doc(self, node):
        body = getattr(node, "body", None)
        if body and isinstance(body[0], ast.Expr) and \
                isinstance(body[0].value, ast.Constant) and \
                isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
        return node

    def visit_Module(self, node):
        self.generic_visit(node)
        return self._strip_doc(node)

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        return self._strip_doc(node)

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        return self._strip_doc(node)

    def visit_Call(self, node):
        func = node.func
        name = func.id if isinstance(func, ast.Name) else (
            func.attr if isinstance(func, ast.Attribute) else "")
        if name == "log":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and \
                        isinstance(sub.value, str) and \
                        sub.value.lstrip().startswith(("INFO", "SUCCESS")):
                    sub.value = _signature(sub.value, "log")
        self.generic_visit(node)
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, str) and _is_comment_string(node.value):
            node.value = _signature(node.value, "comment")
        return node


def _norm_py(src):
    tree = ast.parse(src)
    tree = _Normalize().visit(tree)
    return ast.dump(tree, include_attributes=False)


def _coding(src):
    head = src.splitlines()[:2]
    return [l for l in head if re.match(r"^#.*coding[:=]", l)]


def check_py(ref, path):
    old = _git_show(ref, path)
    new = io.open(path, encoding="utf-8").read()
    if old is None:
        return ["new file (not in {0})".format(ref)]
    errors = []
    if _coding(old) != _coding(new):
        errors.append("coding line changed")
    try:
        compile(new, path, "exec")
    except SyntaxError as exc:
        return ["does not compile: {0}".format(exc)]
    if _norm_py(old) != _norm_py(new):
        errors.append("code changed (AST differs after removing comments, "
                      "docstrings and INFO/SUCCESS texts)")
    # Docstrings are not compared above, so a lost or added backslash
    # (e.g. "\\b" in a Windows path becoming the escape "\b") or quote
    # would pass unnoticed: these counts must not change.
    for token in ("\\", '"""', "'''"):
        if old.count(token) != new.count(token):
            errors.append("number of {0!r} changed ({1} -> {2})".format(
                token, old.count(token), new.count(token)))
    return errors


def _code_lines(src):
    out = []
    for line in src.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        code = re.sub(r"\s+#[^'\"]*$", "", line).rstrip()
        out.append(code)
    return out


def check_comm(ref, path):
    old = _git_show(ref, path)
    new = io.open(path, encoding="utf-8").read()
    if old is None:
        return ["new file (not in {0})".format(ref)]
    errors = []
    if _code_lines(old) != _code_lines(new):
        errors.append("code lines changed")
    if sorted(_FMT.findall(old)) != sorted(_FMT.findall(new)):
        errors.append("placeholders changed")
    if (old.count("{{"), old.count("}}")) != (new.count("{{"),
                                              new.count("}}")):
        errors.append("number of literal braces changed")
    try:
        new.format(**dict((k, "0") for k in _FMT.findall(new) if k))
    except (KeyError, IndexError, ValueError) as exc:
        errors.append("str.format fails: {0!r}".format(exc))
    return errors


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    ref = argv[1]
    files = argv[2:]
    if not files:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", ref, "--", "Scripts/*.py",
             "Scripts/*.comm"]).decode("utf-8")
        files = [f for f in out.splitlines() if f.strip()]
    bad = 0
    for path in files:
        if path.endswith(".py"):
            errors = check_py(ref, path)
        elif path.endswith(".comm"):
            errors = check_comm(ref, path)
        else:
            continue
        status = "OK" if not errors else "FOUT: " + "; ".join(errors)
        print("{0}: {1}".format(path, status))
        bad += bool(errors)
    print("{0} file(s) checked, {1} with problems".format(len(files), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
