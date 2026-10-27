# SceneGap Edge: Stage I demo video script (English)

- Length: 3:00 maximum. As built (v8): 2:58, narration 360 words (`docs/video/narration.json` is the final text).
- The shot table below is the plan; times and wording in the final cut follow `narration.json` and `make_video.py`.
- Everything on screen is real: Wikimedia Commons footage (CC0 / CC BY / CC BY-SA, credited at the end), live
  screen recordings of the SceneGap app running on a desktop, and figures from the repository. No actors.
- Narration: neural English voice (edge-tts, en-US). Burned-in English captions for every line.
- The demo project is created on camera in a fresh work folder, so the analysis, decisions and reshoot list are
  what the app actually produced during the recording.
- Numbers come from `eval/results/REPORT.md`. Device: desktop CPU/GPU today; UGen300 is the next step.

## Demo setup (recorded live)

| Item | Detail |
|---|---|
| Project | "Café promo · 60 s" in a fresh work folder |
| Shot list | the 11 café shots from `eval/requirements.json` (Chinese wording + English query) |
| First import | 8 clips: 001 Vichy terrace, 007 Café Lomi, 012 roaster, 016 Lions Almelo, 020 espresso, 026 latte art, 032 sugar into coffee, 041 Paris streets (019, a blender grinding beans, is left out so the grinder shot is genuinely missing) |
| "Reshoot" import | 022 *Der perfekte Espresso aus dem Siebträger* (shows grounds falling from a grinder), added after the reshoot list is made |

## Shot list, narration and captions

| # | Time | Picture | Narration | On-screen text |
|---|---|---|---|---|
| 1 | 0:00–0:11 | Real café footage: Café Lomi interior, a latte-art pour, a Paris terrace (Commons). Slow cross-fades. | A café promo. Eleven must-have shots. Two people, one afternoon on location. | "A café promo · 11 must-have shots" |
| 2 | 0:11–0:24 | Dark card: a timeline "17:40 wrap → 23:00 edit". The espresso stream clip plays small inside the card. | The crew packs up at five forty. At eleven that night, the editor finds the pour cuts away after two seconds, and nobody filmed a customer drinking. | "17:40 wrap · 23:00 edit: the 3-second pour is missing" |
| 3 | 0:24–0:36 | Card: three tool names (Premiere Pro, DaVinci Resolve, Final Cut Pro) with "searches footage ✓" and "checks the shot list ✗". | Editing tools can now search footage for a cup. None of them checks the shot list: how long, how many takes, what must be in the same frame. | "Footage search ≠ shot-list check" |
| 4 | 0:36–0:44 | Title card: SceneGap Edge logo text over a blurred café frame. | This is SceneGap Edge. It checks your shot list against your footage, on your own computer, before you leave. | "SceneGap Edge · local shot coverage" |
| 5 | 0:44–1:00 | Screen: Shot list screen. Scroll the 11 shots; open SH-05 "咖啡倒入杯中或拉花，連續 3 秒" with the English query and "minimum 3 s". | You write the shot list the way the crew talks. A person confirms the English query the model reads, and adds rules: minimum length, number of takes, what must appear together. | "Shot list: your words + the query the model reads" |
| 6 | 1:00–1:13 | Screen: Assets → authorise the card folder → import 8 clips → Start analysis; progress bar runs (sped up, labelled). | Point it at the card. It hashes every file, cuts the shots, samples one frame a second on the original timecode, and indexes everything with CLIP. | "Analysis on a desktop GPU · sped up ×N" |
| 7 | 1:13–1:22 | Screen: Coverage board fills in; pan down the rows with real thumbnails. | Every shot gets an answer from the AI, and a separate answer from you. Only yours counts. | "AI answer · your answer" |
| 8 | 1:22–1:46 | Screen: evidence view for SH-05. Candidate 1 plays: espresso stream, no cup → Reject with reason "no cup in frame". Candidate 2: latte-art pour → Accept. Human pill turns white. | Coffee poured into a cup, three seconds. The first candidate is an espresso stream with no cup in frame, so you reject it and say why. The next one is a latte-art pour. One click, accepted. | "Reject: no cup in frame" → "Accepted" |
| 9 | 1:46–2:02 | Screen: SH-04 grinder candidates are tamping, not grinding → "Add to reshoot" with reason; same for SH-07 drinking. Reshoot list shows the cards. | Nobody grinds coffee in these clips, and nobody drinks it. Those go on the reshoot list, with the reason and the minimum length, while the crew is still on location. | "Reshoot list: made before you leave" |
| 10 | 2:02–2:20 | Screen: import the reshoot clip (022) → re-analyse → SH-04 now shows grounds falling from the grinder → Accept; the card moves to done. | Here is the reshot clip. Only the new file is analysed. The grinder shot is now found. Accept it, and the gap closes. | "Only the new clip is analysed" |
| 11 | 2:20–2:38 | Results card (from REPORT.md): 44 Commons clips · two independent labellers (κ 0.91) · held-out test scored once: right clip in top 5 for 7 of 11 shots · 317 s to review instead of 839 s · missing-shot detection: Stage II. | We tested on forty-four openly licensed clips labelled by two AI annotators, scoring the held-out set once. The right clip was in the top five for seven of eleven shots; plain frame search got eight. Rule checks were right on ten of twelve controlled cases. On fresh photo clips, a preregistered second check caught two thirds of missing shots, with under four percent wrong reshoots. | "Top-5 hit 7/11 · review 317 s vs 839 s" |
| 12 | 2:38–2:52 | Architecture figure, push-in on the UGen300 box. | Next, the image encoder moves onto the ASUS UGen300, so the analysis leaves your editing machine free. Today it takes about two seconds per minute of video on a desktop GPU. | "Next: CLIP image encoder on UGen300" |
| 13 | 2:52–3:00 | End card: SceneGap Edge · team · repo · footage credits. | SceneGap Edge. Fewer surprises in the edit. | Credits list (author, licence) for every clip shown |

