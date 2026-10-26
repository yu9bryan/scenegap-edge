# SceneGap Edge UI — design notes

Short research pass (layout patterns only; no assets, logos or trademarks copied) over public material about
Frame.io review panels, Premiere Pro Media Intelligence / Search panel, DaVinci Resolve 21 IntelliSearch,
Linear's 2024 UI refresh, Vercel's 2026 sidebar navigation and Final Cut Pro's browser/viewer/inspector split.

## Takeaways we adopt

1. **Viewer in the middle, context left, inspector right** (Final Cut browser/viewer/inspector, Resolve pages).
   The evidence viewer uses the same three columns: requirement + hard conditions on the left, the player in
   the centre, condition verdicts and decision actions on the right. Editors already read a screen this way.
2. **A result opens as a marked range, not a whole clip** (Premiere's Search panel loads a visual hit into the
   Source Monitor with In/Out points set). The viewer seeks to `start_ms`, loops `[start, end)`, and draws the
   range on a timeline strip under the video, so the reviewer checks exactly the evidence the model used.
3. **Comments/decisions live under the play bar and jump the playhead** (Frame.io panel). Every candidate on the
   timeline strip and in the candidate list is a button that moves the playhead to that range.
4. **Search scope is explicit** (IntelliSearch only knows imported media; Premiere waits for analysis before
   search). Every coverage number says what it covers: "已分析範圍", analysis progress, failed-file banner.
   "Not found" is always worded as "在已分析範圍未找到", never as "missing".
5. **Local-first is a feature to state, not hide** (both Adobe and Blackmagic stress on-device analysis). The
   top bar always shows the real active backend (`cpu-reference`, `cuda-reference`, `not loaded`) and the
   UGen300 connection state, so nobody mistakes a CPU run for an NPU run.
6. **Near-black canvas, hierarchy from lightness steps, not many hues** (Linear's refresh: fewer theme
   variables, more contrast, less visual noise). Background `#0E0E14`, panels `#15151F`, raised `#1C1C29`,
   hairline borders; colour is reserved for accent (violet) and status.
7. **One accent for action, one for information.** Violet `#6C4CF5` / `#8B72FF` marks primary actions and the
   current selection; cyan `#22D3EE` marks "live"/running things (job progress, playhead, focus ring).
8. **Status = icon + text + colour, always** (PRD FR-UI-04; also Linear's issue-status icons have distinct
   shapes). Each automatic status has its own glyph (dashed circle, spinner, target, half circle, search-x,
   question, warning, pencil) so it still reads in greyscale or for colour-blind users.
9. **Automatic and human state are two separate chips in two columns.** AI chips are tinted/filled and prefixed
   "AI"; human chips are outlined and prefixed "人工". There is no combined green light, mirroring review tools
   where an "approved" mark is something a person sets, not the software.
10. **Collapsible left sidebar with stable order** (Vercel's 2026 navigation moved to a resizable/hideable
    sidebar ordered by workflow). Our nav follows the actual workflow order: 專案 → 需求 → 素材 → 覆蓋矩陣 →
    證據 → 複核／補拍 → 裝置; below 1280 px it collapses to an icon rail with tooltips and aria-labels.
11. **Dense tables with tabular numerals** (Resolve media pool list view, Linear lists). Asset and coverage
    tables use `font-variant-numeric: tabular-nums`, monospace time codes `mm:ss.mmm`, sticky headers, and
    failure rows are styled, not filtered away.
12. **KPI cards that refuse to lie** (dashboard pattern from Vercel usage cards): a null metric prints "N/A"
    with a one-line reason, never 0 % or 100 %, and the bar is drawn hatched instead of empty.
13. **Never a fake progress bar.** Job progress is determinate only when `total > 0`; otherwise an
    indeterminate stripe plus the stage text. Cancel is always next to the bar.
14. **Board columns for follow-up work** (Frame.io/Linear boards). 先複核 and 建議補拍（待確認） are two columns
    of cards; a card's status is a segmented control a person changes, never auto-advanced.
15. **Keyboard first, visible focus** (Linear/Final Cut shortcut culture). Every control is a native button,
    input or link; focus ring is a 2 px cyan outline with offset; in the viewer Space = play/pause, `J`/`L`
    jump to range start/end, `[`/`]` previous/next candidate.

## Sources read

- Adobe Help / Community: Premiere Pro Search panel and Media Intelligence (visual search, In/Out on result).
- Frame.io support and Adobe Help: Frame.io panel in Premiere / After Effects (comments under the play bar,
  comments tied to markers).
- Larry Jordan / CineD / Newsshooter coverage of DaVinci Resolve 21 IntelliSearch (local analysis, smart bins,
  only searches imported media).
- Linear blog: "How we redesigned the Linear UI" and the 2024-03-20 changelog (LCH themes, contrast, less noise).
- Vercel changelog: dashboard navigation redesign rollout (sidebar, workflow ordering).
