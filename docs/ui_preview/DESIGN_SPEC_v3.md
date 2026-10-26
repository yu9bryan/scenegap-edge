# SceneGap Edge UI, design spec v3

Two inputs, as the user asked: the **layout and component style** of a reference video-editor concept the user
supplied (a dance clip in an editor with floating round controls and a pill timeline), and the **colours of ASUS**
(measured on asus.com and the UGen300 product page, 2026-10-26). No ASUS logos, wordmarks or images; the product
stays "SceneGap Edge".

## 1. What the reference does (analysis)

| # | Observation in the reference | Why it works | How SceneGap uses it |
|---|---|---|---|
| R1 | The media fills the workspace edge to edge inside one large rounded container (radius ≈ 40 px); the UI floats on top | The footage is the subject; chrome never competes with it | Evidence viewer: the candidate frame/video fills the stage; controls float over it |
| R2 | Tools are **circular buttons** (≈ 48 px) in a floating vertical column on the left; no sidebar panel, no borders | Low visual weight, big hit targets, reads as "tools", not navigation chrome | Left rail = circular icon buttons for the 7 screens; label in a tooltip and an expanded state at ≥ 1280 px |
| R3 | Three button tiers: **solid white** (primary/back/save), **translucent grey glass** (idle tools), **accent fill** (the one active tool) | One glance shows what is active; the accent appears once | Same three tiers; the accent is ASUS blue |
| R4 | The project name is a **translucent dark pill** centred at the top, with a round "+" beside it | Context without a heavy header bar | Top bar = project pill + round actions (switch project, refresh); backend/device as small pills on the right |
| R5 | The timeline is a **filmstrip of thumbnails inside pill-shaped segments**, with round "+" insert buttons between them | Time is visual; insert points are explicit | Evidence viewer: filmstrip of the asset's sampled frames; candidate ranges drawn as pill segments; round markers at range starts/ends |
| R6 | The selected segment has **dark round handles** at both ends | Clear edit affordance for a range | "Fix range" mode shows the same round handles on the selected candidate |
| R7 | The **playhead** is a thin accent line with a **dot** on top, crossing filmstrip and chips | Ties the two time views together | Same, in ASUS blue |
| R8 | Below, **time-range chips**: `00s · · · 10s`. Earlier chips are white with dark text, the active chip is accent-filled, later chips are dark with light text | A second, coarse index of time; state is shown by fill only | Candidate list as range chips `00:12.4 · · · 00:17.9`; active chip blue; reviewed chips white; unreviewed dark |
| R9 | A contextual **accent bubble** grows out of the active "+" with a small connector, holding 3 round icons | Actions appear where the user is looking | Accept / reject / fix range / reshoot appear as a bubble attached to the active candidate chip |
| R10 | No hairlines or boxes; separation comes from fill, radius and space. Generous gaps (≈ 8–12 px between chips, 24 px margins) | Calm, product-like rather than dashboard-like | Cards without borders; 20–28 px radius; 24 px page padding; 12–16 px gaps |
| R11 | Typography: clean sans, regular/medium, small sizes on chips (≈ 14–15 px), no all-caps labels | Friendly, consumer-grade | Roboto + Noto Sans TC; numbers in tabular figures; no condensed caps labels |
| R12 | Soft drop shadow under the whole device frame, none inside | Depth only at the outer level | One soft shadow for floating layers (rail, top pills, bubble); none on cards |

## 2. Colours: ASUS ProArt (measured; user's choice, replaces the generic ASUS blue)

