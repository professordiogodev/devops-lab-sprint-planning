#!/usr/bin/env python3
"""Checks sprint-plan.md against the backlog, the team availability and the velocity. Run: python3 verify.py"""
import csv, math, re, sys

def rows(f): return list(csv.DictReader(open(f, encoding="utf-8")))
backlog = {r["id"]: r for r in rows("backlog.csv")}
team = rows("team.csv"); vel = rows("velocity.csv")
avg_velocity = sum(int(v["completed"]) for v in vel) / len(vel)
avail = sum(int(t["days_available"]) for t in team) / sum(int(t["days_in_sprint"]) for t in team)
capacity = math.floor(avg_velocity * avail)

passed = failed = 0
def check(desc, ok):
    global passed, failed
    print(("PASS  " if ok else "FAIL  ") + desc)
    if ok: passed += 1
    else: failed += 1

try: text = open("sprint-plan.md", encoding="utf-8").read()
except FileNotFoundError:
    print("FAIL  sprint-plan.md does not exist"); print("1 check(s) failed, 0 passed"); sys.exit(1)

def section(name):
    m = re.search(r"^##\s+" + name + r"[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.S | re.M | re.I)
    return m.group(1) if m else ""

backlog_sec = section("Sprint backlog")
items = []   # (id, points, parent)
for line in backlog_sec.splitlines():
    m = re.match(r"^\s*[-*]\s*(S\d\d[a-z]?)\s*\((\d+)\s*pts?\)", line, re.I)
    if m:
        sid, pts = m.group(1), int(m.group(2))
        items.append((sid, pts, sid[:3]))
ids = [i[0] for i in items]

print(f"(capacity for this sprint: {capacity} points = average velocity {avg_velocity:.0f} x availability {avail:.3f})")
print("== The plan is well formed ==")
check("sprint-plan.md has a '## Sprint backlog' with lines like '- S01 (2 pts): ...'", len(items) >= 3)
check("every story id exists in backlog.csv", all(i[2] in backlog for i in items) and len(items) > 0)
check("no story appears twice", len(ids) == len(set(ids)))

print("== The numbers ==")
total = sum(i[1] for i in items)
check(f"total points ({total}) do not exceed the capacity ({capacity})", 0 < total <= capacity)
check(f"total points are at least 80% of capacity (>= {math.ceil(0.8*capacity)})", total >= math.ceil(0.8 * capacity))
whole = [i for i in items if i[0] == i[2]]
check("no unsplit story is larger than 8 points (13-point stories must be sliced)", all(backlog[i[0]]["points"].isdigit() and int(backlog[i[0]]["points"]) <= 8 for i in whole if i[0] in backlog))
check("whole stories use the estimate from backlog.csv", all(i[1] == int(backlog[i[0]]["points"]) for i in whole if i[0] in backlog))
slices = [i for i in items if i[0] != i[2]]
check("a slice is never bigger than its parent story", all(i[2] in backlog and i[1] <= int(backlog[i[2]]["points"]) for i in slices))
check("at most one spike", sum(1 for i in items if i[2] in backlog and backlog[i[2]]["type"] == "spike") <= 1 or len({i[2] for i in items if i[2] in backlog and backlog[i[2]]["type"] == "spike"}) <= 1)

print("== Priorities and dependencies ==")
musts = [k for k, v in backlog.items() if v["must"] == "yes"]
check("all 'must' stories are in the sprint: " + ", ".join(musts), all(m in {i[2] for i in items} for m in musts))
pos = {}
for n, (sid, _, parent) in enumerate(items): pos.setdefault(parent, n)
dep_ok = True; msg = []
for sid, _, parent in items:
    if parent not in backlog: continue
    dep = backlog[parent]["depends_on"]
    if dep and (dep not in pos or pos[dep] > pos[parent]):
        dep_ok = False; msg.append(f"{parent} needs {dep} listed before it")
check("every story's dependency is in the sprint AND listed before it" + (": " + "; ".join(msg) if msg else ""), dep_ok)

# value: compare with the best possible knapsack within capacity (ignoring dependencies, as an upper bound)
vals = [(int(v["points"]), int(v["value"])) for v in backlog.values() if int(v["points"]) <= 8]
best = [0] * (capacity + 1)
for p, v in vals:
    for c in range(capacity, p - 1, -1): best[c] = max(best[c], best[c - p] + v)
mine = sum(int(backlog[i[0]]["value"]) for i in whole if i[0] in backlog)
check(f"business value delivered ({mine}) is at least 60% of the best possible ({best[capacity]})", mine >= 0.6 * best[capacity])

print("== The conversation with the team ==")
goal = " ".join(section("Sprint goal").split())
check("a Sprint goal of 10-40 words (one outcome, not a list of ticket ids)", 10 <= len(goal.split()) <= 40 and len(re.findall(r"S\d\d", goal)) <= 1)
left = [l for l in section("Left out").splitlines() if re.match(r"^\s*[-*]\s*S\d\d", l)]
check("'## Left out' explains at least 3 stories, each with a reason of 5+ words", len(left) >= 3 and all(len(re.sub(r"^\s*[-*]\s*S\d\d[a-z]?\s*:?", "", l).split()) >= 5 for l in left))
left_ids = {re.search(r"S\d\d", l).group(0) for l in left}
check("nothing is both in the sprint and left out", not (left_ids & {i[2] for i in items}))
dod = [l for l in section("Definition of Done").splitlines() if re.match(r"^\s*[-*]\s*\S", l)]
check("'## Definition of Done' has at least 3 bullets", len(dod) >= 3)
risks = [l for l in section("Risks").splitlines() if re.match(r"^\s*[-*]\s*\S", l)]
check("'## Risks' names at least 2 risks", len(risks) >= 2)

print()
if failed == 0: print(f"ALL CHECKS PASSED ({passed}/{passed})")
else: print(f"{failed} check(s) failed, {passed} passed")
sys.exit(1 if failed else 0)
