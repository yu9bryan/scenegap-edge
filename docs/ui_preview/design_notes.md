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

## ASUS design references (restyle, 2026-10-26)

The user asked for the feel of ASUS's own software. SceneGap Edge runs on the ASUS UGen300 and is an entry in
ASUS's UGen AI League, so the UI now borrows that hardware-utility feel. **We take the feel, not the brand:**
no ASUS / ProArt / ROG logos, wordmarks, icons or images are used; the app is still "SceneGap Edge", and only
the device screen names the hardware ("UGen300"). Our accents stay violet `#6C4CF5`/`#8B72FF` and cyan `#22D3EE`,
not ProArt's bronze or ROG red.

### What we looked at (described, not copied; screenshots kept outside the repo)
- **ProArt Creator Hub product page** — https://www.asus.com/uk/ProArt/ProArt-Creator-Hub/ (we looked at the
  hero section and the dashboard screenshots). The app is a near-black, neutral (not blue-tinted) charcoal
  window. A slim left rail has icon + label items and a filled active item. Device tabs run across the top
  (laptop, monitor). Square cards have a small title at top-left, a hairline under the header and a tiny
  action glyph at top-right. Big *light-weight* numerals ("7 %") sit next to a thin ring gauge. Key/value rows
  put the label left in grey and the value right in the accent colour. Thin progress lines everywhere.
- **ProArt Creator Hub FAQ** — https://www.asus.com/support/faq/1045995/ (structure: Dashboard with
  draggable info cards, operating-mode quick switches, a 2026 refresh that moves system info to the top-left).
- **Armoury Crate 6 article** — https://rog.asus.com/uk/articles/guides/armoury-crate-version-6-is-here-optimizing-your-gaming-pc-easier-than-ever/
  (dashboard and feature-library screenshots, plus the article page itself). It describes a "less visually busy"
  redesign. Panels have **chamfered (angled) corners**, condensed uppercase headings, a slash `/` before
  section titles, a `/////` hatch motif next to dates, and dense metric tables with right-aligned values and
  thin coloured lines. The left nav is split into small grey **group labels**.
- **MyASUS introduction / FAQ** — https://www.asus.com/us/support/faq/1050467/ (home page screenshot). A device
  hero shows the product name large, serial and quick links, with a **2×2 grid of status tiles**: each has a
  thin coloured top line, icon, label and a big number with a small unit (Battery 79 %, CPU load 6 % | 77 °C).
- ASUS ProArt home page — https://www.asus.com/proart/ (overall tone: black canvas, light display type,
  generous spacing, thin rules).

### What we adopted, and where
1. **Neutral charcoal surfaces** (`#0B0B0D` canvas, `#141417` panels, hairline `#2C2C33`), with no blue tint.
   Status colours are unchanged and still always paired with an icon and text.
2. **Chamfered top-right corner on every panel and card**, with a hairline drawn along the cut (`clip-path`
   plus a rotated 1.5 px line). Corners are square (2 px) elsewhere. Buttons and inputs are *not* clipped,
   so focus rings stay fully visible.
3. **Slash section markers** (`/ 條件檢查`) replace the panel-header icons; **condensed uppercase eyebrows** with
   a `////` hatch sit above every page title (`//// COVERAGE MATRIX`). Fonts: Barlow / Barlow Condensed for
   display numbers and eyebrows (Google Fonts); Inter + Noto Sans TC for body text.
4. **KPI tiles in the Creator Hub / MyASUS style**: 2 px coloured top line, light 42 px numerals with a smaller
   unit, and a thin ring gauge. A null value draws a dashed empty ring and prints "N/A", never 0 %.
5. **Device hero on 裝置與診斷**: "UGen300" in large light type, a one-line status, and a 2×2 tile grid
   (連線狀態, 執行後端, 相容性驗證, NPU 執行中). Detailed key/value rows follow, label left, value right.
6. **Nav rail with group labels** (專案 / 準備 / 檢查 / 系統), a filled active row with a 3 px accent bar.
   Below 1280 px the rail collapses to icons with hairline group dividers.
7. **Dense tables** with condensed uppercase column headers and right-aligned key/value rows (run info,
   device details, requirement facts).

## v3 (2026-10-26): reference layout + ProArt palette — supersedes the two sections above

The binding spec is `DESIGN_SPEC_v3.md` (sections 1, 2, 2b, 3). The charcoal/violet look, the angled corners,
the `////` condensed caps eyebrows and Barlow are gone. How the spec was applied:

- **Shell (R2–R4).** Floating rounded rail of 48 px round tools. Idle tools are glass, the active screen is a
  bronze-gradient circle with a bronze label, and the brand mark is the one solid-white circle. Labels show beside
  the circles at ≥ 1280 px; below that it is an icon rail with tooltips and aria-labels. The top bar has the
  screen name on the left and the project name as a glass pill in the centre, with a solid-white round "+"
  (switch or create project) and a glass refresh. The backend and UGen300 status sit as small outlined pills on
  the right and always show the real values.
- **Cards (R10, 2b).** `#141414` cards with a 1 px `#2A2A2A` border and 8 px radius, 14 px white card titles, no
  icons or slashes in the headers. In-card buttons are 4 px rectangles; floating controls and chips are pills.
  Nothing uses a radius in between. Line icons are 1.5 px.
- **Colour budget.** Bronze is used on only five things:
  - the one primary button per view (bronze fill with black text);
  - the active rail item;
  - the hero numeral (人工確認覆蓋, in the gradient text `#CEB497 → #766050`) and its gauge ring;
  - the playhead and active candidate;
  - the focus ring.

  Secondary actions such as 開啟覆蓋矩陣 are a 1 px bronze outline. Everything else is greyscale. Status colours
  (`#F2994A` / `#FF6B6B` / `#9B9B9B`) are used only on icons and 2 px row markers.
- **States.** The AI state is a bronze-outlined pill with an "AI" prefix. Human-confirmed or exception is a solid
  white pill with black text; not confirmed is an outlined grey pill. Every state still has its own icon and
  Chinese text.
- **Evidence stage (R1, R5–R9).**
  - A 32 px-radius black stage; the candidate video, or its frame in preview, fills it. Dark scrims sit under the
    floating pills (file, original range, take, backend, run, AI and human state).
  - A glass column of round transport tools: play (white), back to start (glass), loop (bronze while on).
  - A filmstrip of 12 frames sampled from the zoomed time range. Candidates are drawn as rounded segments with
    round end markers; the area outside the active range is dimmed. The playhead is a bronze line with a dot.
  - Below it, range chips `00:12.5 · · · 00:17.9`: bronze = current, white = reviewed on this version,
    dark = not reviewed, each with an icon and a full aria-label. A round "+" adds a manual segment.
  - A bronze bubble attached to the active chip holds 接受 / 拒絕 / 修正時段 / 需要補拍 / 人工接受例外.
    Forms open in a glass popover above the filmstrip.
  - 修正時段 shows dark round handles on the strip. They can be dragged, or moved with the arrow keys
    (100 ms steps; Shift = 1 s), and they stay in sync with the time inputs.
  - Cards below the stage: requirement and hard conditions, condition checks with 排序分數（非機率）, and the
    decision history with undo.
- **Type and motion.** Roboto + Noto Sans TC. Titles are 34 px weight 400 and KPI numerals 52 px weight 300 with a
  small unit; body text is `#C7C7C7` with 0.5 px tracking. Views fade in over 180 ms; all motion is off under
  `prefers-reduced-motion`.
