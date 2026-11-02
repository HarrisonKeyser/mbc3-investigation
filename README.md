# My Body Coach 3 (Xbox 360): achievements and the "endless saving" bug

Static analysis of the EUR build (`default.xex` plus its Lua scripts). It covers how every achievement is actually unlocked, why some look broken, and what can make the end-of-session save hang forever.

All addresses are virtual addresses in the decrypted `default.xex` (base `0x82000000`). Annotated listings are in [`evidence/disassembly.txt`](evidence/disassembly.txt).

## TL;DR

| Problem | What the code shows |
|---|---|
| **"Saving…" never finishes** | Saves and achievement unlocks share **one background thread** that runs jobs one at a time. Before writing, the save checks the storage device. That check contains **two waits with no timeout**, one for the Xbox Guide/system UI to close and one for the storage-device selector to return. If either never resolves, the job never finishes, and the game shows "Saving…" forever. **Everything from that session is lost**, including Zen, relaxation time and exercises completed. |
| **Master of Relaxation** (no known legit unlock) | It isn't impossible in code, but it's extremely demanding. You must complete **every one of 129 relaxation exercises** (61 Pilates + 22 Breath + 46 Suppleness) as the main exercise of a session. Many of them only appear at **one relaxation level** (Newb, Normal or Pro) and in **one position** (Floor or Standing). |
| **Master of wisdom** (25,000 Zen) | Simple check: lifetime Zen plus this session's Zen ≥ 25,000. The only real obstacle is the save hang, which throws away the session's Zen. |
| **Adept of Relaxation** (20 h) | A counter of **72,000 seconds**. It only advances during the Relaxation part of a session, and only while an exercise is actually in progress. That's why it takes far longer than 20 hours of play. Hung saves also throw away time. |

---

## The save hang

1. `BCProfile::SaveGame` (`0x821e8dd0`) saves a **3,599,548-byte** block (profile+`0x408`…`0x36f0c4`). It does this by queuing a job and storing a handle at `global+0x7c`. Until the handle clears, the game shows "Saving…".
2. Jobs run on a **single worker thread** (`0x822977b0`). It takes one job, runs it to completion, then takes the next. **Achievement unlocks use the same queue** and call `XUserWriteAchievements` synchronously (`0x822aa4d8`). A slow or blocked job delays everything behind it.
3. The save job (`0x822a8c58`) first validates the storage device (`0x822a8988`). If no valid device is recorded for the player, it:
   - **waits while the system-UI flag is set** (`while (flag) Sleep(0);` at `0x822a8a54`). That flag (`0x82e2e394`) is set and cleared only by the `XN_SYS_UI` notification (`0x822a9b4c` / `0x822a9b6c`), i.e. when the Xbox Guide or another system dialog opens or closes.
   - **opens the storage-device selector and spins until it reports a result** (`0x822a8a9c`), with no timeout.
4. The main loop (`0x8224d860`) only completes the save once the job is marked done. There's **no timeout or error path** for a job that never finishes.

The code doesn't show why digital copies would be affected more than discs. It does show that any storage-device check that never resolves leaves you on "Saving…" forever.

**Ways to reduce the risk (untested suggestions based on the code):**
- Set a storage device explicitly before playing. There's an in-game **Options → Storage** entry (`GUI_PROFILEMENU_OPTIONS_STORAGE` / `ChangeStorage`). Make sure it has a few MB free; each save is about 3.5 MB.
- **Don't open the Xbox Guide** near the end of a session or while it's saving. Don't remove USB storage while playing.
- If it hangs, that session's progress is gone. Keep sessions shorter while grinding, so a hang costs less.

## Achievement-by-achievement

