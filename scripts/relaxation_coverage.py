"""
My Body Coach 3: which exercises count toward Master of Breathing / Master of Relaxation,
and in which ListCombination contexts (muscle group / position / user level) each can be drawn.
For each exercise it also lists the relaxation session type that can contain it, the goals whose
programs schedule that session type/position, and the relaxation-level slider settings that reach
its level(s) (see session_plan.py for the rules taken from the executable).
Usage: python3 relaxation_coverage.py <game>/Common/Scripts  > relaxation_exercises.csv
"""
import re, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session_plan as SP
S = sys.argv[1]
src = open(os.path.join(S, 'Exercises.lua'), encoding='latin-1').read()
body = src[src.index('\nExercises ='):]
ents = []; depth = 0; pos = body.index('{') + 1; start = name = None
while pos < len(body):
    c = body[pos]
    if body.startswith('--', pos): pos = body.find('\n', pos); pos = len(body) if pos < 0 else pos; continue
    if c == '"': pos = body.find('"', pos + 1) + 1; continue
    if c == '{':
        if depth == 0:
            m = re.search(r'([A-Za-z0-9_]+)\s*=\s*$', body[max(0, pos - 120):pos]); name = m and m.group(1); start = pos
        depth += 1
    elif c == '}':
        if depth == 0: break
        depth -= 1
        if depth == 0: ents.append((name, body[start:pos + 1]))
    pos += 1
rows = []
for n, b in ents:
    t = re.search(r'\bType\s*=\s*ExerciseType\.(\w+)', b); g = re.search(r'\bGroup\s*=\s*MuscleGroup\.(\w+)', b)
    rows.append((n, t and t.group(1), g and g.group(1)))
lc = re.sub(r'--[^\n]*', '', open(os.path.join(S, 'ListCombination.cfg'), encoding='latin-1').read())
stack = []; pend = None; where = collections.defaultdict(set)
for m in re.finditer(r'\[(\w+)\.(\w+)\]\s*=|"([A-Z0-9_]+)"|[{}]', lc):
    t = m.group(0)
    if m.group(1): pend = m.group(2); continue
    if t == '{': stack.append(pend); pend = None; continue
    if t == '}': stack.pop(); continue
    if m.group(3) and len(stack) >= 4: where[m.group(3)].add(tuple(stack[1:4]))
GROUP_SESSION = {g: t for t, gs in SP.SESSION_GROUPS.items() for g in gs}
LEVEL_VALUE = {v: k for k, v in SP.LEVEL.items()}
def goals_for(ctx):
    out = set()
    for g in SP.GOALS:
        sched = {SP.relaxation_of_session(g, k) for k in range(4)}
        if any((GROUP_SESSION.get(grp), pos) in sched for grp, pos, lvl in ctx): out.add(g)
    return out
def sliders_for(ctx):
    lv = {LEVEL_VALUE[l] for _, _, l in ctx}
    return [SP.SLIDER[v] for v in SP.SLIDER if any(l in lv for l, _ in SP.levels_of_slider(v))]
print('exercise,type,group,levels,positions,combination_groups,relaxation_session,goals,slider_settings,note')
for n, t, g in rows:
    if t not in ('Pilates', 'Breath', 'Suppleness'): continue
    w = where.get(n, set())
    lv = '|'.join(sorted({x[2] for x in w})); ps = '|'.join(sorted({x[1] for x in w})); gs = '|'.join(sorted({x[0] for x in w}))
    note = 'breathing intro only (counted as Breath)' if not w and g == 'BreathNoMove' else ('NOT IN ANY COMBINATION' if not w else ('single level' if len({x[2] for x in w}) == 1 else ''))
    ses = '|'.join(sorted({GROUP_SESSION.get(x[0], '?') for x in w})) or ('any (breathing intro)' if g == 'BreathNoMove' else '')
    gl = '|'.join(SP.GOALS[x] for x in sorted(goals_for(w))) if w else ('any' if g == 'BreathNoMove' else '')
    sl = '|'.join(sliders_for(w)) if w else ('any' if g == 'BreathNoMove' else '')
    print(f'{n},{t},{g},{lv},{ps},{gs},{ses},{gl},{sl},{note}')
