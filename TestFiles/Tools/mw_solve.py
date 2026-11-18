# Let Mecway solve headless (reference for the verification, no GUI needed).
# Usage (CPython): python mw_solve.py <in.liml> <out_base>  -> <out>_sol.liml
# Mecway solves with the solver of <analysis> (solver="ccx" for CCX). Reading the
# result: aster_results_export format, see TestFiles/Verificatie/verif_lib.py.
# Mecway 36 with CCX returns a beam on the hex8/hex20 elements CCX expands it into,
# with their own node numbers (4 or 8 nodes around the section per beam node): read a
# beam node as the mean of the solution nodes around it, not by node id (only
# displacements checked this way, on LS-50, NL-82, NL-83). verif_lib.Results does
# not do this: it reads node ids, so average the nodes before evaluating a check.
# Environment: MWT = time limit in s (default 300).
import sys, os, io, re, subprocess, time
# hidden, with the dialog watchdog of the verification (verif_lib.run_mecway;
# the solver window of a solve is normal, so only dialogs and the time limit
# stop it)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "Verificatie"))
import verif_lib
src, base = sys.argv[1], os.path.abspath(sys.argv[2])
txt = io.open(src, encoding="utf-8").read()
txt = re.sub(r"\s*<solution>.*?</solution>", "", txt, flags=re.S)
txt = re.sub(r"\s*<solutionfile[^>]*/>", "", txt, flags=re.S)
sol = base + "_sol.liml"
if os.path.exists(sol): os.remove(sol)
txt = txt.replace("</liml>", '  <solutionfile filename="{0}" />\n</liml>'.format(sol.replace("/", "\\")))
inp = base + "_in.liml"
io.open(inp, "w", encoding="utf-8").write(txt)
t0 = time.time()
state, rc, wins = verif_lib.run_mecway(
    [r"C:\Program Files\Mecway\mecway.exe", inp.replace("/", "\\"), "solve"],
    timeout=float(os.environ.get("MWT", "300")), other_grace=None)
if state == "ok":
    print("exit", rc, "%.1f s" % (time.time() - t0))
else:
    print(state.upper(), wins)
print("solution:", os.path.exists(sol), os.path.getsize(sol) if os.path.exists(sol) else 0)
