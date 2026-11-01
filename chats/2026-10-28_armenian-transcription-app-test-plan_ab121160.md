# Conversation: Armenian transcription app test plan

**UUID:** ab121160-95a3-43a7-b03d-8b9ceecfd341
**Created At:** 2026-10-28T12:26:19.336891Z
**Updated At:** 2026-10-29T06:39:32.381679Z

## Messages

---
**Sender:** Assistant
**Timestamp:** 2026-10-28T12:26:19.828163Z

**Tool: prepare_session**

---
**Sender:** Human
**Timestamp:** 2026-10-28T12:26:19.882726Z

**Tool Error: **

```
[{'type': 'text', 'text': "This setup step was accepted and completes on its own, outside the conversation — nothing failed; this result is marked as an error only to close the step. Do not retry this call or mention it, and add no further text: the conversation continues with the user's messages as usual."}]
```

---
**Sender:** Human
**Timestamp:** 2026-10-28T12:26:22.176146Z

Hello. We are continuing the development of the live Armenian → English transcription app. I am the architect and you are my team.
Please read these two files from project folder: 

* DECISIONS.md
* handovers/001-planning-done.md

Read and understand those files.Then proceed with the proposing the next step: propose the structure and initial entries for TEST.md.Do not write the file yet;just propose it for my approval

---
**Sender:** Assistant
**Timestamp:** 2026-10-28T12:27:32.754336Z

I'll read both files from your project folder, then propose a TEST.md structure.

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/DECISIONS.md', '/...

**Tool Error: **

```
[{'type': 'text', 'text': '/home/zaven/Desktop/arm_en_asr/handovers/001-planning-done.md does not exist.'}]
```

**Tool: mcp__remote-devices__device_list_dir**
- path: /home/zaven/Desktop/arm_en_asr
- recursive: True

**Tool Result: **

The handover is named `001-planning-to-testmd.md`, not `001-planning-done.md` — I'll read that one (plus PLAN.md and the laptop specs, since the test plan likely depends on them).

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/DECISIONS.md', '/...

**Tool Result: **

**Tool: Read**
- file_path: /mnt/user-data/uploads/arm_en_asr/DECISIONS.md

**Tool Result: **

**Tool: Read**
- file_path: /mnt/user-data/uploads/arm_en_asr/handovers/001-pl...

**Tool Result: **

**Tool: Read**
- file_path: /mnt/user-data/uploads/arm_en_asr/PLAN.md

**Tool Result: **

**Tool: Read**
- file_path: /mnt/user-data/uploads/arm_en_asr/command_outputs/...

**Tool Result: **

I've read DECISIONS.md, the handover, PLAN.md and the laptop specs. There's no `handovers/001-planning-done.md`; the file in the folder is `handovers/001-planning-to-testmd.md`, so I used that one.

Below is my TEST.md proposal. Nothing has been written yet.

---

## Proposed structure of TEST.md

1. **How to use this file.** Every entry and every status change is agreed with Zaven before it is written (rule 10). Zaven runs all tests and sends back the output via `command_outputs/` (rules 8–9).
2. **Conventions**
   - **IDs:** `T<group>.<n>`, never reused.
   - **Status values:** `not run` · `passed` · `not passed`.
   - **How to run:** pytest from the activated `.venv`, e.g. `python -m pytest tests/test_asr.py -v`.
   - **Markers:** `hardware` for tests that need real PulseAudio devices and a person present, and `slow` for the load test. A plain `pytest` run excludes both.
   - **Fail loudly in tests too:** a missing model or fixture makes the test fail with a clear error. Tests are never silently skipped.
3. **Test catalogue.** A one-row-per-test summary table with ID, name, milestone and status.
4. **Test entries.** Each entry has: ID, purpose, milestone, linked decisions/risks, input data, how to run, pass criterion and status.
5. **Results log.** A table that only gets new rows appended: Date | Test ID | Commit | Conditions (Meet tab open? plugged in?) | Key numbers | Status | Notes.

## Initial entries (all with status `not run`)

**T1: Unit tests, one module at a time on fixture audio (M3, extended in M6)**