Planned narration was about 400 words; the final cut uses 359.

## Footage credits shown on the end card

Only clips that appear in the video, with author and licence from `datasets/manifests/commons_manifest.json`.

## Production notes

1. Record the UI with Playwright (1440×900, Edge, video on), driving the real app in a fresh work folder; a visible
   cursor overlay shows clicks.
2. Generate one narration file per scene; each scene's length = narration + about 0.6 s, picture trimmed or
   held to match.
3. Cards are rendered as 1920×1080 PNGs in the deck's look (Neo: violet/cyan on near-black).
4. Captions: white text on a dark band, bottom third.
5. Assemble with ffmpeg: per-scene MP4s → concat → narration mixed to −16 LUFS. No music bed (no licensed track available).

## As built (v2, 2026-10-26)

- Final length 2:39, 1920×1080, 30 fps, −16 LUFS. Narration: edge-tts `en-US-AndrewNeural` (`docs/video/narration.json`, `tts.py`).
- Live recordings made with `record_demo.py` against a fresh work folder; first analysis of the 8 clips took 25.2 s,
  the reshoot clip 2.5 s (desktop GPU). Sped-up parts are tagged on screen.
- Recording the demo found two UI bugs, both fixed before the final take: the analyse button stayed disabled after an
  import, and the job stage label reused the evidence `.stage` class (rendered as a large dark box).
- Assembled with `make_video.py` (Pillow cards and captions, ffmpeg).

## As built (v4, 2026-10-26)

- 2:57, 1920×1080, 30 fps, −16 LUFS. Built after a four-way review (judge, numbers, copy, video).
- UI re-recorded with `record_demo.py` after the wording changes; the recorder now writes `marks.json` (time and box of
  every click). `make_video.py` places each narration sentence on the click it describes, so voice and picture match.
- Screen recordings sit above a caption band (captions no longer cover the buttons); punch-in zooms on reject,
  add-to-reshoot and accept; every piece carries its real speed ("Live app · ×2", "real time · zoom").
- Narration changes: AI annotators named as AI; plain frame search scored one more top-5 hit than SceneGap, said
  plainly; the reshoot clip is labelled as a stand-in (another Commons clip); no claim about freeing the editing
  machine.
- End card: full attribution for every clip shown, voice and GPU named, and the licence: the video adapts CC BY-SA
  footage, so it is released under CC BY-SA 4.0.

## v5 (2026-10-26, after an external review)

- Positioning: "helps you check" the shot list; SceneGap is a review assistant, missing-shot detection is next.
- SH-05 is said as written in the shot list: coffee or latte art poured into a cup.
- Tools card: shot-list rules are "not in their docs" rather than "no"; Premiere finds the moment in a clip.
- Results: plain frame search 8 vs SceneGap 7; 10 of 12 controlled rule cases right (`eval/rule_check.py`).
- `make_video.py` retries ffmpeg when this Windows build crashes with 0xC000008F (the same command then succeeds).

## v6 (2026-10-27)

- Scene 11 ends on the new result: "A second check now catches a third of the missing shots on new footage" (test-2, eval/results/test2_metrics.json).
