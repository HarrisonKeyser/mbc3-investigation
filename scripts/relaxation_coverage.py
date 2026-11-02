"""
My Body Coach 3: which exercises count toward Master of Breathing / Master of Relaxation,
and in which ListCombination contexts (muscle group / position / user level) each can be drawn.
Usage: python3 relaxation_coverage.py <game>/Common/Scripts  > relaxation_exercises.csv
"""
import re, sys, os, collections
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
print('exercise,type,group,levels,positions,combination_groups,note')
for n, t, g in rows:
    if t not in ('Pilates', 'Breath', 'Suppleness'): continue
    w = where.get(n, set())
    lv = '|'.join(sorted({x[2] for x in w})); ps = '|'.join(sorted({x[1] for x in w})); gs = '|'.join(sorted({x[0] for x in w}))
    note = 'breathing intro only (counted as Breath)' if not w and g == 'BreathNoMove' else ('NOT IN ANY COMBINATION' if not w else ('single level' if len({x[2] for x in w}) == 1 else ''))
    print(f'{n},{t},{g},{lv},{ps},{gs},{note}')
