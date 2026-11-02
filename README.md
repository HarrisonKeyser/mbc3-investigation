# My Body Coach 3 (Xbox 360): achievements and the "endless saving" bug

Static analysis of the EUR build (`default.xex` plus its Lua scripts). It covers how every achievement is actually unlocked, why some look broken, and what can make the end-of-session save hang forever.

All addresses are virtual addresses in the decrypted `default.xex` (base `0x82000000`). Annotated listings are in [`evidence/disassembly.txt`](evidence/disassembly.txt).

## Track your Master of Relaxation progress

**[Open the progress tracker](https://harrisonkeyser.github.io/mbc3-investigation/)**: a checklist of all 129 relaxation exercises. It's grouped by the session type and position that can give you each one, with the levels it appears at, its pose and the coach's instructions, plus progress bars for Master of Breathing and Master of Relaxation.

- Nothing to install or sign up for. Your ticks are saved in your own browser and nobody else sees them.
- Use **Copy progress code** to back up your ticks or move them to another device or browser, and **Paste a code** to load them.
- No internet? Download [`docs/index.html`](docs/index.html) (*Download raw file*) and open it in any browser; it works offline.
- Prefer a spreadsheet? [`docs/relaxation_tracker.csv`](docs/relaxation_tracker.csv) has the same list with a *Done* column. Open it in Excel, or in Google Sheets with *File → Import*.

## TL;DR

| Problem | What the code shows |
|---|---|
| **"Saving…" never finishes** | Saves and achievement unlocks share **one background thread** that runs jobs one at a time. Before writing, the save checks the storage device. That check contains **two waits with no timeout**, one for the Xbox Guide/system UI to close and one for the storage-device selector to return. If either never resolves, the job never finishes, and the game shows "Saving…" forever. **Everything from that session is lost**, including Zen, relaxation time and exercises completed. |
| **Master of Relaxation** (no known legit unlock) | It isn't impossible in code, but it's extremely demanding. You must complete **every one of 129 relaxation exercises** (61 Pilates + 22 Breath + 46 Suppleness) as the main exercise of a session. What a session contains isn't random: **your goal decides the exercise type and position**, and **no single goal has all three types**. Suppleness only comes up under *Lose weight*, and Breath only under *Peace and calm* or *An active and balanced life*, so you have to **change goal at least once**. Many exercises also only appear at **one relaxation level**, so you need sessions at all three. |
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
| 14 | Master of Breathing | every **Breath**-type exercise (22) completed at least once. The 2 "no-movement" breathing exercises are the breathing **intro** at the start of relaxation; the code counts intro exercises as Breath. The other 20 only come up in Breath sessions, which only the *Peace and calm* and *An active and balanced life* goals schedule. Newb, Normal and Pro each have Breath exercises found nowhere else, so you need Breath sessions at all three levels. | `0x821ed1a8` |
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

### What decides which relaxation exercises you get
Three things decide it. The first two aren't random at all.

**1. Your goal and how far into the program you are decide the exercise type and the position.** When you start a program, the game plans every session in advance (`0x821e98f0`). The relaxation part of each session gets **one exercise type and one position** from a fixed 4-session cycle. The cycle depends only on the goal:

| Goal | 1st session | 2nd | 3rd | 4th (then it repeats) |
|---|---|---|---|---|
| Lose weight | Pilates, standing | **Suppleness**, standing | Pilates, floor | **Suppleness**, floor |
| Peace and calm | **Breath**, standing | Pilates, standing | **Breath**, standing | Pilates, floor |
| An active and balanced life | Pilates, standing | **Breath**, standing | Pilates, floor | **Breath**, standing |
| Tone your look | Pilates, standing | Pilates, floor | Pilates, standing | Pilates, floor |

- The whole relaxation part of the session uses that one type and position. That includes the extra session the coach offers when you miss your Zen goal (`StartAdjustmentSession` → `0x821eceb0`).
- **No goal schedules all three types.** Suppleness only appears under *Lose weight*. Breath only appears under *Peace and calm* and *An active and balanced life*.
- When no session is planned for the day, the game uses the next planned one (`0x821e7060`), so the cycle carries on.
- If a day has no planned type or position (for example after a program has ended), it falls back to **Pilates, standing**.
- The game doesn't let you choose the position yourself. (`IsStandInProgram` is about a *stand-in*, i.e. substitute, program, not about standing.)

**2. The Relaxation level slider decides the difficulty, and the in-between settings mix two levels.** The slider (`UpdateLevels.lua`, labelled from *Anguished* to *Serene* when you create a profile) stores 0, 5, 10, 15 or 20 (`0x821ec648`). Exercise lists only exist for Newb (0), Normal (10) and Pro (20). For an in-between setting, the session builder (`0x821e5260`) uses the next level up for the first half of the relaxation time and the lower level for the rest:

| Slider position | Exercises drawn from |
|---|---|
| 1 (lowest, *Anguished*) | Newb |
| 2 (*Agitated*) | Normal for the first half, then Newb |
| 3 (*Worried*) | Normal |
| 4 (*Fairly calm*) | Pro for the first half, then Normal |
| 5 (highest, *Serene*) | Pro |

*(An earlier version of this README said positions 2 and 4 fall back to Pro. That was wrong.)*

**3. Within those, the game works through sets you haven't had yet.** Each block is one set of 4 exercises from `ListCombination.cfg` for the session's muscle group, position and level. Pilates sessions alternate between the Postural and Support lists. The picker (`0x821e6270`) skips sets already used this session and sets already used in earlier programmed sessions (remembered in the save, `0x821e9168`). It only starts repeating once a whole list has been used.

### Where each exercise can come from
[`evidence/relaxation_exercises.csv`](evidence/relaxation_exercises.csv) lists all 129 exercises. For each one it gives the levels and positions where it appears, the session type that contains it, the goals that schedule that session, and the slider settings that reach it. Summary:

| Exercises | Only in… | Goals that give you that session |
|---|---|---|
| 61 Pilates, plus 1 Suppleness exercise (`PIL_KNEE_EXE_MED_4`, which is only in a Pilates list: floor, Pro) | Pilates sessions | any goal |
| the other 45 Suppleness | Suppleness sessions | **Lose weight** only |
| 20 Breath | Breath sessions (always standing) | **Peace and calm** or **An active and balanced life** |
| 2 Breath (the breathing intros) | the intro at the start of every relaxation part, picked at random | any goal |

Level and position restrictions on top of that:

| Type | Total | Only at Newb | Only at Normal | Only at Pro | Floor only | Standing only |
|---|---|---|---|---|---|---|
| Pilates | 61 | 8 | 5 | 9 | 40 | 18 |
| Suppleness | 46 | 4 | 7 | 5 | 19 | 27 |
| Breath | 22 | 3 | 1 | 2 | – | 20 (+2 intro) |

So you need Pilates standing and floor, Suppleness standing and floor, and Breath standing, **each at all three levels**. Going through every list once is 141 sets of four (24 Breath, 70 Pilates, 47 Suppleness), spread over many sessions.

**Practical route (worked out from the code, not tested):**
1. **Start with *Peace and calm* or *An active and balanced life*.** That gives you Breath sessions plus Pilates standing and floor. Play sessions at each slider level: lowest, middle and highest. Positions 2 and 4 cover two levels in one session, but only half the time each. Breath needs all three levels too: for example, Breath sessions at position 2 (Normal, then Newb) and at position 4 or 5 (Pro), repeated until nothing new turns up. That also gets you **Master of Breathing**.
2. **Then switch the goal to *Lose weight*** (Profile menu → *Modify the goal*). That's the only goal with Suppleness sessions. It alternates Pilates and Suppleness, standing for two sessions and then floor for two. Again, cover all three levels. Changing the goal stops the current program, but it doesn't touch the completed-exercise list. That list is kept separately, and only starting a brand-new profile clears it (`0x821f4740`).
3. Don't forget `PIL_KNEE_EXE_MED_4`. Despite being a Suppleness exercise, it only shows up in **Pilates sessions on the floor at Pro** (slider position 4 or 5).
4. If you miss the Zen goal, **accept the coach's offer of another session**. It adds more blocks of the same type and position, so it's an easy way to see extra exercises.
5. Make sure saves complete (see above). A hung save wipes that session's newly completed exercises, and the "already used" set memory too.

Players have reported getting Master of Breathing in one long session. That fits if the last missing Breath exercises came in that session. A single session can cover at most two of the three levels (slider position 2 or 4), and all three levels have Breath exercises of their own.

### Relaxation time (Adept of Relaxation / A quick Zen warm-up)
`0x8221b088` adds frame time to the counter at profile+`0x36a5b0` only while the session phase is **Relaxation** or **Overtime Relaxation**, and only in a specific per-exercise state. Fitness and the assessment don't count, and probably neither do intros, transitions and rests. Thresholds are 3,600 s and 72,000 s. A player reporting about 67 hours of play before it unlocked fits this.

## Reproducing

Requirements: Python 3 with `cryptography` and `capstone`.

```sh
python3 tools/xexdec_basic.py <game>/default.xex default.pe            # AES retail key + "basic" compression
MBC3_PE=default.pe python3 -c "import sys; sys.path.insert(0,'tools'); import disasm_helpers as C; C.prf(0x821ed1a8)"
python3 scripts/relaxation_coverage.py <game>/Common/Scripts > relaxation_exercises.csv
python3 scripts/session_plan.py                                        # goal -> session cycle, slider -> levels
python3 scripts/build_tracker_data.py <game>/Common evidence/relaxation_exercises.csv docs/   # tracker data + CSV
```

The tracker (`docs/index.html`) is one self-contained page with the output of `build_tracker_data.py` pasted in as `const DATA = ...`. It's served by GitHub Pages from the `docs/` folder.

No game files are included in this repo.

## Caveats
- Static analysis only, with no testing on hardware or an emulator. Title updates weren't examined.
- The digital-vs-disc difference in the save hang isn't explained by anything found here.
- The goal → session-type cycle assumes sessions are played in calendar order. How missed or rescheduled sessions (`0x821eaa48`) shift the cycle wasn't traced in detail.
