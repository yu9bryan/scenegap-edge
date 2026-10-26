# Labelling guide (given to both annotators; written before labelling)

You label what is **clearly visible** in each 1-frame-per-second contact sheet. You never see system output.

For each clip and each requirement below, list the sample times (seconds, as printed under each thumbnail,
`t=12.0s`) where the requirement's visual content is clearly on screen in that frame. Ignore duration and number of
takes; the scorer computes those. When a frame is too small, blurred or ambiguous, leave it out (label only clear
cases). A thumbnail with `shot k` belongs to shot k of the clip.

| id | label the frame when … |
|---|---|
| SH-01 | the outside of a café/coffee shop is visible from the street (storefront, terrace, sign, façade). Not any street. |
| SH-02 | the inside of a café/coffee shop with tables or chairs is visible (a room view, not a close-up of a cup). |
| SH-03 | coffee beans (roasted or green) fill a clear part of the frame, close up. |
| SH-04 | a coffee grinder is grinding, or ground coffee is coming out of a grinder. |
| SH-05 | coffee or milk is being poured into a cup/glass (incl. latte art pouring, pour-over, espresso dripping into a cup). |
| SH-06 | a cup/glass of coffee is the main subject, standing (on a table, saucer, counter), not being poured into. |
| SH-07 | a person is holding a coffee cup to drink or is drinking from it. |
| SH-08 | at least two people are in the same frame inside a café/coffee shop. |
| SH-09 | an espresso machine is extracting (coffee flowing from the group head / portafilter). |
| SH-10 | a bag, box or package of coffee is visible. Also answer separately whether a brand name on it is readable: yes / no / cannot tell. |
| SH-11 | a barista/worker is preparing coffee (behind a counter, at a machine, pouring, tamping). |

Output (JSON, one object): `{"clip.mp4": {"SH-01": [t, ...], ..., "SH-10_brand_readable": "yes|no|cannot tell|n/a"}, ...}`.
Every clip and every id must appear; use `[]` when none.

Scoring rule: a labelled sample at time t stands for the interval [t, t + 1 s). Consecutive labelled samples in the
same shot are merged.