| ID | Achievement | Exact condition | Where |
|---|---|---|---|
| 1 | Assessment completed | profile created | `0x821eb5dc` |
| 2 | Good start! | first session in the program | `0x821eb31c` |
| 6 / 7 / 8 | Zenitude / Towards inner peace / Master of wisdom | (lifetime Zen + this session's Zen) ≥ 2,000 / 5,000 / 25,000. Checked live during sessions and at the end. **Only the highest bracket reached is checked**, so jumping past 2,000 straight to 5,000 in one go would skip Zenitude. | `0x821ed0c8` |
| 14 | Master of Breathing | every **Breath**-type exercise (22) completed at least once. The 2 "no-movement" breathing exercises are the breathing **intro** at the start of relaxation; the code counts intro exercises as Breath. | `0x821ed1a8` |
| 17 | Master of Relaxation | every **Pilates** (61), **Breath** (22) and **Suppleness** (46) exercise completed at least once | `0x821ed1a8` |
| 19 / 20 | Okay, we're done here / Perfect synchronization | profile updates | `0x821ec048` |
| 25 | Relaxation Mission accomplished! | during the Relaxation part, this session's Zen ≥ the day's Zen goal | `0x8221a808` |
| 28 / 29 | A quick Zen warm-up / Adept of Relaxation | relaxation-time counter ≥ 3,600 s / 72,000 s | `0x8221b088` |
| 30 | Your efforts will pay off | set when the program's calendar logic marks the program as ended | `0x821eaa48` |

### How exercise completion is tracked (Breathing and Relaxation)
- When an exercise finishes, `0x821eb0b8` calls `MarkDone(name, type)` (`0x821f4d10`). Each type keeps a list of up to 100 exercise names, and its counter `done[type]` only goes up for a **new** name. Repeats don't count twice.
- `total[type]` is rebuilt at every boot by counting entries of that `Type` in `Exercises.lua` (`0x821e0488`).
- The check is `done == total` for Breath (Master of Breathing), and for Pilates, Breath and Suppleness together (Master of Relaxation).
- Only exercises played as **main session exercises** count under their own type. Warm-up and loosening exercises are relabelled (types 7 and 9) and ignored. Stretch-end exercises are relabelled (type 8) on one of the two code paths that build them.

### Why Master of Relaxation is so hard
Main relaxation exercises come from `ListCombination.cfg`, keyed by **muscle group × position × relaxation level**. The picker (`0x821e6270`) draws one 4-exercise combination at a time and prefers ones you haven't had yet. [`evidence/relaxation_exercises.csv`](evidence/relaxation_exercises.csv) lists every one of the 129 exercises with the levels and positions where it can appear:

| Type | Total | Only at Newb | Only at Normal | Only at Pro | Floor only | Standing only |
|---|---|---|---|---|---|---|
| Pilates | 61 | 8 | 5 | 9 | 40 | 18 |
| Suppleness | 46 | 4 | 7 | 5 | 19 | 27 |
| Breath | 22 | 3 | 1 | 2 | – | 20 (+2 intro) |

So to finish the set you have to do relaxation at **all three relaxation levels** and get **both floor and standing** blocks, many times over. The game picks the position itself; there's no "standing only" option for relaxation. (`IsStandInProgram` refers to a *stand-in*, i.e. substitute, program.)

**Practical approach (suggested from the code, not tested):**
- The relaxation level is the **Relaxation slider** in the profile level settings (`UpdateLevels.lua`). It stores 0, 5, 10, 15 or 20, and the exercise lists only exist for **0 (Newb), 10 (Normal) and 20 (Pro)**. A setting with no list of its own (5 or 15) falls back to Pro. So use the lowest, middle and highest positions.
- Grind relaxation at one level until no new exercises are appearing, then switch level, and repeat.
- Make sure saves complete (see above). A hung save wipes the session's newly completed exercises.

Caveat: Breathing also has level-exclusive exercises, yet players report getting Master of Breathing in one long free session. So the game evidently mixes levels in some situations (possibly the assessment or free-program sessions). That path wasn't fully traced, so treat the level advice as a strong suggestion rather than a proven requirement.

### Relaxation time (Adept of Relaxation / A quick Zen warm-up)
`0x8221b088` adds frame time to the counter at profile+`0x36a5b0` only while the session phase is **Relaxation** or **Overtime Relaxation**, and only in a specific per-exercise state. Fitness and the assessment don't count, and probably neither do intros, transitions and rests. Thresholds are 3,600 s and 72,000 s. A player reporting about 67 hours of play before it unlocked fits this.

## Reproducing

Requirements: Python 3 with `cryptography` and `capstone`.

```sh
python3 tools/xexdec_basic.py <game>/default.xex default.pe            # AES retail key + "basic" compression
MBC3_PE=default.pe python3 -c "import sys; sys.path.insert(0,'tools'); import disasm_helpers as C; C.prf(0x821ed1a8)"
python3 scripts/relaxation_coverage.py <game>/Common/Scripts > relaxation_exercises.csv
```

No game files are included in this repo.

## Caveats
- Static analysis only, with no testing on hardware or an emulator. Title updates weren't examined.
- The digital-vs-disc difference in the save hang isn't explained by anything found here.
- How the game picks level and position for each relaxation block was only partly traced (see the Breathing caveat).
