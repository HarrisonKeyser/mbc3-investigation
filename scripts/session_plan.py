"""
My Body Coach 3: which relaxation exercises a session can contain.

Re-implements three pieces of default.xex (EUR):
  * 0x821e98f0  program planner: relaxation exercise type + position of the k-th session of a program,
                chosen only from the goal ("objective") and k
  * 0x821ec648  SetRelaxUserLevel: slider value 0/5/10/15/20 -> base level (0/10/20) + "half step" flag
  * 0x821e5260  relaxation-session builder: with the half-step flag, the first half of the relaxation
                time uses the next level up, the rest uses the base level

Usage: python3 session_plan.py            (prints the tables)
"""
GOALS = {1: 'Lose weight', 2: 'Peace and calm', 3: 'An active and balanced life', 4: 'Tone your look'}
SLIDER = {0: 'Anguished', 5: 'Agitated', 10: 'Worried', 15: 'Fairly calm', 20: 'Serene'}
LEVEL = {0: 'Newb', 10: 'Normal', 20: 'Pro'}
PILATES, BREATH, SUPPLENESS = 'Pilates', 'Breath', 'Suppleness'
STAND, FLOOR = 'Stand', 'Floor'


def relaxation_of_session(goal, k):
    """0x821e98f0: (exercise type, position) of the relaxation part of session k (0-based) of a program."""
    if goal == 1:   # 0x821e999c
        return (PILATES if k % 2 == 0 else SUPPLENESS), (STAND if k % 4 in (0, 1) else FLOOR)
    if goal == 2:   # 0x821e99f4
        return (BREATH if k % 2 == 0 else PILATES), (FLOOR if k % 4 == 3 else STAND)
    if goal == 3:   # 0x821e9a60
        return (PILATES if k % 2 == 0 else BREATH), (FLOOR if k % 4 == 2 else STAND)
    if goal == 4:   # 0x821e9aec
        return PILATES, (FLOOR if k % 2 else STAND)
    # anything else keeps the defaults None/Any, which 0x821e7060 turns into Pilates/Stand
    return PILATES, STAND


def levels_of_slider(v):
    """0x821ec648 + 0x821e5260: list of (level, share of the relaxation time)."""
    base, half = (v // 10) * 10, v % 10
    if not half:
        return [(base, 1.0)]
    first = base + 10 if base < 20 else base
    return [(first, half / 10), (base, 1 - half / 10)]


# which ListCombination muscle groups each relaxation session type draws from (0x821e5260)
SESSION_GROUPS = {PILATES: ('Postural', 'Support'), BREATH: ('BreathMove',), SUPPLENESS: ('Suppleness',)}

if __name__ == '__main__':
    print('Relaxation part of each programmed session (repeats every 4 sessions):')
    for g, name in GOALS.items():
        print(f'  {name:28s}', ' | '.join('%s %s' % relaxation_of_session(g, k) for k in range(4)))
    print('\nRelaxation level slider:')
    for v, name in SLIDER.items():
        print(f'  {name:12s} ({v:2d}) ->', ' then '.join(f'{LEVEL[l]} ({int(s * 100)}% of the time)' for l, s in levels_of_slider(v)))
    print('\nSession types available per goal:')
    for g, name in GOALS.items():
        ctx = sorted({relaxation_of_session(g, k) for k in range(4)})
        print(f'  {name:28s}', ', '.join('%s/%s' % c for c in ctx))