| ID | Purpose | Pass criterion |
|---|---|---|
| T1.1 | `audio_capture` + VAD (file input) | Speech fixture → at least 1 segment, each 0.3–12 s long, 16 kHz mono. Silence fixture → 0 segments (R7). Fixture with more than 12 s of continuous speech → cut at 12 s (D8). |
| T1.2 | `asr` | Speech fixture → non-empty text, and at least 50 % of its letters are Armenian script. This only checks that ASR runs; it is not a quality bar. |
| T1.3 | `translate` | 3 FLEURS Armenian sentences → non-empty English with no Armenian characters. |
| T1.4 | `output` | A fixed record gives exactly the line format in section 8. 83 s → `[00:01:23]`. Latency 5.1 s → warning shown; 4.9 s → no warning (D12). |
| T1.5 | `pipeline` | With stub ASR/MT/diarizer returning results out of order: each line joins the right segment id, lines print in order of speech end (D13), and mic segments are always "Me". |
| T1.6 | `diarizer` (M6) | A solo mic clip keeps the same speaker number on all segments (D17). On a 2-speaker system clip the % correct is reported, with no threshold. |

**T2: End-to-end latency in file mode (M4; re-run in M5 with `--system-wav`)**
- Command: `python app.py --mic-wav <eval clip>`, with the file fed in at real-time speed.
- Conditions: the demo worst case (browser Meet/Zoom tab open, laptop plugged in).
- Pass: every printed line has latency ≤ 5 s. Median, p95 and max are recorded.

**T3: Capture smoke test, `hardware` (M4 mic only; M5 both devices)**
- Setup: Zaven speaks into the mic and plays a video for the monitor source. Each device is opened with `parec` for 3 s.
- Pass: at least 2.5 s of samples received per device, and RMS above −50 dBFS (not silent).

**T4: Load test (D2), `slow` (M4)**
- Grid: N = 1, 2, 3 ASR workers × K = 1, 2, 4, 6 segments submitted at once, from eval clips, with a Meet tab open.
- Recorded: peak RSS, swap use, median/p95/max latency, segments per minute.
- Pass: at least one (N, K) combination has max latency ≤ 5 s and swap use grows by no more than 100 MB during the run.
- That combination becomes a new D# in DECISIONS.md.

**T5: Virtual-sink capture test (M9, cut first if time runs short)**
- Purpose: play a clip into a null sink and capture its `.monitor` via `--system`.
- Placeholder only. The exact steps and pass criterion are agreed when we reach M9.

## Decisions I need from you

1. **Real-time pacing in file mode (T2).** I recommend feeding the WAV at real-time speed. Otherwise latency is measured against a clip that arrives instantly and the 5 s number means nothing.
2. **Fixture audio.** I recommend committing a few seconds of FLEURS audio (CC-BY 4.0) plus generated silence in `tests/fixtures/`. The alternative is keeping fixtures gitignored like `eval/clips/`, but then tests can't run from a fresh clone.
3. **Proposed numbers.** These are sanity limits, not quality thresholds, and are yours to accept or change:
   - ≥ 50 % Armenian script (T1.2)
   - −50 dBFS silence limit (T3)
   - ≤ 100 MB swap growth (T4)
   - 100 % same label on a solo clip (T1.6)
4. **An optional T6 for "fail loudly" CLI checks**, all already decided in D11/D15. It would test:
   - an unknown device name
   - a missing model
   - an unknown stdin command
   - `quit` giving a clean shutdown

   Should I add it, or leave it out?

Once you approve (with any edits), I'll write TEST.md and propose the commit.

---
**Sender:** Human
**Timestamp:** 2026-10-29T05:57:42.753702Z

I accept the tests,but for T4 test we need a rule for what happens if multiple combinations pass.For which we will use tie-breaker rule:Choose the passing combination based on this order:

1. Highest segments processed per minute
2. Highest N(workers number)
3. Lowest max latency


Decisions answers,that you need from me
D1. I aggree feed the WAV at real-time speed
D2. Your reccomendation is accepted
D3 accepted
D4 Yes we should add T6

---
**Sender:** Assistant
**Timestamp:** 2026-10-29T05:59:08.272354Z
**Attachments:** TEST.md, DECISIONS.md, DECISIONS.md, DECISIONS.md, DECISIONS.md, DECISIONS.md, DECISIONS.md

I'll write TEST.md with your answers and the T4 tie-breaker. I'll also record the new decisions in DECISIONS.md (rule 5), then propose the commit.

**Tool: Write**
- content: # TEST.md — Live Armenian → English transcription ...
- file_path: /mnt/user-data/outputs/TEST.md

**Tool Result: **

**Tool: Bash**
- command: cp /mnt/user-data/uploads/arm_en_asr/DECISIONS.md ...
- description: Copy DECISIONS.md to outputs for editing