The user asked for the **ProArt** palette (ASUS's creator line). Measured from computed styles on
https://www.asus.com/proart/ on 2026-10-26:

| Token | Value | Seen as |
|---|---|---|
| `--pa-black` | `#000000` | dominant page background |
| `--pa-ink` | `#0F0F11` | second dark surface |
| `--pa-glass` | `rgba(51,51,51,0.30)` + backdrop blur | floating panels and dialogs |
| `--pa-panel` | `#333333` | solid dark controls; `#4D4D4D` borders |
| `--pa-bronze` | `#CDAB82` (also `#CDA882`) | the single accent: primary buttons, active states, links, focus |
| `--pa-bronze-grad` | `linear-gradient(135deg, #DFC9A9, #CDAB82 50.78%, #9A7A59)` | primary pill buttons |
| `--pa-bronze-hi` | `#D7B286` | hover |
| `--pa-text` | `#F5F5F5` / `#FFFFFF` | headings, primary text |
| `--pa-text-2` | `#C7C7C7` | body text |
| `--pa-text-3` | `#9B9B9B` / `#757575` | secondary, disabled |
| text on bronze | `#000000` | buttons are bronze with black text |
| radius | `80px` pills for buttons/chips, `8px` small, `32px` large panels | |
| font | Roboto (body) + TT Norms Pro Medium (headings, proprietary) | we use Roboto + Noto Sans TC |

Contrast: bronze on black ≈ 9.7:1, black on bronze ≈ 9.7:1, #C7C7C7 on #0F0F11 ≈ 12:1. Bronze on white is too
weak (≈ 2:1), so the whole app is **dark**, as ProArt's site is.

Status colours are not in the ProArt palette; we add them only as small icons/dots with text, tuned for black
backgrounds and kept away from the bronze hue: partial `#F2994A`, not found `#FF6B6B`, unverifiable / not analysed
`#9B9B9B`.

## 2b. ProArt style in detail (measured 2026-10-26 on asus.com/proart and the ProArt Creator Hub page)

**Mood.** Studio-at-night: product and footage glow out of black, the brand speaks in one warm metal colour
(champagne bronze), everything else is greyscale. Calm, premium, low saturation; no playful colours, no heavy
shadows, very little decoration. Confidence comes from large light type and space, not from boxes.

**Typography.**

| Role | Measured | SceneGap use |
|---|---|---|
| Hero / product name | TT Norms Pro Normal/Medium, 44–68 px, weight 400–500, line-height ≈ 1.1, no caps, no tracking | screen titles 32–40 px, weight 400–500 |
| Section heading | TT Norms Pro Medium 44 px, centred, **bronze gradient text** `linear-gradient(39deg, #CEB497, #766050)` via `background-clip:text` | page section titles and KPI numerals (one per view) |
| Sub-headline | Roboto 26–30 px, `#C7C7C7` | screen subtitles 18–20 px |
| Body | Roboto / TT Norms 16 px, line-height 24 px, letter-spacing 0.5 px, `#C7C7C7` on black | body 14–16 px, same tracking |
| Nav / labels | Roboto 14 px, weight 500, `#C7C7C7`; active nav text bronze `#CDAB82` | rail labels, table headers (no all-caps) |
| Numerals (Creator Hub app) | very large, **light** weight (e.g. "7 %"), unit small beside | KPI numbers 48–56 px weight 300, unit 16 px |

Fonts we can ship: **Roboto** (ProArt's own body font) for Latin, **Noto Sans TC** for Chinese; TT Norms Pro is
proprietary, so headings use Roboto 400/500 at large size to imitate its even, geometric feel.

**Colour proportions.** ≈ 85% black/near-black surfaces, ≈ 12% greys (text, lines, glass), ≤ 3% bronze. Bronze is
reserved for: the one primary button per view, the active item, the key numeral/gauge, the playhead, focus.

| Pairing | Use |
|---|---|
| Bronze `#CDA882` fill + black `#000` text | primary button ("Learn more": 36 px high, padding 7/16/9 px, square or pill) |
| Bronze outline 1 px + bronze text on black | secondary button ("Stay here" style), AI-state pill |
| Bronze gradient text `#CEB497 → #766050` | section headings, hero numeral |
| Bronze gradient fill `#DFC9A9 → #CDAB82 → #9A7A59` (135°) | gauges/rings, progress fill, active range in the timeline |
| `#C7C7C7` on `#000` | body text; `#9B9B9B` secondary; `#757575` disabled |
| White `#FFF` on `#000` | product names, titles; white pill + black text for human-confirmed |
| Glass `rgba(51,51,51,.30)` + blur over imagery | floating panels, dialogs, top bar over video |
| `#333333` / `#4D4D4D` 1 px | card borders and dividers in the Creator Hub app |

**Shapes.**
- Buttons: two shapes coexist on ProArt pages: crisp rectangles (radius 0–4 px, the classic ProArt CTA) and full
  pills (radius 80 px) in dialogs. SceneGap uses **pills** for floating controls and chips (fits the user's
  reference) and **4 px** for in-card buttons, never in between.
- Cards in the Creator Hub app: near-black `#141414`–`#1C1C1C`, 1 px `#2A2A2A`–`#333` border, small radius
  6–8 px, generous inner padding, title 14 px white top-left, controls top-right.
- Large containers (media stage, hero): radius 32 px.
- Gauges: thin rings with a bronze gradient arc; progress bars thin (4 px) with bronze fill on `#333` track.
- Icons: thin line icons (1.5 px stroke), monochrome `#C7C7C7`, bronze when active.
- Imagery is the hero: full-bleed photos/video with a dark gradient scrim (`linear-gradient(90deg, rgba(0,0,0,.9), transparent)`) for text on top.

**Motion.** Sections fade in on scroll (opacity + slight rise). SceneGap: 150–200 ms fades on view change; none
when `prefers-reduced-motion`.

## 3. Mapping to SceneGap

- **Dark canvas everywhere** (`#000` page, `#0F0F11` cards, glass for floating layers). The evidence viewer is the
  media stage of R1: the footage fills it.
- **One accent**: ProArt bronze for the active nav button, primary action (gradient pill, black text), active
  candidate chip, playhead and dot, focus ring.
- **AI vs human stays separate** (product rule): AI state = bronze-outlined pill with an "AI" prefix and icon;
  human confirmed = solid **white** pill with black text; unconfirmed = outlined grey. Never colour alone: every
  state keeps icon + Chinese text.
- **Honest numbers stay**: N/A cards keep their reason; ranking score labelled 排序分數（非機率）; backend pill always
  says `cpu-reference` / `cuda-reference`; device pill says UGen300 未連線 when not connected.
- Floating circular left rail (R2/R3: white = primary, glass = idle, bronze = active), top project glass pill (R4),
  evidence stage with filmstrip + range chips + playhead + bronze action bubble (R5–R9), borderless cards (R10),
  Roboto (R11), shadow/blur only on floating layers (R12).
- Accessibility: focus ring 2 px bronze + 2 px black offset; hit targets ≥ 40 px; prefers-reduced-motion.

ASUS-wide reference values measured the same day (not used now): ASUS blue `#006CE1`, canvas `#F5F5F5`.
