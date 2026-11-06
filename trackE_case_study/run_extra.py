"""Extra Track E checks: (1) is the weak annealing at 150x28 a budget/temperature issue? (2) where does the ILP start to strain?"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import roster as R
P = os.path.join(HERE, "results", "results.json")
res = json.load(open(P))
inst = R.make_instance(150, 28, seed=0)
g = R.greedy(inst)
ilp_obj = res["sizes"]["150x28"]["raw"][0]["ilp"]["objective"]
rows = []
for iters, t0 in ((400_000, 2.0), (400_000, 0.5), (400_000, 0.2), (1_500_000, 0.5)):
    t = time.perf_counter()
    best, _ = R.anneal(inst, g, iters=iters, t0=t0, t1=0.02, seed=0)
    o = R.evaluate(inst, best)["objective"] if best is not None else None
    rows.append(dict(iters=iters, t0=t0, objective=o, gap_to_ilp_pct=None if o is None else 100 * (o - ilp_obj) / ilp_obj,
                     seconds=time.perf_counter() - t))
    print(rows[-1], flush=True)
res["annealing_sensitivity_150x28_seed0"] = dict(ilp_objective=ilp_obj, greedy_objective=R.evaluate(inst, g)["objective"], rows=rows,
                                                 note="single instance, single seed: indicative only")
probe = []
for W, D in ((300, 28), (600, 28)):
    inst = R.make_instance(W, D, seed=0)
    a, info = R.ilp(inst, 60.0)
    probe.append(dict(workers=W, days=D, variables=W * D * R.S, seconds=info["seconds"], proven_optimal=info.get("proven_optimal"),
                      gap=info.get("gap"), objective=info.get("objective")))
    print(probe[-1], flush=True)
res["ilp_scaling_probe"] = probe
json.dump(res, open(P, "w"), indent=1, default=float)