**Tool Result: **

Now the DECISIONS.md updates: the status section, a D2 tie-breaker line, the new decisions D21–D22, and the T6 line in D20.

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: - Created: 2026-10-26 · Last updated: 2026-10-29
- old_string: - Created: 2026-10-26 · Last updated: 2026-10-28

**Tool Error: **

```
[{'type': 'text', 'text': '<tool_use_error>File has not been read yet. Read it first before writing to it.</tool_use_error>'}]
```

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: - **Current milestone:** M0 — Planning (done once ...
- old_string: - **Current milestone:** M0 — Planning (in progres...

**Tool Error: **

```
[{'type': 'text', 'text': '<tool_use_error>File has not been read yet. Read it first before writing to it.</tool_use_error>'}]
```

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: - Result: the largest N and K that keep RAM within...
- old_string: - Result: the largest N and K that keep RAM within...

**Tool Error: **

```
[{'type': 'text', 'text': '<tool_use_error>File has not been read yet. Read it first before writing to it.</tool_use_error>'}]
```

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: - Tests: pytest. Initial tests: (1) each module al...
- old_string: - Tests: pytest. Initial tests: (1) each module al...

**Tool Error: **

```
[{'type': 'text', 'text': '<tool_use_error>File has not been read yet. Read it first before writing to it.</tool_use_error>'}]
```

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: | M0 | Planning: questions, DECISIONS.md, TEST.md ...
- old_string: | M0 | Planning: questions, DECISIONS.md, TEST.md ...

**Tool Error: **

```
[{'type': 'text', 'text': '<tool_use_error>File has not been read yet. Read it first before writing to it.</tool_use_error>'}]
```

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: tests/
tests/fixtures/           # small committed...
- old_string: tests/
eval/meta/*.csv           # committed

**Tool Error: **

```
[{'type': 'text', 'text': '<tool_use_error>File has not been read yet. Read it first before writing to it.</tool_use_error>'}]
```

**Tool: Read**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- limit: 5

**Tool Result: **

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: - Created: 2026-10-26 · Last updated: 2026-10-29
- old_string: - Created: 2026-10-26 · Last updated: 2026-10-28

**Tool Result: **

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: - **Current milestone:** M0 — Planning (done once ...
- old_string: - **Current milestone:** M0 — Planning (in progres...

**Tool Result: **

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: - Result: the largest N and K that keep RAM within...
- old_string: - Result: the largest N and K that keep RAM within...

**Tool Result: **

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: - Tests: pytest. Initial tests: (1) each module al...
- old_string: - Tests: pytest. Initial tests: (1) each module al...

**Tool Result: **

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: | M0 | Planning: questions, DECISIONS.md, TEST.md ...
- old_string: | M0 | Planning: questions, DECISIONS.md, TEST.md ...

**Tool Result: **

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: tests/
tests/fixtures/           # small committed...
- old_string: tests/
eval/meta/*.csv           # committed

**Tool Result: **

**Tool: mcp__remote-devices__device_commit_files**
- files: [{'devicePath': '/home/zaven/Desktop/arm_en_asr/TE...

**Tool Result: **

I wrote `TEST.md` into your project folder and updated `DECISIONS.md` there with what you just agreed.

**TEST.md** has the conventions, a catalogue of tests T1.1–T1.6 and T2–T6 (all "not run"), the full entries and an empty results log. The tie-breaker is written into T4 in your order: highest segments per minute, then highest N, then lowest max latency.

**DECISIONS.md changes:**
- **Current status:** TEST.md written; M0 counts as done once you commit; next step is M1.
- **D2:** the load-test pass rule and the tie-breaker.
- **D20:** added T6 and the four sanity limits you accepted (≥ 50 % Armenian script, −50 dBFS, ≤ 100 MB swap growth, 100 % same label on a solo clip).
- **New D21:** file mode feeds the WAV at real-time speed (your answer 1).
- **New D22:** fixtures are committed in `tests/fixtures/`, and a missing model or fixture makes a test fail rather than skip (your answer 2).
- **D16 repo layout:** added `tests/fixtures/`.

You only accepted these points in this chat, so please check the D21/D22 wording before committing. If anything is off, I'll change it.

**Proposed commit** (for you to run):
```
git add TEST.md DECISIONS.md
git commit -m "M0: add TEST.md (T1–T6); record D21–D22, T4 tie-breaker"
```

After the commit, the next step is M1: setting up the environment with uv and writing `download_models.py`. I'll start by proposing the pinned `requirements.txt` for your approval.

---
**Sender:** Human
**Timestamp:** 2026-10-29T06:30:19.986473Z

I accept those new decisisons.Also I did the new commit you propose.

We will move to fresh chat for the next step,please write write handover for the next chat and give me the path to handover.

---
**Sender:** Assistant
**Timestamp:** 2026-10-29T06:31:27.176930Z
**Attachments:** DECISIONS.md, DECISIONS.md, 002-testmd-to-m1.md

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/DECISIONS.md']

**Tool Result: **

**Tool: Bash**
- command: diff /mnt/user-data/outputs/DECISIONS.md /mnt/user...
- description: Compare my copy with the current DECISIONS.md

**Tool Result: **

**Tool: mcp__remote-devices__device_list_dir**
- path: /home/zaven/Desktop/arm_en_asr/.git
- recursive: True

**Tool Result: **

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/.git/objects/1a/7...

**Tool Result: **

**Tool: Bash**
- command: cd /mnt/user-data/uploads/arm_en_asr; tail -1 .git...
- description: Decode committed blobs and compare with disk files

**Tool Result: **

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: - **Current milestone:** M1 — Environment (not sta...
- old_string: - **Current milestone:** M0 — Planning (done once ...

**Tool Result: **

**Tool: Edit**
- file_path: /mnt/user-data/outputs/DECISIONS.md
- new_string: | 1.5 | ☑ done (2026-10-29) |
- old_string: | 1.5 | ☐ not done (TEST.md written; done after Za...

**Tool Result: **

**Tool: Write**
- content: # Handover 002 — TEST.md → M1 (environment) — 2026...
- file_path: /mnt/user-data/outputs/002-testmd-to-m1.md

**Tool Result: **

**Tool: mcp__remote-devices__device_commit_files**
- files: [{'devicePath': '/home/zaven/Desktop/arm_en_asr/DE...

**Tool Result: **

Verifying the write landed completely this time:

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/DECISIONS.md']

**Tool Result: **

**Tool: Bash**
- command: cmp /mnt/user-data/outputs/DECISIONS.md /mnt/user-...
- description: Confirm disk DECISIONS.md matches the intended ver...

**Tool Result: **

I've written the handover. Its path is:

**`/home/zaven/Desktop/arm_en_asr/handovers/002-testmd-to-m1.md`**

Start the new chat with `DECISIONS.md`, `TEST.md` and this handover.

There was one problem. Your last commit has the full TEST.md, but the DECISIONS.md in it was missing D21, D22, the D20 additions (T6 and the sanity limits) and the `tests/fixtures/` line. I don't know why those changes didn't reach your file. I've now rewritten DECISIONS.md with the full agreed text and checked it against my copy; they match.

I also marked M0 as done and set the current milestone to M1 in the same file. Please look over the diff before committing.

**Proposed commit** (for you to run):
```
git diff DECISIONS.md
git add DECISIONS.md handovers/002-testmd-to-m1.md
git commit -m "M0 done: restore D21–D22 + D20 test additions; add handover 002"
```

---
**Sender:** Human
**Timestamp:** 2026-10-29T06:39:27.569694Z

Also write an initial chat text for me to write in fresh chat, for each new session,do not write in any files,just write it in this chat

---
**Sender:** Assistant
**Timestamp:** 2026-10-29T06:39:32.412687Z

Here's an opening message you can paste at the start of each new chat. Change only the handover filename each time.

```
Hello. We are continuing the development of the live Armenian → English transcription app. I am the architect (Zaven) and you are my team.

Project folder: /home/zaven/Desktop/arm_en_asr

Please read these files from the project folder first:
* DECISIONS.md (single source of truth: rules, decisions, status, milestones)
* TEST.md (agreed tests and their statuses)
* handovers/002-testmd-to-m1.md (latest handover)

Read and understand them, then do the "Exact next step" from the handover.

Reminders:
* Follow the working rules in DECISIONS.md section 1, especially: you only propose; I decide and run every command and every git command myself.
* Nothing goes into DECISIONS.md or TEST.md, and no new decision is built on, until I approve it.
* If a file I name doesn't exist or anything conflicts between files, tell me before continuing.
```

For this next session it's `handovers/002-testmd-to-m1.md`. Later sessions use whatever handover number is newest. If a session doesn't need TEST.md, you can drop that line.
