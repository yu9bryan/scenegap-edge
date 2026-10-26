"""Exports (FR-EXP-01/02): machine-readable JSON and CSV, and an offline HTML report.
Every export names its run, scope and versions. CSV cells cannot start a spreadsheet formula (TC-021);
HTML escapes every user-supplied string and loads nothing remote."""
from __future__ import annotations

import csv
import html
import io
import json

SCHEMA_VERSION = "1.0"
_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(v) -> str:
    s = "" if v is None else str(v)
    return "'" + s if s.startswith(_FORMULA) else s


def to_json(view: dict, cards: list[dict], project: dict, device: dict) -> str:
    return json.dumps({"schema_version": SCHEMA_VERSION, "project": project, "run": view.get("run"), "outdated": view.get("outdated"),
                       "coverage": view.get("coverage"), "scope": view.get("scope"), "requirements": view.get("requirements"),
                       "reshoot_cards": cards, "device": device}, ensure_ascii=False, indent=1)


def to_csv(view: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["requirement_id", "revision", "source_text", "auto_status", "human_confirmed", "human_exception", "reasons",
                "candidate_asset", "start_ms", "end_ms", "ranking_score", "conditions", "run_id", "backend", "model_fingerprint"])
    run = view.get("run") or {}
    for row in view.get("requirements", []):
        r, a = row["requirement"], row["auto"] or {}
        cands = a.get("candidates") or [None]
        for c in cands:
            w.writerow([csv_safe(x) for x in [
                r["requirement_id"], r["revision"], r["source_text"], "outdated" if row["auto_outdated"] else a.get("status"),
                row["human_confirmed"], row["human_exception"], "|".join(a.get("reasons", [])),
                c and c["asset_id"], c and c["start_ms"], c and c["end_ms"], c and c["ranking_score"],
                c and "; ".join(f"{x['kind']}={x['verdict']}" for x in c["conditions"]),
                run.get("run_id"), run.get("backend"), run.get("model_fingerprint")]])
    return buf.getvalue()


def to_html(view: dict, cards: list[dict], project: dict, thumbs: dict[str, str] | None = None) -> str:
    e = lambda s: html.escape("" if s is None else str(s))
    cov = view.get("coverage") or {}
    pct = lambda v: "N/A" if v is None else f"{v*100:.0f}%"
    run = view.get("run") or {}
    rows = []
    for row in view.get("requirements", []):
        r, a = row["requirement"], row["auto"] or {}
        st = "已過期，需重新分析" if row["auto_outdated"] else a.get("status_zh", "")
        human = "人工接受例外" if row["human_exception"] else ("已接受" if row["human_confirmed"] else "未決定")
        c = (a.get("candidates") or [None])[0]
        ev = f"{e(c['asset_id'])} {c['start_ms']/1000:.1f}–{c['end_ms']/1000:.1f}s" if c else "—"
        img = f'<img src="{thumbs[c["asset_id"]]}" alt="">' if c and thumbs and thumbs.get(c["asset_id"]) else ""
        rows.append(f"<tr><td>{e(r['requirement_id'])}<br><small>rev {e(r['revision'])}</small></td><td>{e(r['source_text'])}</td>"
                    f"<td>{e(st)}</td><td>{e(human)}</td><td>{img}{ev}</td><td>{e('、'.join(a.get('reasons', [])))}</td></tr>")
    crd = "".join(f"<li><b>{e(c['requirement_id'])}</b> {'先複核' if c['review_first'] else '建議補拍（待決定）'}："
                  f"{e(c['source_text'])}；原因：{e('、'.join(c['reasons_zh']))}；最短連續 {c['min_continuous_s']:.1f} 秒；驗證方式：{e(c['verify_by'])}</li>"
                  for c in cards)
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>SceneGap 報告 {e(project.get('name'))}</title>
<style>body{{font:14px/1.6 system-ui,'Noto Sans TC',sans-serif;margin:32px;color:#16151d}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ddd;padding:6px 8px;vertical-align:top}}th{{background:#f3f1ff;text-align:left}}img{{height:48px;margin-right:6px;vertical-align:middle}}
.warn{{background:#fff4e5;padding:8px 12px;border-radius:8px}}</style></head><body>
<h1>拍攝需求覆蓋報告：{e(project.get('name'))}</h1>
<p>Run {e(run.get('run_id'))} · {e(run.get('created_at'))} · 後端 {e(run.get('backend'))} · 模型 {e(run.get('model_fingerprint'))} · 設定 {e(run.get('config_hash'))}</p>
{"<p class='warn'>此報告的自動結果已過期（需求或素材在分析後有變更），請重新分析。</p>" if view.get('outdated') else ""}
<p>人工確認覆蓋 {pct(cov.get('human_confirmed'))} · AI 候選覆蓋 {pct(cov.get('ai_candidate'))} · 分析進度 {pct(cov.get('analysis_progress'))} · 未能自動判定 {e(cov.get('unknown_count'))} 項</p>
<p><small>「在已分析範圍未找到」不代表沒有拍；候選不等於完成；AI 分數是排序分數，不是機率。</small></p>
<table><tr><th>需求</th><th>原文</th><th>自動狀態</th><th>人工狀態</th><th>最佳證據</th><th>原因</th></tr>{''.join(rows)}</table>
<h2>複核／補拍清單</h2><ol>{crd or '<li>無</li>'}</ol></body></html>"""
