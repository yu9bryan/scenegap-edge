# Publishing checklist

How to put the repository and the project page online. Nothing here is automated except the Pages deploy.

## 1. Replace the placeholders

Two placeholders are used wherever the team name or the GitHub owner is not known yet:

| Placeholder | Replace with | Files |
|---|---|---|
| `[Team name]` | the registered team name | `README.md`, `README.zh-TW.md`, `site/index.html` |
| `[team]` | the GitHub user or organisation that owns the repository | the same three files (repository, Pages and release URLs) |

Find every occurrence before committing (this file is excluded because it explains them):

```bash
git grep -n -e "\[Team name\]" -e "\[team\]" -- . ":!docs/PUBLISHING.md"
```

The same placeholders are baked into the proposal deck (`docs/deck/make_spec.py`, then the PDF and PPTX) and the
demo video end card (`docs/video/make_video.py`). Regenerate those after replacing them in the scripts; the copy of
the deck in `site/assets/` must then be refreshed from `docs/deck/`.

Replace them, for example with `sed` (check the result with `git diff`):

```bash
sed -i 's/\[Team name\]/Your Team/g; s/\[team\]/your-github-owner/g' README.md README.zh-TW.md site/index.html
```

If the repository is not called `scenegap-edge`, also change `scenegap-edge` in those URLs.

## 2. Create the repository and push

```bash
git remote add origin https://github.com/<owner>/scenegap-edge.git
git push -u origin main
```

The CI workflow (`.github/workflows/ci.yml`) runs the tests on Python 3.10 and 3.12 on every push.

## 3. Enable GitHub Pages

1. On GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Push a change under `site/` to `main`, or run the **pages** workflow by hand (**Actions → pages → Run workflow**).
3. The page appears at `https://<owner>.github.io/scenegap-edge/`. The workflow uploads the `site/` folder as it
   is; there is no build step.

The page uses only relative paths, so it also works opened from disk (`site/index.html`).

## 4. Demo video

- **Small version for the page:** copy the rendered file to `site/assets/SceneGapEdge_StageI_Demo.mp4` before
  committing. Until it is there, the player shows the poster frame (`site/assets/04_coverage.png`) and the video link
  answers 404. Keep this file small (well under 20 MB) so the repository stays light.
- **Full resolution:** do not commit it. Create a release and attach it as an asset:

  ```bash
  gh release create v0.1.0 --title "SceneGap Edge Stage I" --notes "Stage I submission" path/to/SceneGapEdge_StageI_Demo_full.mp4
  ```

  or on GitHub: **Releases → Draft a new release**, attach the file, publish. The README and the page link to
  `https://github.com/<owner>/scenegap-edge/releases`.

## 5. Before you make the repository public

- The `git grep` from step 1 returns nothing (binary matches in the deck PDF mean it still needs regenerating).
- `python -m pytest -q` passes.
- The page loads on a phone and a desktop, the video plays, and every link opens.
- Footage credits are in `docs/CREDITS.md` and on the page.
