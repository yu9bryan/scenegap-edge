/* SceneGap Edge web UI — vanilla JS, no build step, no external libraries.
 *
 * Safety rule: every string that comes from the server is inserted with textContent / setAttribute
 * (through h()). innerHTML is used only for the constant icon SVG paths defined in this file.
 *
 * Preview mode: when window.SG_PREVIEW is set (docs/ui_preview/preview.html), api() answers from
 * that object instead of fetch() and the page shows a "預覽資料（非實測）" ribbon.
 */
(function () {
  'use strict';

  const PREVIEW = window.SG_PREVIEW || null;
  const API = '/api/v1';
  const TOKEN = (document.querySelector('meta[name="sg-token"]') || {}).content || '';

  // ------------------------------------------------------------------ DOM helpers
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (k === 'checked') { el.checked = !!v; continue; }
        if (k === 'value') { if (v != null) el.value = v; continue; }
        if (v == null || v === false) continue;
        if (k === 'class') el.className = v;
        else if (k === 'text') el.textContent = v;
        else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
        else if (v === true) el.setAttribute(k, '');
        else el.setAttribute(k, String(v));
      }
    }
    add(el, kids);
    return el;
  }
  function add(el, kids) {
    for (const k of [kids].flat(Infinity)) {
      if (k == null || k === false) continue;
      el.append(k instanceof Node ? k : document.createTextNode(String(k)));
    }
    return el;
  }
  const $ = (sel, root) => (root || document).querySelector(sel);

  // Constant icon paths (24x24, stroke). Never contains server data.
  const ICONS = {
    home: '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>',
    list: '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M4 6h.01M4 12h.01M4 18h.01"/>',
    film: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    board: '<rect x="3" y="4" width="5" height="16" rx="1"/><rect x="10" y="4" width="5" height="11" rx="1"/><rect x="17" y="4" width="4" height="7" rx="1"/>',
    cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    dashed: '<path d="M10.1 2.2a10 10 0 0 1 3.8 0M17.6 4.1a10 10 0 0 1 2.3 2.3M21.8 10.1a10 10 0 0 1 0 3.8M19.9 17.6a10 10 0 0 1-2.3 2.3M13.9 21.8a10 10 0 0 1-3.8 0M6.4 19.9a10 10 0 0 1-2.3-2.3M2.2 13.9a10 10 0 0 1 0-3.8M4.1 6.4a10 10 0 0 1 2.3-2.3"/>',
    loader: '<path d="M21 12a9 9 0 1 1-6.2-8.6"/>',
    target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/>',
    half: '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor" stroke="none"/>',
    searchx: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3M8.5 8.5l5 5M13.5 8.5l-5 5"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5v.7"/><path d="M12 17h.01"/>',
    alert: '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
    pencil: '<path d="M17 3l4 4L8 20H4v-4z"/>',
    checkc: '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    flag: '<path d="M4 21V4M4 4h12l-2 4 2 4H4"/>',
    circle: '<circle cx="12" cy="12" r="9"/>',
    check: '<path d="M5 12l5 5L20 7"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    xc: '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    plugoff: '<path d="M9 2v5M15 2v5M6 7h12v4a6 6 0 0 1-12 0zM12 17v5"/><path d="M3 3l18 18"/>',
    plug: '<path d="M9 2v5M15 2v5M6 7h12v4a6 6 0 0 1-12 0zM12 17v5"/>',
    play: '<path d="M7 4l13 8-13 8z"/>',
    pause: '<path d="M7 4h3v16H7zM14 4h3v16h-3z"/>',
    back: '<path d="M19 20L9 12l10-8z"/><path d="M5 19V5"/>',
    repeat: '<path d="M17 2l4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="M7 22l-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M12 11v6M9 14h6"/>',
    download: '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
    refresh: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
    scissors: '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M8.1 8.1L20 20M8.1 15.9L20 4"/>',
    camera: '<path d="M23 7l-7 5 7 5z"/><rect x="1" y="5" width="15" height="14" rx="2"/>',
    hand: '<path d="M8 13V5a1.5 1.5 0 0 1 3 0v6M11 11V4a1.5 1.5 0 0 1 3 0v7M14 11V5.5a1.5 1.5 0 0 1 3 0V14a7 7 0 0 1-7 7h-1a6 6 0 0 1-5-3l-2.5-4.5a1.5 1.5 0 0 1 2.6-1.5L8 15"/>',
    ban: '<circle cx="12" cy="12" r="9"/><path d="M5.6 5.6l12.8 12.8"/>',
    sparkle: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    external: '<path d="M14 3h7v7M21 3l-9 9"/><path d="M19 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="1"/>',
    left: '<path d="M19 12H5M12 19l-7-7 7-7"/>',
    right: '<path d="M5 12h14M12 5l7 7-7 7"/>',
    file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>',
    beaker: '<path d="M9 3h6M10 3v6L4.5 18.5A2 2 0 0 0 6.2 21h11.6a2 2 0 0 0 1.7-2.5L14 9V3"/>',
    open: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  };
  function icon(name, cls) {
    const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    s.setAttribute('viewBox', '0 0 24 24');
    s.setAttribute('fill', 'none');
    s.setAttribute('stroke', 'currentColor');
    s.setAttribute('stroke-width', '2');
    s.setAttribute('stroke-linecap', 'round');
    s.setAttribute('stroke-linejoin', 'round');
    s.setAttribute('aria-hidden', 'true');
    s.setAttribute('focusable', 'false');
    s.setAttribute('class', 'ico' + (cls ? ' ' + cls : ''));
    s.innerHTML = ICONS[name] || ICONS.circle;      // constant strings only
    return s;
  }

  // ------------------------------------------------------------------ vocabularies (PRD wording)
  const AUTO = {
    not_analyzed: { zh: '尚未分析', icon: 'dashed', tone: 'slate' },
    analyzing: { zh: '分析中', icon: 'loader', tone: 'cyan', spin: true },
    candidate: { zh: '有候選，待確認', icon: 'target', tone: 'violet' },
    partial: { zh: '部分符合', icon: 'half', tone: 'amber' },
    not_found: { zh: '在已分析範圍未找到', icon: 'searchx', tone: 'red' },
    unverifiable: { zh: '無法自動確認', icon: 'help', tone: 'orange' },
    failed: { zh: '分析失敗', icon: 'alert', tone: 'red' },
    draft: { zh: '草稿（未確認）', icon: 'pencil', tone: 'slate' },
  };
  const AUTO_STALE = { zh: '結果已過期，需重新分析', icon: 'clock', tone: 'slate' };
  const HUMAN = {
    confirmed: { zh: '已人工確認', icon: 'checkc', tone: 'green' },
    exception: { zh: '人工接受例外', icon: 'flag', tone: 'amber' },
    none: { zh: '未確認', icon: 'circle', tone: 'slate' },
  };
  const REASON_ZH = {
    NO_CANDIDATE: '已分析範圍內沒有候選', DURATION_SHORT: '連續時長不足', DURATION_UNKNOWN: '連續時長未能確認',
    QUALITY_WARNING: '品質警示', NEEDS_MANUAL: '含需人工確認的條件', EVIDENCE_UNKNOWN: '證據不足',
    TAKES_SHORT: '獨立 take 數不足', SCOPE_INCOMPLETE: '仍有素材未分析或失敗', UNSUPPORTED_CORE: '核心條件此版本不支援',
    ANALYSIS_FAILED: '分析失敗', NOT_ANALYZED: '尚未分析', NO_ASSETS: '尚未加入素材', CONSTRAINT_FAILED: '條件不符',
  };
  const ASSET_ST = {
    pending: { zh: '待分析', icon: 'dashed', tone: 'slate' },
    analyzing: { zh: '分析中', icon: 'loader', tone: 'cyan', spin: true },
    analyzed: { zh: '已分析', icon: 'checkc', tone: 'green' },
    failed: { zh: '解析失敗', icon: 'alert', tone: 'red' },
    missing: { zh: '檔案離線', icon: 'plugoff', tone: 'orange' },
    excluded: { zh: '已排除', icon: 'ban', tone: 'slate' },
  };
  const VERDICT = {
    pass: { zh: '通過', icon: 'checkc', tone: 'green', cls: 'v-pass' },
    fail: { zh: '不符', icon: 'xc', tone: 'red', cls: 'v-fail' },
    unknown: { zh: '未能確認', icon: 'help', tone: 'amber', cls: 'v-unknown' },
  };
  const CAP = {
    auto: { zh: '自動', icon: 'sparkle', tone: 'cyan' },
    manual: { zh: '人工', icon: 'hand', tone: 'amber' },
    unsupported: { zh: '不支援', icon: 'ban', tone: 'slate' },
  };
  const KIND_ZH = {
    semantic: '語意內容', co_occur: '同框共現', duration: '連續時長', takes: '獨立 take 數', quality: '畫質',
    readable_text: '可讀文字', action: '動作', composition: '構圖', forbidden: '禁止出現',
  };
  const JOB_ST = {
    queued: { zh: '排隊中', icon: 'clock', tone: 'slate' },
    running: { zh: '執行中', icon: 'loader', tone: 'cyan', spin: true },
    done: { zh: '已完成', icon: 'checkc', tone: 'green' },
    failed: { zh: '失敗', icon: 'alert', tone: 'red' },
    cancelled: { zh: '已取消', icon: 'stop', tone: 'slate' },
  };
  const STAGE_ZH = {
    'queued': '排隊等待中', 'analyzing assets': '解析素材中（切鏡、取樣、計算特徵）', 'matching requirements': '比對需求中',
    'done': '完成', 'cancelled by user': '已由使用者取消', 'resumed after restart': '服務重啟後自動續跑', 'failed': '失敗',
  };
  const RESHOOT_ST = [
    ['proposed', '待確認'], ['confirmed', '已確認補拍'], ['shooting', '拍攝中'], ['done', '已完成'], ['dismissed', '已略過'],
  ];
  const RESHOOT_TONE = { proposed: 'slate', confirmed: 'violet', shooting: 'cyan', done: 'green', dismissed: 'slate' };
  const RESHOOT_ICON = { proposed: 'dashed', confirmed: 'check', shooting: 'camera', done: 'checkc', dismissed: 'ban' };
  const WARN_ZH = {
    'non-zero start time': '起始時間不為 0（時間碼以原始時間戳為準）',
    'variable frame rate suspected; timestamps use PTS': '疑似可變影格率；時間以 PTS 為準',
  };
  const NEXT_STEP = {
    NETWORK: '無法連線到本機服務。請確認 SceneGap 仍在執行，再重新整理本頁。',
    UNAUTHORIZED: '工作階段權杖已失效。請從 SceneGap 啟動程式重新開啟本頁。',
    ORIGIN_REJECTED: '請直接從 SceneGap 啟動程式開啟的網址使用本工具。',
    NOT_FOUND: '項目不存在或已被移除。請重新整理後再試。',
    ROOT_NOT_FOUND: '找不到這個資料夾。請確認路徑存在、磁碟已連接，再重新授權。',
    PATH_NOT_ALLOWED: '只能讀取已授權資料夾內的檔案。請先授權包含該檔案的資料夾。',
    STALE_REVISION: '需求已被修改，請重新載入。',
    REASON_REQUIRED: '請填寫理由後再送出。',
    BAD_INTERVAL: '時段需落在影片長度內，且開始時間要早於結束時間。',
    UNCALIBRATED: '語意門檻尚未校準，目前無法搜尋。請先執行校準流程。',
    SCHEMA: '欄位內容不符合格式，請檢查後再送出。',
    ASSET_MISSING: '素材離線或已被移動。請重新連接磁碟或重新授權資料夾。',
    NO_FRAME: '這個時間點取不到影格，請改選其他時間。',
    MODEL_MISMATCH: '模型版本與既有索引不一致，請重新分析。',
    PREVIEW: '預覽模式只顯示範例資料，不會寫入任何東西。',
  };

  // ------------------------------------------------------------------ formatting
  function pad(n, w) { return String(n).padStart(w, '0'); }
  function fmtTime(ms) {
    if (ms == null || !isFinite(ms)) return '—';
    const neg = ms < 0; ms = Math.abs(Math.round(ms));
    return (neg ? '-' : '') + pad(Math.floor(ms / 60000), 2) + ':' + pad(Math.floor(ms % 60000 / 1000), 2) + '.' + pad(ms % 1000, 3);
  }
  function parseTime(str) {
    const t = String(str || '').trim();
    if (!t) return NaN;
    const parts = t.split(':');
    if (parts.length > 3) return NaN;
    let sec = 0;
    for (const p of parts) { if (!/^\d+(\.\d+)?$/.test(p)) return NaN; sec = sec * 60 + parseFloat(p); }
    return Math.round(sec * 1000);
  }
  function fmtPct(x) {
    if (x == null || !isFinite(x)) return null;
    const v = x * 100;
    return (Math.abs(v - Math.round(v)) < 0.05 ? Math.round(v).toString() : v.toFixed(1)) + '%';
  }
  function fmtDate(s) {
    if (!s) return '—';
    const d = new Date(s);
    return isNaN(d) ? String(s) : d.toLocaleString('zh-TW', { hour12: false });
  }
  function fmtSec(ms) { return ms == null ? '—' : (ms / 1000).toFixed(ms % 1000 ? 1 : 0) + ' 秒'; }
  function short(s, n) { s = String(s == null ? '' : s); return s.length > n ? s.slice(0, n) + '…' : s; }
  function firstLine(s) { return String(s || '').split('\n')[0].slice(0, 240); }
  function baseName(p) { return String(p || '').split(/[\\/]/).pop(); }

  // ------------------------------------------------------------------ storage (per-viewer conveniences only)
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* ignore */ } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* ignore */ } },
  };

  // ------------------------------------------------------------------ API
  class ApiError extends Error {
    constructor(status, body) {
      body = body && typeof body === 'object' ? body : {};
      const code = body.code || (status === 422 ? 'SCHEMA' : status ? 'HTTP_' + status : 'NETWORK');
      super(typeof body.message === 'string' ? body.message : (status ? '服務回應錯誤（HTTP ' + status + '）' : '無法連線到本機服務'));
      this.status = status; this.code = code; this.recoverable = body.recoverable !== false;
      this.stage = body.stage || null; this.asset_id = body.asset_id || null; this.request_id = body.request_id || null;
    }
  }

  function previewApi(method, path, body) {
    const key = method + ' ' + path.split('?')[0];
    const routes = PREVIEW.routes || {};
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (Object.prototype.hasOwnProperty.call(routes, key)) {
          const v = routes[key];
          if (v && v.__error) return reject(new ApiError(v.__error.status || 400, v.__error));
          return resolve(JSON.parse(JSON.stringify(v)));
        }
        if (method === 'GET') return reject(new ApiError(404, { code: 'NOT_FOUND', message: 'preview: no sample data for ' + key }));
        resolve({ ok: true, preview: true, decision_id: 'd_preview', job_id: 'j_demo', backend: 'cpu-reference', model_fingerprint: 'preview' });
      }, 30);
    });
  }

  async function api(method, path, body) {
    if (PREVIEW) return previewApi(method, path, body);
    const headers = { 'X-SG-Token': TOKEN, 'Accept': 'application/json' };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    let res;
    try {
      res = await fetch(API + path, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
    } catch (e) {
      throw new ApiError(0, { code: 'NETWORK', message: '無法連線到本機服務' });
    }
    let data = null;
    const ct = res.headers.get('content-type') || '';
    try { data = ct.includes('json') ? await res.json() : await res.text(); } catch (e) { data = null; }
    if (!res.ok) throw new ApiError(res.status, data);
    return data;
  }

  // Media: <img>/<video> cannot send the X-SG-Token header, so media is fetched with the header and
  // handed to the element as a blob: URL. (See report: a short-lived media URL would allow streaming.)
  const blobCache = new Map();
  function authBlob(path) {
    if (blobCache.has(path)) return blobCache.get(path);
    const p = fetch(API + path, { headers: { 'X-SG-Token': TOKEN } }).then(async (r) => {
      if (!r.ok) { let b = null; try { b = await r.json(); } catch (e) { /* not json */ } throw new ApiError(r.status, b); }
      return URL.createObjectURL(await r.blob());
    });
    blobCache.set(path, p);
    p.catch(() => blobCache.delete(path));
    return p;
  }
  const frameQ = []; let frameActive = 0;
  function pumpFrames() {
    while (frameActive < 3 && frameQ.length) {
      const job = frameQ.shift(); frameActive++;
      job.fn().then(job.res, job.rej).finally(() => { frameActive--; pumpFrames(); });
    }
  }
  function frameUrl(aid, t) {
    if (PREVIEW) return Promise.resolve((PREVIEW.frames || {})[aid] || null);
    const path = '/assets/' + encodeURIComponent(aid) + '/frame?t_ms=' + Math.max(0, Math.round(t || 0));
    if (blobCache.has(path)) return blobCache.get(path);
    return new Promise((res, rej) => { frameQ.push({ fn: () => authBlob(path), res, rej }); pumpFrames(); });
  }
  function videoUrl(aid) {
    if (PREVIEW) return Promise.resolve(null);
    return authBlob('/assets/' + encodeURIComponent(aid) + '/media');
  }

  async function doExport(fmt) {
    if (!S.pid) return;
    if (PREVIEW) { toast({ kind: 'info', title: '預覽模式不會產生檔案', text: '連線到本機服務時，這裡會下載 ' + fmt.toUpperCase() + ' 報告。' }); return; }
    try {
      const r = await fetch(API + '/projects/' + encodeURIComponent(S.pid) + '/exports/' + fmt, { headers: { 'X-SG-Token': TOKEN } });
      if (!r.ok) { let b = null; try { b = await r.json(); } catch (e) { /* */ } throw new ApiError(r.status, b); }
      const url = URL.createObjectURL(await r.blob());
      if (fmt === 'html') { window.open(url, '_blank', 'noopener'); }
      else {
        const a = h('a', { href: url, download: 'scenegap_' + S.pid + '.' + fmt });
        document.body.append(a); a.click(); a.remove();
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      toast({ kind: 'ok', title: '已匯出 ' + fmt.toUpperCase() });
    } catch (e) { showError(e, '匯出失敗'); }
  }

  // ------------------------------------------------------------------ state
  const S = {
    pid: PREVIEW ? PREVIEW.project_id : store.get('sg.pid', null),
    project: null, health: null, device: null,
    jobId: null, job: null, jobTimer: null, jobSubs: new Set(),
    route: { name: 'home', params: [] },
  };
  let cleanup = [];
  let renderSeq = 0;

  function setProject(pid, name) {
    S.pid = pid; S.project = null;
    if (!PREVIEW) store.set('sg.pid', pid);
    if (pid && name) {
      const recent = store.get('sg.recent', []).filter((r) => r.id !== pid);
      recent.unshift({ id: pid, name, at: Date.now() });
      store.set('sg.recent', recent.slice(0, 8));
    }
    restoreJob();
  }

  // ------------------------------------------------------------------ small components
  function chip(def, opts) {
    opts = opts || {};
    const c = h('span', {
      class: 'chip tone-' + def.tone + (opts.human ? ' human' : '') + (opts.lg ? ' lg' : '') + (opts.outline ? ' outline' : ''),
      title: opts.title, 'aria-label': opts.aria,
    },
    opts.prefix ? h('span', { class: 'chip-pfx', 'aria-hidden': 'true' }, opts.prefix) : null,
    icon(def.icon, def.spin ? 'spin' : ''), h('span', null, opts.text || def.zh));
    return c;
  }
  function autoDef(row, cov) {
    if (!row) return AUTO.not_analyzed;
    if (row.auto && AUTO[row.auto.status]) return AUTO[row.auto.status];
    if (row.auto) return { zh: row.auto.status_zh || row.auto.status, icon: 'help', tone: 'slate' };
    if (cov && cov.run && row.auto_outdated) return AUTO_STALE;
    return AUTO.not_analyzed;
  }
  function autoChip(row, cov, lg) {
    const d = autoDef(row, cov);
    return chip(d, { prefix: 'AI', lg, aria: '自動判定：' + d.zh });
  }
  function humanDef(row) {
    if (!row) return HUMAN.none;
    if (row.human_exception) return HUMAN.exception;
    if (row.human_confirmed) return HUMAN.confirmed;
    return HUMAN.none;
  }
  function humanChip(row, lg) {
    const d = humanDef(row);
    return chip(d, { human: true, lg, aria: '人工狀態：' + d.zh });
  }
  function reasonList(codes) {
    if (!codes || !codes.length) return h('span', { class: 'faint small' }, '—');
    return h('div', { class: 'chips' }, codes.map((c) => h('span', { class: 'reason', title: c }, icon('info'), REASON_ZH[c] || c)));
  }
  function capChip(cap) { return chip(CAP[cap] || CAP.auto, { aria: '判定方式：' + (CAP[cap] || CAP.auto).zh }); }

  function thumb(aid, t, label) {
    const img = h('img', { alt: label || ('影格 ' + fmtTime(t)), decoding: 'async' });
    const box = h('span', { class: 'thumb' }, img, h('span', { class: 't-time' }, fmtTime(t)));
    const fail = () => { img.remove(); box.classList.add('none'); box.prepend(h('span', null, '無法載入影格')); };
    frameUrl(aid, t).then((u) => { if (u) img.src = u; else fail(); }, fail);
    return box;
  }
  function noThumb(text) { return h('span', { class: 'thumb none' }, text || '沒有候選'); }

  function banner(kind, title, text, actions) {
    const ic = { warn: 'alert', info: 'info', error: 'alert' }[kind] || 'info';
    return h('div', { class: 'banner ' + kind, role: kind === 'error' ? 'alert' : 'status' },
      icon(ic), h('div', { class: 'grow' }, h('div', { class: 'b-title' }, title), text ? h('div', { class: 'b-text' }, text) : null),
      actions && actions.length ? h('div', { class: 'b-actions' }, actions) : null);
  }
  function btn(label, opts) {
    opts = opts || {};
    return h(opts.href ? 'a' : 'button', {
      class: 'btn ' + (opts.kind || '') + (opts.sm ? ' sm' : '') + (opts.block ? ' block' : ''),
      type: opts.href ? null : (opts.type || 'button'), href: opts.href, onclick: opts.onclick,
      disabled: opts.disabled, title: opts.title, 'aria-label': opts.aria, 'aria-pressed': opts.pressed,
    }, opts.icon ? icon(opts.icon) : null, label ? h('span', null, label) : null);
  }
  function empty(ic, title, text, actions) {
    return h('div', { class: 'empty' }, icon(ic), h('div', { class: 'e-title' }, title), text ? h('p', null, text) : null,
      actions ? h('div', { class: 'e-actions' }, actions) : null);
  }
  function panel(title, body, opts) {
    opts = opts || {};
    return h('section', { class: 'panel' + (opts.cls ? ' ' + opts.cls : ''), 'aria-label': typeof title === 'string' ? title : null },
      title ? h('div', { class: 'panel-head' }, h(opts.h || 'h2', null, opts.icon ? icon(opts.icon) : null, title), opts.right || null) : null,
      opts.raw ? body : h('div', { class: 'panel-body' }, body));
  }
  function pageHead(title, sub, actions) {
    return h('div', { class: 'page-head' },
      h('div', null, h('h1', null, title), sub ? h('div', { class: 'sub' }, sub) : null),
      actions && actions.length ? h('div', { class: 'actions' }, actions) : null);
  }
  function kvs(pairs) {
    return h('dl', { class: 'kvs' }, pairs.map(([k, v]) => [h('dt', null, k), h('dd', null, v == null || v === '' ? '—' : v)]));
  }
  function errorState(err, retry) {
    const next = NEXT_STEP[err.code] || (err.recoverable === false ? '請重新啟動 SceneGap 後再試。' : '請稍後再試；若持續發生，請到「裝置與診斷」匯出報告。');
    return h('div', null, banner('error', '無法載入：' + (err.message || '未知錯誤'), next + (err.request_id ? '（請求編號 ' + err.request_id + '）' : ''),
      retry ? [btn('重試', { icon: 'refresh', onclick: retry, sm: true })] : null));
  }

  // toasts
  function toast(o) {
    const box = $('#toasts');
    const ic = { error: 'alert', ok: 'checkc', info: 'info' }[o.kind] || 'info';
    const close = btn('', { kind: 'ghost', sm: true, icon: 'x', aria: '關閉通知' });
    const t = h('div', { class: 'toast ' + (o.kind || 'info'), role: o.kind === 'error' ? 'alert' : 'status' },
      icon(ic), h('div', { class: 'grow' }, h('div', { class: 't-title' }, o.title), o.text ? h('div', { class: 't-text' }, o.text) : null,
        o.meta ? h('div', { class: 't-text faint' }, o.meta) : null), close);
    close.classList.add('t-close');
    close.addEventListener('click', () => t.remove());
    box.append(t);
    if (o.kind !== 'error') setTimeout(() => t.remove(), 5000);
  }
  function showError(err, title) {
    if (!(err instanceof ApiError)) err = new ApiError(0, { code: 'CLIENT', message: String(err && err.message || err) });
    const next = NEXT_STEP[err.code] || (err.recoverable ? '請確認輸入後再試一次。' : '請重新啟動 SceneGap 後再試。');
    toast({ kind: 'error', title: title || '操作失敗', text: '下一步：' + next, meta: (err.message ? '詳細：' + err.message + ' · ' : '') + '代碼 ' + err.code + (err.request_id ? ' · 請求 ' + err.request_id : '') });
  }

  // ------------------------------------------------------------------ jobs
  function jobKey() { return 'sg.job.' + S.pid; }
  function restoreJob() {
    clearTimeout(S.jobTimer); S.job = null; S.jobId = null;
    if (!S.pid) return;
    const id = PREVIEW ? PREVIEW.active_job_id : store.get(jobKey(), null);
    if (id) { S.jobId = id; pollJob(); }
  }
  async function startAnalyze() {
    try {
      const r = await api('POST', '/projects/' + encodeURIComponent(S.pid) + '/analyze');
      S.jobId = r.job_id; S.job = { state: 'queued', stage: 'queued', done: 0, total: 0, failed: 0, backend: r.backend };
      if (!PREVIEW) store.set(jobKey(), r.job_id);
      toast({ kind: 'ok', title: '已開始分析', text: '後端 ' + (r.backend || '—') + ' · 模型指紋 ' + (r.model_fingerprint || '—') });
      notifyJob(); pollJob();
    } catch (e) { showError(e, '無法開始分析'); }
  }
  async function cancelJob() {
    if (!S.jobId) return;
    try { await api('POST', '/jobs/' + encodeURIComponent(S.jobId) + '/cancel'); toast({ kind: 'info', title: '已要求取消', text: '目前處理中的檔案完成後會停止。' }); pollJob(); }
    catch (e) { showError(e, '取消失敗'); }
  }
  function pollJob() {
    clearTimeout(S.jobTimer);
    const id = S.jobId;
    const tick = async () => {
      if (id !== S.jobId) return;
      try {
        const j = await api('GET', '/jobs/' + encodeURIComponent(id));
        if (id !== S.jobId) return;
        S.job = j; notifyJob();
        if (j.state === 'queued' || j.state === 'running') { S.jobTimer = setTimeout(tick, 1000); return; }
        if (!PREVIEW) store.del(jobKey());
        if (j.state === 'done') toast({ kind: 'ok', title: '分析完成', text: '覆蓋矩陣已更新。' });
        else if (j.state === 'failed') toast({ kind: 'error', title: '分析工作失敗', text: '下一步：檢查失敗的素材，或到「裝置與診斷」確認後端狀態後重新分析。' });
        if (['home', 'assets', 'coverage'].includes(S.route.name)) render();
      } catch (e) {
        if (e.code === 'NOT_FOUND') { S.jobId = null; S.job = null; if (!PREVIEW) store.del(jobKey()); notifyJob(); return; }
        S.jobTimer = setTimeout(tick, 2000);
      }
    };
    tick();
  }
  function notifyJob() { S.jobSubs.forEach((f) => f()); }
  function jobPanel(opts) {
    opts = opts || {};
    const el = h('div', { class: 'job', 'aria-live': 'polite' });
    const upd = () => {
      el.replaceChildren();
      const j = S.job;
      if (!j) {
        el.append(h('div', { class: 'job-head' }, h('span', { class: 'muted' }, '目前沒有進行中的分析工作。'),
          h('span', { class: 'grow' }),
          btn('開始分析', { kind: 'primary', icon: 'play', onclick: startAnalyze, disabled: opts.disabled })));
        return;
      }
      const st = JOB_ST[j.state] || JOB_ST.queued;
      const running = j.state === 'queued' || j.state === 'running';
      const stage = STAGE_ZH[j.stage] || j.stage || '';
      el.append(h('div', { class: 'job-head' }, chip(st, { aria: '工作狀態：' + st.zh }), h('span', { class: 'stage' }, stage),
        h('span', { class: 'grow' }),
        running ? btn('取消分析', { kind: 'danger', icon: 'stop', sm: true, onclick: cancelJob })
          : btn('重新分析', { kind: 'primary', icon: 'refresh', sm: true, onclick: startAnalyze })));
      const total = j.total || 0;
      if (running) {
        if (total > 0) {
          const pct = Math.min(100, (j.done || 0) / total * 100);
          el.append(h('div', { class: 'bar cyan', role: 'progressbar', 'aria-valuemin': 0, 'aria-valuemax': total, 'aria-valuenow': j.done || 0, 'aria-label': '已處理檔案數' },
            h('span', { style: 'width:' + pct.toFixed(1) + '%' })));
        } else {
          el.append(h('div', { class: 'bar indet', role: 'progressbar', 'aria-label': '進度未知' }, h('span')));
        }
      }
      el.append(h('div', { class: 'job-meta' },
        h('span', null, total > 0 ? '已處理 ' + (j.done || 0) + ' / ' + total + ' 支檔案' : (running ? '正在計算檔案數…' : '檔案數：—')),
        h('span', null, '失敗 ' + (j.failed || 0) + ' 支'),
        S.jobId ? h('span', { class: 'mono faint' }, '工作 ' + S.jobId) : null));
      if (j.state === 'failed') {
        el.append(h('div', { class: 'err-line' }, '原因：' + firstLine(j.error || '未提供')),
          h('div', { class: 'faint small' }, '下一步：檢查失敗的素材，或到「裝置與診斷」確認後端狀態後重新分析。'));
      }
    };
    S.jobSubs.add(upd); cleanup.push(() => S.jobSubs.delete(upd));
    upd();
    return el;
  }

  // ------------------------------------------------------------------ data helpers
  const P = () => '/projects/' + encodeURIComponent(S.pid);
  async function loadProject() {
    const p = await api('GET', P());
    S.project = p;
    return p;
  }
  function totalAssets(counts) { return counts ? Object.values(counts).reduce((a, b) => a + (b || 0), 0) : 0; }

  // ------------------------------------------------------------------ chrome: nav + topbar
  const NAV = [
    ['home', '專案首頁', 'home'], ['requirements', '需求編輯器', 'list'], ['assets', '素材庫', 'film'],
    ['coverage', '覆蓋矩陣', 'grid'], ['evidence', '證據檢視器', 'eye'], ['board', '複核／補拍板', 'board'], ['device', '裝置與診斷', 'cpu'],
  ];
  const NAME_ZH = Object.fromEntries(NAV.map((n) => [n[0], n[1]]));
  NAME_ZH.projects = '選擇專案';

  function renderNav() {
    const ul = $('#nav');
    ul.replaceChildren(...NAV.map(([key, label, ic], i) => {
      const needsProject = !['home', 'device'].includes(key);
      const disabled = needsProject && !S.pid;
      const cur = S.route.name === key || (key === 'home' && S.route.name === 'projects');
      return h('li', null, h('a', {
        href: '#/' + key, class: disabled ? 'disabled' : null, 'aria-current': cur ? 'page' : null,
        'aria-disabled': disabled ? 'true' : null, tabindex: disabled ? '-1' : null, title: label,
      }, icon(ic), h('span', { class: 'nav-label' }, label), h('span', { class: 'nav-step', 'aria-hidden': 'true' }, String(i + 1))));
    }));
    const foot = $('#sidebar-foot');
    foot.replaceChildren(
      h('span', { class: 'foot-text' }, 'SceneGap Edge ' + ((S.health && S.health.version) ? 'v' + S.health.version : '')),
      h('span', { class: 'foot-text' }, '本機服務 · 資料不離開這台電腦'));
  }

  function renderTop() {
    const left = $('#topbar-left');
    const name = S.project && S.project.project ? S.project.project.name : (S.pid ? S.pid : '尚未選擇專案');
    left.replaceChildren(h('div', { class: 'crumb' },
      h('span', { class: 'proj', title: name }, name), h('span', { class: 'sep', 'aria-hidden': 'true' }, '/'),
      h('span', { class: 'screen' }, NAME_ZH[S.route.name] || '')));
    const right = $('#topbar-right');
    right.replaceChildren();
    if (PREVIEW) right.append(chip({ zh: '預覽資料（非實測）', icon: 'beaker', tone: 'amber' }));
    const be = (S.device && S.device.active_backend) || (S.health && S.health.active_backend) || null;
    if (be) {
      const beDef = { zh: '後端 ' + (be === 'not loaded' ? '尚未載入' : be), icon: 'cpu', tone: be === 'not loaded' ? 'slate' : 'violet' };
      right.append(h('a', { href: '#/device', class: 'chip-link', title: '目前實際使用的推論後端', style: 'text-decoration:none' }, chip(beDef, { aria: '目前後端：' + be })));
    }
    const dev = (S.device && S.device.device) || (S.health && S.health.device);
    if (dev) {
      const d = dev.available ? { zh: 'UGen300 已連線', icon: 'plug', tone: 'green' } : { zh: 'UGen300 未連線', icon: 'plugoff', tone: 'orange' };
      right.append(h('a', { href: '#/device', title: dev.reason || '', style: 'text-decoration:none' }, chip(d, { outline: true })));
    }
    right.append(btn('', { kind: 'ghost', sm: true, icon: 'refresh', aria: '重新整理資料', title: '重新整理資料', onclick: () => { refreshStatus(); render(); } }));
  }

  async function refreshStatus() {
    const [hl, dv] = await Promise.allSettled([api('GET', '/health'), api('GET', '/device/status')]);
    if (hl.status === 'fulfilled') S.health = hl.value;
    if (dv.status === 'fulfilled') S.device = dv.value;
    renderTop(); renderNav();
  }

  // ------------------------------------------------------------------ routing
  function parseRoute() {
    const raw = (location.hash || '#/home').replace(/^#\/?/, '');
    const [path] = raw.split('?');
    const parts = path.split('/').filter(Boolean).map(decodeURIComponent);
    const name = parts[0] || 'home';
    return { name: SCREENS[name] ? name : 'home', params: parts.slice(1) };
  }
  function go(hash) { if (location.hash === hash) render(); else location.hash = hash; }

  async function render() {
    cleanup.forEach((f) => { try { f(); } catch (e) { /* ignore */ } });
    cleanup = [];
    const prev = S.route.name;
    S.route = parseRoute();
    if (!S.pid && !['home', 'projects', 'device'].includes(S.route.name)) { location.replace('#/projects'); return; }
    if (S.route.name === 'home' && !S.pid) S.route = { name: 'projects', params: [] };
    renderNav(); renderTop();
    const seq = ++renderSeq;
    const main = $('#main');
    if (prev !== S.route.name) main.replaceChildren(h('div', { class: 'loading', role: 'status' }, '載入中…'));
    let node;
    try {
      if (S.pid && !S.project) { try { await loadProject(); } catch (e) { if (e.code === 'NOT_FOUND') { setProject(null); location.replace('#/projects'); toast({ kind: 'error', title: '找不到這個專案', text: '下一步：建立新專案，或輸入正確的專案 ID。' }); return; } throw e; } }
      node = await SCREENS[S.route.name](S.route.params);
    } catch (e) {
      node = errorState(e instanceof ApiError ? e : new ApiError(0, { code: 'CLIENT', message: String(e && e.message || e) }), render);
      if (!(e instanceof ApiError)) console.error(e);
    }
    if (seq !== renderSeq) return;
    main.replaceChildren(node);
    renderTop();
    document.title = (NAME_ZH[S.route.name] || 'SceneGap') + ' · SceneGap Edge';
    if (prev !== S.route.name) { main.scrollTop = 0; main.focus({ preventScroll: true }); }
  }

  // ================================================================== SCREENS
  const SCREENS = {};

  // ---------- project picker / creator
  SCREENS.projects = async function () {
    const f = { name: '', purpose: '', aspect: '16:9', target: '' };
    const err = h('div', { class: 'err-line', role: 'alert' });
    const create = h('form', { class: 'stack', onsubmit: async (ev) => {
      ev.preventDefault(); err.textContent = '';
      if (!f.name.trim()) { err.textContent = '請填寫專案名稱。'; return; }
      const t = f.target === '' ? null : Number(f.target);
      if (t != null && !(t > 0)) { err.textContent = '目標長度需為正數（秒）。'; return; }
      try {
        const r = await api('POST', '/projects', { name: f.name.trim(), purpose: f.purpose.trim(), aspect: f.aspect, target_len_s: t });
        setProject(r.project_id, f.name.trim());
        toast({ kind: 'ok', title: '專案已建立', text: '下一步：建立需求，並授權素材資料夾。' });
        go('#/home');
      } catch (e) { showError(e, '無法建立專案'); }
    } },
    h('div', { class: 'field' }, h('label', { for: 'pj-name' }, '專案名稱（必填）'), h('input', { id: 'pj-name', class: 'input', required: true, maxlength: 120, oninput: (e) => { f.name = e.target.value; } })),
    h('div', { class: 'field' }, h('label', { for: 'pj-purpose' }, '用途／交付說明'), h('input', { id: 'pj-purpose', class: 'input', placeholder: '例：品牌形象 60 秒短片', oninput: (e) => { f.purpose = e.target.value; } })),
    h('div', { class: 'grid-2' },
      h('div', { class: 'field' }, h('label', { for: 'pj-aspect' }, '畫面比例'),
        h('select', { id: 'pj-aspect', class: 'input', onchange: (e) => { f.aspect = e.target.value; } },
          ['16:9', '9:16', '1:1', '4:5', '2.39:1'].map((a) => h('option', { value: a }, a)))),
      h('div', { class: 'field' }, h('label', { for: 'pj-len' }, '目標長度（秒）'), h('input', { id: 'pj-len', class: 'input', type: 'number', min: '1', step: '1', inputmode: 'numeric', oninput: (e) => { f.target = e.target.value; } }))),
    err,
    h('div', { class: 'row' }, h('span', { class: 'grow' }), btn('建立專案', { kind: 'primary', icon: 'plus', type: 'submit' })));

    const openErr = h('div', { class: 'err-line', role: 'alert' });
    let openId = '';
    const open = h('form', { class: 'stack', onsubmit: async (ev) => {
      ev.preventDefault(); openErr.textContent = '';
      const id = openId.trim();
      if (!id) { openErr.textContent = '請輸入專案 ID。'; return; }
      try {
        const p = await api('GET', '/projects/' + encodeURIComponent(id));
        setProject(id, p.project && p.project.name); S.project = p; go('#/home');
      } catch (e) { if (e.code === 'NOT_FOUND') openErr.textContent = '找不到這個專案 ID。'; else showError(e, '無法開啟專案'); }
    } },
    h('div', { class: 'field' }, h('label', { for: 'pj-id' }, '專案 ID'), h('input', { id: 'pj-id', class: 'input mono', placeholder: 'p_…', oninput: (e) => { openId = e.target.value; } }),
      h('span', { class: 'hint' }, '本機服務目前沒有「列出所有專案」的 API，因此只顯示這台瀏覽器曾開啟過的專案。')),
    openErr, h('div', { class: 'row' }, h('span', { class: 'grow' }), btn('開啟', { icon: 'open', type: 'submit' })));

    const recent = store.get('sg.recent', []);
    const recentList = recent.length
      ? h('div', { class: 'roots' }, recent.map((r) => h('div', { class: 'root-item' }, icon('film'),
        h('div', { class: 'grow' }, h('div', null, r.name || r.id), h('div', { class: 'mono faint' }, r.id)),
        btn('開啟', { sm: true, onclick: () => { setProject(r.id, r.name); go('#/home'); } }))))
      : h('p', { class: 'faint' }, '還沒有開啟過的專案。');

    return h('div', null,
      pageHead('選擇或建立專案', '專案包含一組需求（腳本鏡頭清單）與授權的素材資料夾。'),
      h('div', { class: 'grid-2' }, panel('建立新專案', create, { icon: 'plus' }),
        h('div', null, panel('開啟既有專案', open, { icon: 'open' }), panel('最近開啟', recentList, { icon: 'clock' }))));
  };

  // ---------- 1 home
  SCREENS.home = async function () {
    const [proj, cov] = await Promise.all([loadProject(), api('GET', P() + '/coverage')]);
    const p = proj.project || {};
    const counts = proj.assets || {};
    const total = totalAssets(counts);
    const c = cov && cov.coverage;
    const be = (S.device && S.device.active_backend) || (S.health && S.health.active_backend) || 'not loaded';
    const dev = (S.device && S.device.device) || (S.health && S.health.device);
    const out = [];
    out.push(pageHead(p.name || S.pid,
      [p.purpose, p.aspect, p.target_len_s ? '目標 ' + p.target_len_s + ' 秒' : null].filter(Boolean).join(' · ') || null,
      [btn('切換專案', { icon: 'open', href: '#/projects' }), btn('開啟覆蓋矩陣', { kind: 'primary', icon: 'grid', href: '#/coverage' })]));

    if (dev && !dev.available) {
      out.push(banner('info', 'UGen300 未連線', '目前以明示的 CPU 參考後端（' + (be === 'not loaded' ? '尚未載入，首次分析時載入' : be) + '）執行分析；結果與報告都會標示這個後端，不代表 NPU 效能。',
        [btn('裝置與診斷', { sm: true, href: '#/device', icon: 'cpu' })]));
    }
    if (cov && cov.run && cov.outdated) {
      out.push(banner('warn', '需求或素材已變更，請重新分析', 'AI 候選覆蓋在重新分析前顯示為 N/A；人工確認仍有效。',
        [btn('重新分析', { sm: true, kind: 'primary', icon: 'refresh', onclick: startAnalyze })]));
    }
    if (counts.failed) {
      out.push(banner('warn', '這 ' + counts.failed + ' 支影片尚未完成解析；目前結果只涵蓋其餘素材。', '失敗的檔案列在素材庫，原因不會被隱藏。',
        [btn('查看失敗素材', { sm: true, href: '#/assets/failed' })]));
    }

    // KPI cards
    const kpi = (cls, ic, label, val, ratio, foot, barCls) => {
      const na = val == null;
      return h('div', { class: 'panel kpi ' + cls },
        h('div', { class: 'k-label' }, icon(ic), label),
        h('div', { class: 'k-value' + (na ? ' na' : '') }, na ? 'N/A' : val),
        ratio === undefined ? null : h('div', { class: 'bar ' + (na ? 'na' : barCls || ''), role: 'img', 'aria-label': na ? label + '：無法計算' : label + '：' + val },
          na ? null : h('span', { style: 'width:' + Math.max(0, Math.min(100, ratio * 100)).toFixed(1) + '%' })),
        h('div', { class: 'k-foot' }, foot));
    };
    const noRun = !cov || !cov.run || !c;
    const denom = c && c.denominator_weight != null ? '分母：已確認的必要需求權重 ' + c.denominator_weight : '';
    out.push(h('div', { class: 'kpis' },
      kpi('human', 'checkc', '人工確認覆蓋', c ? fmtPct(c.human_confirmed) : null, c ? (c.human_confirmed == null ? null : c.human_confirmed) : null,
        noRun ? '尚無分析快照' : (c.human_confirmed == null ? '尚無已確認的必要需求' : denom), 'green'),
      kpi('ai', 'sparkle', 'AI 候選覆蓋', c ? fmtPct(c.ai_candidate) : null, c ? c.ai_candidate : null,
        noRun ? '尚無分析快照' : (c.ai_candidate == null ? (cov.outdated ? '結果已過期，重新分析後才會顯示' : '無法計算') : '候選仍需人工確認'), ''),
      kpi('prog', 'activity', '分析進度', c ? fmtPct(c.analysis_progress) : null, c ? c.analysis_progress : null,
        noRun ? '尚無分析快照' : (c.analysis_progress == null ? '範圍內沒有可分析的素材' : '已分析素材佔納入範圍的比例'), 'cyan'),
      kpi('unk', 'help', '未能自動判定', c && c.unknown_count != null ? c.unknown_count + ' 項' : null, undefined,
        noRun ? '尚無分析快照' : '需人工確認或含不支援條件的需求')));

    // asset summary + job
    const statline = h('div', { class: 'statline' }, Object.keys(ASSET_ST).map((k) =>
      h('a', { class: 'stat', href: '#/assets/' + k, style: 'text-decoration:none;color:inherit' }, chip(ASSET_ST[k]), h('span', { class: 's-n' }, String(counts[k] || 0)))));
    const assetsBody = total === 0
      ? empty('film', '尚未加入素材，現在不能判斷是否缺鏡頭。', '先授權素材資料夾並匯入影片，再開始分析。', [btn('前往素材庫', { kind: 'primary', icon: 'folder', href: '#/assets' })])
      : h('div', { class: 'stack' }, statline, h('div', { class: 'panel', style: 'box-shadow:none' }, jobPanel({ disabled: total === 0 })));
    const runInfo = cov && cov.run
      ? kvs([['執行編號', h('span', { class: 'mono' }, cov.run.run_id)], ['時間', fmtDate(cov.run.created_at)], ['後端', cov.run.backend],
        ['模型指紋', h('span', { class: 'mono' }, cov.run.model_fingerprint)], ['設定雜湊', h('span', { class: 'mono' }, cov.run.config_hash)],
        ['狀態', cov.outdated ? chip(AUTO_STALE) : chip({ zh: '與目前需求、素材一致', icon: 'check', tone: 'green' })]])
      : h('p', { class: 'muted' }, '尚未有分析結果。加入素材與需求後按「開始分析」。');
    out.push(h('div', { class: 'grid-2' },
      panel('素材（共 ' + total + ' 支）', assetsBody, { icon: 'film', right: btn('素材庫', { sm: true, kind: 'ghost', href: '#/assets', icon: 'right' }) }),
      panel('最近一次分析', runInfo, { icon: 'activity' })));
    return h('div', null, out);
  };

  // ---------- 2 requirements editor
  function blankReq(list) {
    let n = list.length + 1, id;
    const ids = new Set(list.map((r) => r.requirement_id));
    do { id = 'R' + pad(n++, 2); } while (ids.has(id));
    return { requirement_id: id, revision: 0, source_text: '', query_en: '', required: true, weight: 1, min_duration_ms: 0, min_takes: 1, confirmed: false, excluded_reason: null, constraints: [] };
  }
  SCREENS.requirements = async function (params) {
    const list = await api('GET', P() + '/requirements');
    const sel = params[0] || (list[0] && list[0].requirement_id) || 'new';
    const isNew = sel === 'new' || !list.find((r) => r.requirement_id === sel);
    const orig = isNew ? blankReq(list) : list.find((r) => r.requirement_id === sel);
    let dirty = false;
    const guard = (ev) => { if (dirty && !confirm('有未儲存的變更，確定要離開？')) { ev.preventDefault(); return false; } return true; };

    const listEl = h('ul', { class: 'req-list', 'aria-label': '需求清單' }, list.map((r) => h('li', null, h('button', {
      type: 'button', 'aria-current': r.requirement_id === sel && !isNew ? 'true' : null,
      onclick: (ev) => { if (guard(ev)) go('#/requirements/' + encodeURIComponent(r.requirement_id)); },
    }, h('span', { class: 'rl-id' }, r.requirement_id), h('span', { class: 'rl-text', title: r.source_text }, r.source_text || '（未填寫）'),
    h('span', { class: 'rl-meta' },
      r.confirmed ? chip({ zh: '已確認', icon: 'check', tone: 'green' }) : chip(AUTO.draft),
      r.excluded_reason ? chip({ zh: '已排除', icon: 'ban', tone: 'slate' }) : null,
      !r.required ? chip({ zh: '非必要', icon: 'circle', tone: 'slate' }) : null,
      h('span', { class: 'faint small' }, '第 ' + r.revision + ' 版'))))));
    const left = panel('需求（' + list.length + '）', h('div', null,
      list.length ? listEl : h('p', { class: 'faint', style: 'padding:12px' }, '還沒有需求。'),
      h('div', { style: 'padding:10px' }, btn('新增需求', { icon: 'plus', block: true, onclick: (ev) => { if (guard(ev)) go('#/requirements/new'); } }))),
    { icon: 'list', raw: true });

    return h('div', null,
      pageHead('需求編輯器', '中文原文與確認過的英文檢索字並排；每次修改會產生新版本，舊的人工決策不會套到新版本。'),
      h('div', { class: 'split' }, left, reqForm(orig, isNew, list, () => { dirty = true; })));
  };

  function reqForm(orig, isNew, list, markDirty) {
    const d = JSON.parse(JSON.stringify(orig));
    const paramsText = d.constraints.map((c) => JSON.stringify(c.params || {}));
    const errs = {};
    const fieldErr = (k) => (errs[k] = h('div', { class: 'err-line', role: 'alert' }));
    const set = (k, v) => { d[k] = v; markDirty(); };
    const formMsg = h('div');

    const consWrap = h('div', { class: 'cons-list' });
    const drawCons = () => {
      consWrap.replaceChildren();
      if (!d.constraints.length) consWrap.append(h('p', { class: 'faint small' }, '沒有額外條件。語意內容以英文檢索字比對；可加入時長、take 數、構圖等條件。'));
      d.constraints.forEach((c, i) => {
        const badgeBox = h('div', { class: 'cons-badges' });
        const drawBadges = () => badgeBox.replaceChildren(capChip(c.capability || 'auto'), c.hard ? chip({ zh: '硬性', icon: 'alert', tone: 'violet' }) : chip({ zh: '參考', icon: 'circle', tone: 'slate' }));
        drawBadges();
        const kinds = Object.keys(KIND_ZH).includes(c.kind) ? Object.keys(KIND_ZH) : [c.kind].concat(Object.keys(KIND_ZH));
        const pid = 'cp-' + i;
        const perr = h('div', { class: 'err-line', role: 'alert' });
        errs['params' + i] = perr;
        consWrap.append(h('div', { class: 'cons', role: 'group', 'aria-label': '條件 ' + (i + 1) },
          h('div', { class: 'field' }, h('label', { for: 'ck-' + i }, '條件類型'),
            h('select', { id: 'ck-' + i, class: 'input', onchange: (e) => { c.kind = e.target.value; markDirty(); } },
              kinds.map((k) => h('option', { value: k, selected: k === c.kind }, (KIND_ZH[k] || k) + '（' + k + '）')))),
          h('div', { class: 'field' }, h('label', { for: 'cc-' + i }, '判定方式'),
            h('select', { id: 'cc-' + i, class: 'input', onchange: (e) => { c.capability = e.target.value; markDirty(); drawBadges(); } },
              Object.keys(CAP).map((k) => h('option', { value: k, selected: k === (c.capability || 'auto') }, CAP[k].zh)))),
          h('div', { class: 'field' }, h('label', { for: pid }, '參數（JSON）與備註'),
            h('textarea', { id: pid, class: 'input mono', rows: 1, spellcheck: 'false', value: paramsText[i], oninput: (e) => { paramsText[i] = e.target.value; markDirty(); } }),
            perr,
            h('input', { class: 'input', 'aria-label': '條件備註', placeholder: '備註（例：需人工看字卡是否清楚）', value: c.note || '', oninput: (e) => { c.note = e.target.value; markDirty(); } })),
          h('div', { class: 'cons-side' }, badgeBox,
            h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: c.hard !== false, onchange: (e) => { c.hard = e.target.checked; markDirty(); drawBadges(); } }), '硬性條件'),
            btn('移除', { sm: true, kind: 'ghost', icon: 'trash', aria: '移除條件 ' + (i + 1), onclick: () => { d.constraints.splice(i, 1); paramsText.splice(i, 1); markDirty(); drawCons(); } }))));
      });
    };
    drawCons();

    // trial search
    const searchOut = h('div');
    const trySearch = async () => {
      searchOut.replaceChildren(h('p', { class: 'faint small', role: 'status' }, '搜尋中…'));
      try {
        const r = await api('POST', P() + '/search', { query_en: d.query_en, top_k: 6 });
        const res = r.results || [];
        searchOut.replaceChildren(
          h('p', { class: 'faint small', style: 'margin-top:10px' }, '排序分數（非機率）僅用來排序；是否高於門檻由校準值決定。' + (r.note ? '' : '')),
          res.length ? h('div', { class: 'search-results' }, res.map((x) => h('div', { class: 'sr' },
            thumb(x.asset_id, x.best_ms), h('div', { class: 'row', style: 'justify-content:space-between' },
              h('span', { class: 'mono small' }, fmtTime(x.shot_start_ms) + '–' + fmtTime(x.shot_end_ms)),
              h('span', { class: 'mono small', title: '排序分數（非機率）' }, Number(x.ranking_score).toFixed(3))),
            x.above_threshold ? chip({ zh: '高於門檻', icon: 'check', tone: 'violet' }) : chip({ zh: '低於門檻', icon: 'dashed', tone: 'slate' }))))
            : h('p', { class: 'muted' }, '已分析範圍內沒有結果。'));
      } catch (e) { searchOut.replaceChildren(); showError(e, '搜尋失敗'); }
    };

    const save = async () => {
      Object.values(errs).forEach((e) => { e.textContent = ''; });
      formMsg.replaceChildren();
      let bad = false;
      if (isNew && !/^[A-Za-z0-9_-]{1,32}$/.test(d.requirement_id || '')) { errs.rid.textContent = 'ID 只能使用英數字、底線或連字號。'; bad = true; }
      if (isNew && list.some((r) => r.requirement_id === d.requirement_id)) { errs.rid.textContent = '這個 ID 已存在。'; bad = true; }
      if (!String(d.source_text || '').trim()) { errs.src.textContent = '請填寫中文原文。'; bad = true; }
      if (!String(d.query_en || '').trim()) { errs.q.textContent = '請填寫確認過的英文檢索字（必填）。'; bad = true; }
      if (!(d.weight > 0)) { errs.w.textContent = '權重需大於 0。'; bad = true; }
      const cons = [];
      d.constraints.forEach((c, i) => {
        let params;
        try { params = paramsText[i].trim() ? JSON.parse(paramsText[i]) : {}; if (typeof params !== 'object' || Array.isArray(params) || params === null) throw new Error('obj'); }
        catch (e) { errs['params' + i].textContent = '參數必須是 JSON 物件，例如 {"min_s": 3}'; bad = true; return; }
        cons.push({ kind: c.kind, capability: c.capability || 'auto', params, hard: c.hard !== false, note: c.note || '' });
      });
      if (bad) { formMsg.replaceChildren(banner('error', '有欄位需要修正', '請依欄位下方的提示修改後再儲存。')); return; }
      const data = {
        requirement_id: d.requirement_id, source_text: d.source_text.trim(), query_en: d.query_en.trim(), required: !!d.required,
        weight: Number(d.weight), min_duration_ms: Math.round(Number(d.min_duration_ms) || 0), min_takes: Math.max(1, parseInt(d.min_takes, 10) || 1),
        confirmed: !!d.confirmed, excluded_reason: d.excluded_reason && String(d.excluded_reason).trim() ? String(d.excluded_reason).trim() : null, constraints: cons,
      };
      try {
        const saved = isNew
          ? await api('POST', P() + '/requirements', { data })
          : await api('PATCH', P() + '/requirements/' + encodeURIComponent(d.requirement_id), { data, expected_revision: orig.revision });
        toast({ kind: 'ok', title: '已儲存 ' + data.requirement_id, text: saved && saved.revision ? '目前為第 ' + saved.revision + ' 版。覆蓋結果需重新分析才會更新。' : null });
        go('#/requirements/' + encodeURIComponent(data.requirement_id));
      } catch (e) {
        if (e.code === 'STALE_REVISION') {
          formMsg.replaceChildren(banner('error', '需求已被修改，請重新載入', '另一個視窗或成員已更新這筆需求。重新載入會捨棄你在此畫面的修改。',
            [btn('重新載入', { sm: true, icon: 'refresh', onclick: () => render() })]));
        } else showError(e, '儲存失敗');
      }
    };

    const num = (id, label, val, onv, attrs, hint, ek) => h('div', { class: 'field' }, h('label', { for: id }, label),
      h('input', Object.assign({ id, class: 'input num', type: 'number', value: val, oninput: (e) => onv(e.target.value) }, attrs)),
      hint ? h('span', { class: 'hint' }, hint) : null, ek ? fieldErr(ek) : null);

    const body = h('div', { class: 'stack' },
      formMsg,
      h('div', { class: 'row' },
        h('div', { class: 'field', style: 'width:160px' }, h('label', { for: 'rq-id' }, '需求 ID'),
          h('input', { id: 'rq-id', class: 'input mono', value: d.requirement_id, readonly: !isNew, oninput: (e) => set('requirement_id', e.target.value.trim()) }), fieldErr('rid')),
        h('div', { class: 'grow' }),
        h('label', { class: 'switch' }, h('input', { type: 'checkbox', role: 'switch', checked: !!d.confirmed, onchange: (e) => set('confirmed', e.target.checked) }),
          h('span', null, h('strong', null, '已確認需求'), h('span', { class: 'faint small', style: 'display:block' }, '確認後才列入覆蓋率分母')))),
      h('div', { class: 'bilingual' },
        h('div', { class: 'field' }, h('label', { for: 'rq-src' }, '中文原文', h('span', { class: 'lang' }, 'ZH')),
          h('textarea', { id: 'rq-src', class: 'input', rows: 3, value: d.source_text, oninput: (e) => set('source_text', e.target.value) }),
          h('span', { class: 'hint' }, '腳本或客戶原話，系統不會改寫。'), fieldErr('src')),
        h('div', { class: 'field' }, h('label', { for: 'rq-q' }, '確認過的英文檢索字', h('span', { class: 'lang' }, 'EN')),
          h('textarea', { id: 'rq-q', class: 'input', rows: 3, lang: 'en', spellcheck: 'false', value: d.query_en, oninput: (e) => set('query_en', e.target.value) }),
          h('div', { class: 'row', style: 'justify-content:space-between' }, h('span', { class: 'hint' }, '模型只看這段英文；請由人確認語意與原文一致。'),
            btn('試搜尋', { sm: true, icon: 'search', onclick: () => { if (String(d.query_en || '').trim()) trySearch(); } })), fieldErr('q'))),
      searchOut,
      h('div', { class: 'form-grid' },
        h('div', { class: 'field' }, h('span', { class: 'label' }, '必要性'),
          h('label', { class: 'check', style: 'height:34px' }, h('input', { type: 'checkbox', checked: !!d.required, onchange: (e) => set('required', e.target.checked) }), '必要鏡頭')),
        num('rq-w', '權重', d.weight, (v) => set('weight', Number(v)), { min: '0.1', step: '0.1' }, null, 'w'),
        num('rq-dur', '最短連續時長（秒）', (d.min_duration_ms || 0) / 1000, (v) => set('min_duration_ms', Math.round(Number(v) * 1000)), { min: '0', step: '0.1' }),
        num('rq-takes', '最少獨立 take 數', d.min_takes, (v) => set('min_takes', v), { min: '1', step: '1' })),
      h('div', { class: 'field' }, h('label', { for: 'rq-ex' }, '排除理由'),
        h('input', { id: 'rq-ex', class: 'input', placeholder: '留空表示納入；填寫後此需求不列入覆蓋率', value: d.excluded_reason || '', oninput: (e) => set('excluded_reason', e.target.value) })),
      h('div', null, h('div', { class: 'row', style: 'justify-content:space-between;margin-bottom:10px' },
        h('h3', null, '條件（' + d.constraints.length + '）'),
        btn('新增條件', { sm: true, icon: 'plus', onclick: () => { d.constraints.push({ kind: 'duration', capability: 'auto', params: {}, hard: true, note: '' }); paramsText.push('{}'); markDirty(); drawCons(); } })),
      h('div', { class: 'row small faint', style: 'margin-bottom:10px;gap:8px' }, '判定方式：', capChip('auto'), '由模型或規則判定', capChip('manual'), '需人工看過', capChip('unsupported'), '此版本無法判定'),
      consWrap));

    const head = isNew ? '新增需求' : orig.requirement_id + ' · 第 ' + orig.revision + ' 版';
    return h('section', { class: 'panel', 'aria-label': head },
      h('div', { class: 'panel-head' }, h('h2', null, icon(isNew ? 'plus' : 'pencil'), head),
        !isNew ? h('a', { class: 'btn sm ghost', href: '#/evidence/' + encodeURIComponent(orig.requirement_id) }, icon('eye'), h('span', null, '開啟證據')) : null),
      h('div', { class: 'panel-body' }, body),
      h('div', { class: 'form-foot' },
        h('span', { class: 'faint small grow' }, isNew ? '新需求會建立第 1 版。' : '儲存時會送出目前版本（第 ' + orig.revision + ' 版）；若已被他人修改會提示重新載入。'),
        btn('還原', { kind: 'ghost', onclick: () => render() }), btn('儲存', { kind: 'primary', icon: 'check', onclick: save })));
  }

  // ---------- 3 assets
  SCREENS.assets = async function (params) {
    const [proj, assets] = await Promise.all([loadProject(), api('GET', P() + '/assets')]);
    const counts = proj.assets || {};
    const filter = params[0] && ASSET_ST[params[0]] ? params[0] : 'all';
    const out = [pageHead('素材庫', '只讀取你授權的資料夾；檔案不會被移動或修改。')];

    // roots
    let newPath = '';
    const rootErr = h('div', { class: 'err-line', role: 'alert' });
    const importOut = h('div');
    const doImport = async (root) => {
      importOut.replaceChildren(h('p', { class: 'faint small', role: 'status' }, '匯入中…（正在計算雜湊並讀取影片資訊）'));
      try {
        const r = await api('POST', P() + '/assets/import', { root_id: root.id, rel_paths: null });
        importOut.replaceChildren(importResult(r));
        const fresh = await api('GET', P() + '/assets');
        tableBox.replaceChildren(assetTable(fresh, filter));
        await loadProject();
      } catch (e) { importOut.replaceChildren(); showError(e, '匯入失敗'); }
    };
    const roots = proj.roots || [];
    const rootForm = h('form', { class: 'row', style: 'margin-top:12px', onsubmit: async (ev) => {
      ev.preventDefault(); rootErr.textContent = '';
      const p = newPath.trim();
      if (!p) { rootErr.textContent = '請輸入資料夾的絕對路徑。'; return; }
      if (!/^([A-Za-z]:[\\/]|\\\\|\/)/.test(p)) { rootErr.textContent = '請輸入絕對路徑，例如 D:\\Footage\\Day1。'; return; }
      try { await api('POST', P() + '/roots', { path: p }); toast({ kind: 'ok', title: '已授權資料夾', text: p }); render(); }
      catch (e) { if (NEXT_STEP[e.code]) rootErr.textContent = NEXT_STEP[e.code]; showError(e, '無法授權資料夾'); }
    } },
    h('label', { class: 'sr-only', for: 'root-path' }, '資料夾絕對路徑'),
    h('input', { id: 'root-path', class: 'input mono grow', style: 'flex:1 1 320px', placeholder: 'D:\\Footage\\Day1', oninput: (e) => { newPath = e.target.value; } }),
    btn('授權資料夾', { kind: roots.length ? '' : 'primary', icon: 'folder', type: 'submit' }));
    const rootsBody = h('div', null,
      roots.length ? h('div', { class: 'roots' }, roots.map((r) => h('div', { class: 'root-item' }, icon('open'),
        h('span', { class: 'path', title: r.path }, r.path),
        btn('匯入整個資料夾', { sm: true, icon: 'download', onclick: () => doImport(r) }))))
        : h('p', { class: 'muted' }, '尚未授權任何資料夾。'),
      rootForm, rootErr, h('p', { class: 'hint faint small', style: 'margin-top:6px' }, '請輸入絕對路徑。SceneGap 只會讀取已授權資料夾內的影片。'),
      importOut);

    // analyze
    const analyzePanel = panel('分析', jobPanel({ disabled: !assets.length }), { icon: 'activity', raw: true });

    out.push(h('div', { class: 'grid-2' }, panel('授權素材資料夾', rootsBody, { icon: 'folder' }), analyzePanel));

    if (counts.failed) out.push(banner('warn', '這 ' + counts.failed + ' 支影片尚未完成解析；目前結果只涵蓋其餘素材。', '下表以紅色標示失敗的檔案與原因。修正後可重新匯入或重新分析。'));

    const tableBox = h('div');
    tableBox.append(assets.length ? assetTable(assets, filter) : empty('film', '尚未加入素材，現在不能判斷是否缺鏡頭。', '授權資料夾後按「匯入整個資料夾」。'));
    out.push(panel('素材（' + assets.length + '）', tableBox, { icon: 'film', raw: true }));
    return h('div', { class: 'stack' }, out);
  };

  function importResult(r) {
    const acc = r.accepted || [], rej = r.rejected || [];
    return h('div', { class: 'import-result' },
      h('div', null, h('h3', { style: 'margin-bottom:8px' }, '已接受 ', h('span', { class: 'faint num' }, '(' + acc.length + ')')),
        acc.length ? h('ul', null, acc.map((a) => h('li', null, h('span', { class: 'path' }, a.path),
          h('div', { class: 'row', style: 'gap:6px' }, chip(ASSET_ST[a.status] || ASSET_ST.pending),
            a.duplicate_of ? chip({ zh: '與 ' + a.duplicate_of + ' 內容相同', icon: 'info', tone: 'slate' }) : null,
            a.error_code ? h('span', { class: 'err-line' }, a.error_code) : null))))
          : h('p', { class: 'faint small' }, '沒有新檔案。')),
      h('div', null, h('h3', { style: 'margin-bottom:8px' }, '已拒絕 ', h('span', { class: 'faint num' }, '(' + rej.length + ')')),
        rej.length ? h('ul', null, rej.map((a) => h('li', null, h('span', { class: 'path' }, a.path),
          h('span', { class: 'err-line' }, (a.code || '') + (a.message ? '：' + a.message : '')))))
          : h('p', { class: 'faint small' }, '沒有被拒絕的檔案。')));
  }

  function assetTable(assets, filter) {
    const counts = {};
    assets.forEach((a) => { counts[a.status] = (counts[a.status] || 0) + 1; });
    const wrap = h('div');
    const draw = (f) => {
      const rows = f === 'all' ? assets : assets.filter((a) => a.status === f);
      const seg = h('div', { class: 'seg', role: 'group', 'aria-label': '依狀態篩選' },
        h('button', { type: 'button', 'aria-pressed': String(f === 'all'), onclick: () => draw('all') }, '全部 ', h('span', { class: 'count' }, String(assets.length))),
        Object.keys(ASSET_ST).filter((k) => counts[k]).map((k) => h('button', { type: 'button', 'aria-pressed': String(f === k), onclick: () => draw(k) },
          icon(ASSET_ST[k].icon), ASSET_ST[k].zh, h('span', { class: 'count' }, String(counts[k])))));
      const tbl = h('table', { class: 'tbl' },
        h('thead', null, h('tr', null, ['檔案', '狀態', '編碼', '解析度', '影格率', '長度', '警示／錯誤'].map((t) => h('th', { scope: 'col' }, t)))),
        h('tbody', null, rows.map((a) => {
          const pr = a.probe || {};
          const warns = [].concat(pr.warnings || []);
          const isFail = a.status === 'failed' || a.status === 'missing' || pr.supported === false;
          return h('tr', { class: isFail ? 'row-fail' : (warns.length || pr.vfr_suspected ? 'row-warn' : null) },
            h('td', null, h('div', { class: 'asset-name' }, (a.locations && a.locations[0]) || a.asset_id),
              a.locations && a.locations.length > 1 ? h('div', { class: 'faint small' }, '另有 ' + (a.locations.length - 1) + ' 個位置') : null,
              h('div', { class: 'faint small mono' }, a.asset_id + (a.capture_id ? ' · take ' + a.capture_id : ''))),
            h('td', null, chip(ASSET_ST[a.status] || { zh: a.status, icon: 'help', tone: 'slate' })),
            h('td', null, pr.codec || '—'),
            h('td', { class: 'num' }, pr.width ? pr.width + '×' + pr.height + (pr.rotation ? ' · 旋轉 ' + pr.rotation + '°' : '') : '—'),
            h('td', { class: 'num' }, pr.avg_fps ? Number(pr.avg_fps).toFixed(2) + ' fps' : '—',
              pr.vfr_suspected ? h('div', null, chip({ zh: '疑似可變影格率', icon: 'alert', tone: 'amber' })) : null),
            h('td', { class: 'num mono' }, fmtTime(a.duration_ms != null ? a.duration_ms : pr.duration_ms)),
            h('td', null,
              a.error_code || a.error_msg ? h('div', { class: 'err-line' }, [a.error_code, a.error_msg].filter(Boolean).join('：')) : null,
              pr.supported === false ? h('div', { class: 'err-line' }, '不支援：' + (pr.unsupported_reason || '未提供原因')) : null,
              warns.map((w) => h('div', { class: 'warn-line', title: w }, '⚠ ' + (WARN_ZH[w] || w))),
              !a.error_code && !a.error_msg && pr.supported !== false && !warns.length ? h('span', { class: 'faint' }, '—') : null));
        })));
      wrap.replaceChildren(h('div', { style: 'padding:12px 16px;border-bottom:1px solid var(--line-soft)' }, seg),
        rows.length ? h('div', { class: 'table-wrap' }, tbl) : h('p', { class: 'faint', style: 'padding:16px' }, '沒有符合篩選的素材。'));
    };
    draw(filter || 'all');
    return wrap;
  }

  // ---------- 4 coverage matrix
  async function coverageRows() {
    const [cov, reqs] = await Promise.all([api('GET', P() + '/coverage'), api('GET', P() + '/requirements')]);
    let rows = (cov && cov.requirements) || [];
    if (!rows.length && reqs.length) rows = reqs.map((r) => ({ requirement: r, auto: null, auto_outdated: true, human_confirmed: null, human_exception: null, _noRun: true }));
    return { cov, rows, reqs };
  }
  SCREENS.coverage = async function () {
    const [{ cov, rows }, proj] = await Promise.all([coverageRows(), loadProject()]);
    const counts = proj.assets || {};
    const out = [pageHead('覆蓋矩陣', '每列一個需求。AI 判定與人工狀態分開顯示；只有人工確認才算數。',
      [btn('匯出 HTML', { icon: 'external', onclick: () => doExport('html') }), btn('重新分析', { kind: 'primary', icon: 'refresh', onclick: startAnalyze })])];
    if (cov && cov.run && cov.outdated) out.push(banner('warn', '需求或素材已變更，請重新分析', '下表的 AI 判定來自舊快照；過期的列以「結果已過期」標示。'));
    if (counts.failed) out.push(banner('warn', '這 ' + counts.failed + ' 支影片尚未完成解析；目前結果只涵蓋其餘素材。', null, [btn('查看', { sm: true, href: '#/assets/failed' })]));
    if (S.job && (S.job.state === 'running' || S.job.state === 'queued')) out.push(h('div', { class: 'panel', style: 'margin-bottom:14px' }, jobPanel()));
    if (!totalAssets(counts)) out.push(banner('info', '尚未加入素材，現在不能判斷是否缺鏡頭。', null, [btn('前往素材庫', { sm: true, href: '#/assets' })]));

    if (!rows.length) {
      out.push(panel(null, empty('list', '還沒有需求', '先在需求編輯器建立腳本中的必要鏡頭。', [btn('新增需求', { kind: 'primary', icon: 'plus', href: '#/requirements/new' })]), { raw: true }));
      return h('div', null, out);
    }

    const run = cov && cov.run;
    const scope = (cov && cov.scope) || {};
    const scopeVals = Object.values(scope);
    const runbar = h('div', { class: 'runbar' },
      run ? [h('span', { class: 'kv-inline' }, '執行 ', h('b', { class: 'mono' }, run.run_id)), h('span', { class: 'kv-inline' }, '時間 ', h('b', null, fmtDate(run.created_at))),
        h('span', { class: 'kv-inline' }, '後端 ', h('b', null, run.backend)), h('span', { class: 'kv-inline' }, '模型 ', h('b', { class: 'mono' }, run.model_fingerprint)),
        scopeVals.length ? h('span', { class: 'kv-inline' }, '分析範圍 ', h('b', null, scopeVals.length + ' 支素材（已分析 ' + scopeVals.filter((s) => s === 'analyzed').length + '、失敗 ' + scopeVals.filter((s) => s === 'failed').length + '）')) : null]
        : h('span', null, '尚無分析快照，下表的 AI 判定都是「尚未分析」。'));

    const groups = {
      all: () => true,
      review: (r) => !r.human_confirmed && !r.human_exception && r.auto && ['candidate', 'partial'].includes(r.auto.status),
      gap: (r) => r.auto && ['not_found', 'unverifiable', 'failed'].includes(r.auto.status),
      human: (r) => r.human_confirmed || r.human_exception,
    };
    const gLabel = { all: ['全部', 'grid'], review: ['待人工確認', 'target'], gap: ['缺口／無法判定', 'searchx'], human: ['已人工處理', 'checkc'] };
    const tableBox = h('div');
    const draw = (g) => {
      const vis = rows.filter(groups[g]);
      const seg = h('div', { class: 'seg', role: 'group', 'aria-label': '篩選需求' }, Object.keys(groups).map((k) =>
        h('button', { type: 'button', 'aria-pressed': String(k === g), onclick: () => draw(k) }, icon(gLabel[k][1]), gLabel[k][0], h('span', { class: 'count' }, String(rows.filter(groups[k]).length)))));
      const tbl = h('table', { class: 'tbl matrix' },
        h('thead', null, h('tr', null,
          h('th', { scope: 'col', class: 'col-id' }, 'ID'), h('th', { scope: 'col' }, '需求'), h('th', { scope: 'col', class: 'col-auto' }, '自動判定（AI）'),
          h('th', { scope: 'col', class: 'col-human' }, '人工狀態'), h('th', { scope: 'col' }, '原因'), h('th', { scope: 'col', class: 'col-thumb' }, '最佳候選'),
          h('th', { scope: 'col', class: 'col-act' }, h('span', { class: 'sr-only' }, '動作')))),
        h('tbody', null, vis.map((row) => {
          const r = row.requirement;
          const c = row.auto && row.auto.candidates && row.auto.candidates[0];
          const st = row.auto && row.auto.status;
          return h('tr', { class: ['not_found', 'failed'].includes(st) ? 'row-fail' : (['partial', 'unverifiable'].includes(st) ? 'row-warn' : null) },
            h('td', { class: 'id' }, r.requirement_id, h('div', { class: 'faint small' }, 'v' + r.revision)),
            h('td', null, h('div', { class: 'src' }, r.source_text), h('div', { class: 'q' }, r.query_en),
              h('div', { class: 'chips', style: 'margin-top:6px' },
                !r.confirmed ? chip(AUTO.draft, { text: '需求未確認' }) : null,
                !r.required ? chip({ zh: '非必要', icon: 'circle', tone: 'slate' }) : null,
                r.excluded_reason ? chip({ zh: '已排除', icon: 'ban', tone: 'slate' }, { title: r.excluded_reason }) : null)),
            h('td', null, autoChip(row, cov)),
            h('td', null, row._noRun ? h('span', { class: 'faint small' }, '分析後顯示') : humanChip(row)),
            h('td', null, reasonList(row.auto && row.auto.reasons)),
            h('td', null, c ? thumb(c.asset_id, c.start_ms, r.source_text + ' 的最佳候選') : noThumb(row.auto ? '沒有候選' : '—'),
              c ? h('div', { class: 'faint small mono', style: 'margin-top:4px' }, fmtTime(c.start_ms) + '–' + fmtTime(c.end_ms)) : null),
            h('td', { class: 'cell-actions' }, h('a', { class: 'btn sm' + (c ? ' primary' : ''), href: '#/evidence/' + encodeURIComponent(r.requirement_id) }, icon('eye'), h('span', null, '開啟證據'))));
        })));
      tableBox.replaceChildren(h('div', { class: 'row', style: 'padding:12px 16px;border-bottom:1px solid var(--line-soft)' }, seg),
        vis.length ? h('div', { class: 'table-wrap' }, tbl) : h('p', { class: 'faint', style: 'padding:16px' }, '沒有符合篩選的需求。'));
    };
    draw('all');
    out.push(h('section', { class: 'panel', 'aria-label': '覆蓋矩陣' }, runbar, tableBox));
    return h('div', null, out);
  };

  // ---------- 5 evidence viewer
  SCREENS.evidence = async function (params) {
    const [{ cov, rows }, assets] = await Promise.all([coverageRows(), api('GET', P() + '/assets')]);
    if (!rows.length) return h('div', null, pageHead('證據檢視器'), panel(null, empty('eye', '還沒有需求', '建立需求並分析後，才能檢視證據。', [btn('需求編輯器', { href: '#/requirements/new', kind: 'primary' })]), { raw: true }));
    let rid = params[0];
    if (!rid) { const withC = rows.find((r) => r.auto && r.auto.candidates && r.auto.candidates.length); rid = (withC || rows[0]).requirement.requirement_id; }
    const idxRow = rows.findIndex((r) => r.requirement.requirement_id === rid);
    if (idxRow < 0) return errorState(new ApiError(404, { code: 'NOT_FOUND', message: '找不到需求 ' + rid }), null);
    const row = rows[idxRow];
    const req = row.requirement;
    const cands = (row.auto && row.auto.candidates) || [];
    let ci = Math.min(Math.max(0, parseInt(params[1], 10) || 0), Math.max(0, cands.length - 1));
    const cand = cands[ci] || null;
    const assetById = Object.fromEntries(assets.map((a) => [a.asset_id, a]));
    const asset = cand ? assetById[cand.asset_id] : null;
    const run = cov && cov.run;
    const nav = (i) => go('#/evidence/' + encodeURIComponent(rid) + '/' + i);
    const prevReq = rows[idxRow - 1], nextReq = rows[idxRow + 1];

    // header
    const head = h('section', { class: 'panel ev-head', 'aria-label': '證據資訊' },
      h('div', { class: 'meta', style: 'min-width:0' }, h('span', { class: 'k' }, '檔案'),
        h('span', { class: 'ev-file', title: asset ? (asset.locations || [])[0] : '' }, asset ? baseName((asset.locations || [])[0] || asset.asset_id) : (cand ? cand.asset_id : '—'))),
      h('div', { class: 'meta' }, h('span', { class: 'k' }, '原始時段'),
        h('span', { class: 'v mono' }, cand ? fmtTime(cand.start_ms) + ' – ' + fmtTime(cand.end_ms) : '—')),
      h('div', { class: 'meta' }, h('span', { class: 'k' }, '長度'), h('span', { class: 'v mono' }, cand ? ((cand.end_ms - cand.start_ms) / 1000).toFixed(3) + ' s' : '—')),
      h('div', { class: 'meta' }, h('span', { class: 'k' }, '後端'), h('span', { class: 'v' }, run ? run.backend : '—')),
      h('div', { class: 'meta' }, h('span', { class: 'k' }, '執行編號'), h('span', { class: 'v mono' }, run ? run.run_id : '—')),
      h('div', { class: 'meta' }, h('span', { class: 'k' }, 'Take'), h('span', { class: 'v mono' }, cand ? cand.capture_id || '—' : '—')),
      h('span', { class: 'grow' }),
      h('div', { class: 'meta' }, h('span', { class: 'k' }, '自動判定'), autoChip(row, cov)),
      h('div', { class: 'meta' }, h('span', { class: 'k' }, '人工狀態'), row._noRun ? h('span', { class: 'faint small' }, '分析後顯示') : humanChip(row)));

    // left: requirement
    const hard = (req.constraints || []).filter((c) => c.hard !== false);
    const soft = (req.constraints || []).filter((c) => c.hard === false);
    const consItem = (c) => h('li', null, h('div', { class: 'row', style: 'gap:6px;justify-content:space-between' },
      h('strong', null, KIND_ZH[c.kind] || c.kind), capChip(c.capability)),
    c.note ? h('span', { class: 'small muted' }, c.note) : null,
    c.params && Object.keys(c.params).length ? h('code', { class: 'faint' }, JSON.stringify(c.params)) : null);
    const left = panel(req.requirement_id + ' · 第 ' + req.revision + ' 版', h('div', null,
      h('div', { class: 'stack' },
        h('div', null, h('div', { class: 'faint small' }, '中文原文'), h('div', { style: 'font-weight:600;font-size:15px' }, req.source_text)),
        h('div', null, h('div', { class: 'faint small' }, '英文檢索字'), h('div', { class: 'mono small muted', lang: 'en' }, req.query_en)),
        kvs([['最短連續', fmtSec(req.min_duration_ms)], ['最少 take', String(req.min_takes)], ['權重', String(req.weight)]]),
        reasonList(row.auto && row.auto.reasons)),
      h('div', { class: 'stack' },
        h('div', null, h('h3', { style: 'margin-bottom:8px' }, '硬性條件（' + (hard.length + (req.min_duration_ms ? 1 : 0)) + '）'),
          h('ul', { class: 'hard-list' },
            req.min_duration_ms ? h('li', null, h('div', { class: 'row', style: 'gap:6px;justify-content:space-between' }, h('strong', null, '連續時長 ≥ ' + fmtSec(req.min_duration_ms)), capChip('auto'))) : null,
            hard.map(consItem)),
          !hard.length && !req.min_duration_ms ? h('p', { class: 'faint small' }, '只有語意內容條件。') : null),
        soft.length ? h('div', null, h('h3', { style: 'margin-bottom:8px' }, '參考條件'), h('ul', { class: 'hard-list' }, soft.map(consItem))) : null)),
    { icon: 'list', h: 'h2', cls: 'ev-left', right: h('div', { class: 'row', style: 'gap:4px' },
      btn('', { sm: true, kind: 'ghost', icon: 'left', aria: '上一個需求', title: '上一個需求', disabled: !prevReq, onclick: () => prevReq && go('#/evidence/' + encodeURIComponent(prevReq.requirement.requirement_id)) }),
      btn('', { sm: true, kind: 'ghost', icon: 'right', aria: '下一個需求', title: '下一個需求', disabled: !nextReq, onclick: () => nextReq && go('#/evidence/' + encodeURIComponent(nextReq.requirement.requirement_id)) })) });

    // center: player + timeline + candidates
    const startOff = asset && asset.probe && asset.probe.start_ms ? asset.probe.start_ms : 0;
    const video = h('video', { preload: 'auto', playsinline: true, muted: true, 'aria-label': '候選片段影片' });
    const overlay = h('div', { class: 'p-overlay' });
    const player = h('div', { class: 'player' }, video, overlay,
      h('div', { class: 'p-badge' }, cand ? chip({ zh: '候選 ' + (ci + 1) + ' / ' + cands.length, icon: 'target', tone: 'violet' }) : null));
    let loop = true;
    const tc = h('span', { class: 'tc', 'aria-live': 'off' }, cand ? fmtTime(cand.start_ms) : '—');
    const playBtn = btn('播放', { icon: 'play', kind: 'primary', sm: true });
    const loopBtn = btn('循環片段', { icon: 'repeat', sm: true, pressed: 'true' });
    const toStart = btn('回到起點', { icon: 'back', sm: true });
    const vt = (ms) => Math.max(0, (ms - startOff) / 1000);
    const curMs = () => Math.round(video.currentTime * 1000) + startOff;
    const seekMs = (ms) => { try { video.currentTime = vt(ms); } catch (e) { /* not ready */ } };
    if (cand) {
      overlay.replaceChildren(h('span', null, PREVIEW ? '預覽模式不載入影片' : '載入影片中…'));
      if (PREVIEW) {
        const f = (PREVIEW.frames || {})[cand.asset_id];
        if (f) video.setAttribute('poster', f);
        overlay.style.background = 'linear-gradient(transparent 55%, rgba(0,0,0,.7))';
        overlay.style.justifyContent = 'flex-end';
      } else {
        videoUrl(cand.asset_id).then((u) => { video.src = u; }, (e) => {
          overlay.replaceChildren(icon('alert'), h('strong', null, '無法載入影片'), h('span', { class: 'small' }, NEXT_STEP[e.code] || e.message));
        });
      }
      video.addEventListener('loadedmetadata', () => { overlay.remove(); seekMs(cand.start_ms); });
      video.addEventListener('error', () => { overlay.replaceChildren(icon('alert'), h('strong', null, '瀏覽器無法播放這個檔案'), h('span', { class: 'small' }, '編碼可能不受瀏覽器支援；仍可用縮圖與時間碼複核，或在剪輯軟體中開啟原檔。')); if (!overlay.isConnected) player.append(overlay); });
      let raf = 0;
      const watch = () => {
        const ms = curMs();
        tc.textContent = fmtTime(ms);
        if (head_) head_.style.left = pct(ms) + '%';
        if (loop && ms >= cand.end_ms) seekMs(cand.start_ms);
        if (!video.paused) raf = requestAnimationFrame(watch);
      };
      video.addEventListener('play', () => { playBtn.lastChild.textContent = '暫停'; playBtn.firstChild.replaceWith(icon('pause')); if (curMs() >= cand.end_ms || curMs() < cand.start_ms - 50) seekMs(cand.start_ms); raf = requestAnimationFrame(watch); });
      video.addEventListener('pause', () => { playBtn.lastChild.textContent = '播放'; playBtn.firstChild.replaceWith(icon('play')); cancelAnimationFrame(raf); });
      video.addEventListener('seeked', watch);
      cleanup.push(() => { cancelAnimationFrame(raf); video.pause(); video.removeAttribute('src'); });
      playBtn.addEventListener('click', () => { if (video.paused) video.play().catch(() => {}); else video.pause(); });
      loopBtn.addEventListener('click', () => { loop = !loop; loopBtn.setAttribute('aria-pressed', String(loop)); });
      toStart.addEventListener('click', () => seekMs(cand.start_ms));
    } else {
      overlay.replaceChildren(icon('searchx'), h('strong', null, '這個需求沒有自動候選'), h('span', { class: 'small' }, '可在右側用「修正時段」手動指定素材與時段。'));
      [playBtn, loopBtn, toStart].forEach((b) => { b.disabled = true; });
    }

    // timeline for the candidate's asset
    let head_ = null;
    const durMs = asset ? (asset.duration_ms || (asset.probe && asset.probe.duration_ms) || 0) : 0;
    const sameAsset = cand ? cands.map((c, i) => [c, i]).filter(([c]) => c.asset_id === cand.asset_id) : [];
    const domainEnd = Math.max(durMs + startOff, ...sameAsset.map(([c]) => c.end_ms), 1) ;
    const domainStart = startOff;
    const pct = (ms) => Math.max(0, Math.min(100, (ms - domainStart) / (domainEnd - domainStart) * 100));
    let timeline = null;
    if (cand) {
      const span = domainEnd - domainStart;
      const steps = [1000, 2000, 5000, 10000, 15000, 30000, 60000, 120000, 300000, 600000];
      const step = steps.find((s) => span / s <= 8) || 600000;
      const ticks = [];
      for (let t = Math.ceil(domainStart / step) * step; t <= domainEnd; t += step) ticks.push(h('span', { class: 'tl-tick', style: 'left:' + pct(t) + '%' }, fmtTime(t).slice(0, 5)));
      head_ = h('span', { class: 'tl-head', style: 'left:' + pct(cand.start_ms) + '%' });
      timeline = h('div', { class: 'timeline', role: 'group', 'aria-label': '素材時間軸：' + fmtTime(domainStart) + ' 至 ' + fmtTime(domainEnd),
        onclick: (e) => { if (e.target !== timeline && !e.target.classList.contains('tl-ruler')) return; const r = timeline.getBoundingClientRect(); seekMs(domainStart + (e.clientX - r.left) / r.width * span); } },
      h('div', { class: 'tl-ruler' }, ticks),
      sameAsset.map(([c, i]) => h('button', {
        type: 'button', class: 'tl-seg' + (i === ci ? ' active' : '') + (c.source === 'manual' ? ' manual' : ''),
        style: 'left:' + pct(c.start_ms) + '%;width:max(6px,' + (pct(c.end_ms) - pct(c.start_ms)) + '%)',
        'aria-label': '候選 ' + (i + 1) + '：' + fmtTime(c.start_ms) + ' 至 ' + fmtTime(c.end_ms), title: '候選 ' + (i + 1) + '  ' + fmtTime(c.start_ms) + '–' + fmtTime(c.end_ms),
        onclick: () => (i === ci ? seekMs(c.start_ms) : nav(i)),
      }, String(i + 1))), head_);
    }
    const candList = cands.length ? h('div', { class: 'cand-list', role: 'list' }, cands.map((c, i) => {
      const a = assetById[c.asset_id];
      const ov = VERDICT[c.overall] || VERDICT.unknown;
      return h('div', { role: 'listitem' }, h('button', { type: 'button', class: 'cand', 'aria-current': i === ci ? 'true' : null, onclick: () => nav(i) },
        thumb(c.asset_id, c.start_ms, '候選 ' + (i + 1)),
        h('span', { class: 'c-meta' },
          h('span', { class: 'row', style: 'gap:6px' }, h('strong', null, '候選 ' + (i + 1)), chip(ov, { aria: '整體：' + ov.zh })),
          h('span', { class: 'mono', title: a ? (a.locations || [])[0] : c.asset_id }, a ? baseName((a.locations || [])[0]) : c.asset_id),
          h('span', { class: 'mono faint' }, fmtTime(c.start_ms) + '–' + fmtTime(c.end_ms) + ' · 排序分數 ' + Number(c.ranking_score).toFixed(3)))));
    })) : h('p', { class: 'faint small' }, '沒有其他候選。');

    const center = h('div', { class: 'ev-center' },
      player,
      h('div', { class: 'transport' }, playBtn, toStart, loopBtn, h('span', { class: 'grow' }), tc,
        cand ? h('span', { class: 'faint small mono' }, '片段 ' + fmtTime(cand.start_ms) + '–' + fmtTime(cand.end_ms)) : null),
      timeline,
      timeline ? h('div', { class: 'tl-legend' }, h('span', null, h('i', { style: 'background:rgba(108,76,245,.6)' }), '目前候選'),
        h('span', null, h('i', { style: 'background:rgba(108,76,245,.22);border:1px solid rgba(139,114,255,.55)' }), '同一素材的其他候選'),
        h('span', null, h('i', { style: 'background:var(--cyan)' }), '播放位置'),
        h('span', null, '快捷鍵：空白鍵 播放／暫停 · J 起點 · L 終點 · [ ] 切換候選')) : null,
      h('section', { class: 'panel', style: 'margin-top:14px', 'aria-label': '這個需求的所有候選' },
        h('div', { class: 'panel-head' }, h('h2', null, icon('target'), '這個需求的候選（' + cands.length + '）')),
        h('div', { class: 'panel-body' }, candList)));

    // right: conditions + actions
    const conds = cand ? cand.conditions || [] : [];
    const condList = conds.length ? h('div', null, conds.map((x) => {
      const v = VERDICT[x.verdict] || VERDICT.unknown;
      return h('div', { class: 'cond' }, icon(v.icon, v.cls), h('div', null,
        h('div', { class: 'c-kind' }, KIND_ZH[x.kind] || x.kind, chip(v, { aria: (KIND_ZH[x.kind] || x.kind) + '：' + v.zh })),
        x.reason ? h('div', { class: 'c-reason' }, x.reason) : null));
    })) : h('p', { class: 'faint small' }, cand ? '沒有逐項條件結果。' : '沒有候選可檢查。');

    const right = h('div', { class: 'ev-right stack' },
      cand ? h('div', { class: 'score', title: 'ranking_score 只用於排序，不是機率' },
        h('div', null, h('div', { class: 's-l' }, '排序分數（非機率）'), h('div', { class: 'faint small' }, '只用來排序候選，不代表正確的機率')),
        h('div', { class: 's-v' }, Number(cand.ranking_score).toFixed(3))) : null,
      panel('條件檢查', condList, { icon: 'checkc' }),
      decisionPanel(row, cand, assets, { curMs: () => (cand ? curMs() : null), nav }));

    // keyboard shortcuts (scoped to this screen)
    const onKey = (e) => {
      if (e.target.closest && e.target.closest('input, textarea, select, [contenteditable]')) return;
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      if (e.key === ' ' && cand && !(e.target.closest && e.target.closest('button, a'))) { e.preventDefault(); playBtn.click(); }
      else if ((e.key === 'j' || e.key === 'J') && cand) seekMs(cand.start_ms);
      else if ((e.key === 'l' || e.key === 'L') && cand) seekMs(Math.max(cand.start_ms, cand.end_ms - 100));
      else if (e.key === '[' && ci > 0) nav(ci - 1);
      else if (e.key === ']' && ci < cands.length - 1) nav(ci + 1);
    };
    document.addEventListener('keydown', onKey);
    cleanup.push(() => document.removeEventListener('keydown', onKey));

    return h('div', null,
      h('div', { class: 'row', style: 'margin-bottom:12px' }, btn('覆蓋矩陣', { sm: true, kind: 'ghost', icon: 'left', href: '#/coverage' }),
        h('h1', { class: 'grow', style: 'font-size:18px' }, '證據檢視器'),
        cov && cov.outdated && cov.run ? chip(AUTO_STALE, { text: '分析快照已過期' }) : null),
      head,
      h('div', { class: 'ev-grid' }, left, center, right));
  };

  function decisionPanel(row, cand, assets, ctx) {
    const req = row.requirement;
    const box = h('div', { class: 'stack' });
    const sub = h('div');
    const done = h('div', { class: 'decided', 'aria-live': 'polite' });
    const send = async (decision, payload, okText) => {
      try {
        const r = await api('POST', P() + '/review', Object.assign({ requirement_id: req.requirement_id, revision: req.revision, decision, reason: '', source: 'model' }, payload));
        done.replaceChildren(banner('info', '已記錄：' + okText, '決策綁定需求第 ' + req.revision + ' 版' + (r && r.decision_id ? '（' + r.decision_id + '）' : '') + '。人工狀態已更新。'));
        sub.replaceChildren();
        return true;
      } catch (e) {
        if (e.code === 'STALE_REVISION') done.replaceChildren(banner('error', '需求已被修改，請重新載入', '這筆決策沒有寫入。', [btn('重新載入', { sm: true, icon: 'refresh', onclick: () => render() })]));
        else showError(e, '決策沒有寫入');
        return false;
      }
    };
    const rng = cand ? { asset_id: cand.asset_id, start_ms: cand.start_ms, end_ms: cand.end_ms, source: cand.source === 'manual' ? 'manual' : 'model' } : null;
    const noteIn = h('textarea', { class: 'input', rows: 2, id: 'dc-note', placeholder: '（選填）例：手持晃動太大' });

    const openSub = (node) => { sub.replaceChildren(node); const f = node.querySelector('input, textarea, select'); if (f) f.focus(); };

    const fixForm = () => {
      const analyzed = assets.filter((a) => a.status !== 'excluded');
      let aid = cand ? cand.asset_id : (analyzed[0] && analyzed[0].asset_id);
      const sIn = h('input', { class: 'input mono', id: 'fx-s', value: cand ? fmtTime(cand.start_ms) : '00:00.000', inputmode: 'decimal' });
      const eIn = h('input', { class: 'input mono', id: 'fx-e', value: cand ? fmtTime(cand.end_ms) : '00:03.000', inputmode: 'decimal' });
      const err = h('div', { class: 'err-line', role: 'alert' });
      const here = (inp) => btn('目前位置', { sm: true, kind: 'ghost', icon: 'clock', disabled: !cand, onclick: () => { const m = ctx.curMs(); if (m != null) inp.value = fmtTime(m); } });
      return h('div', { class: 'subform', role: 'group', 'aria-label': '修正時段' },
        h('strong', null, '修正時段（以人工片段記錄）'),
        h('div', { class: 'field' }, h('label', { for: 'fx-a' }, '素材'),
          h('select', { id: 'fx-a', class: 'input', onchange: (e) => { aid = e.target.value; } },
            analyzed.map((a) => h('option', { value: a.asset_id, selected: a.asset_id === aid }, baseName((a.locations || [])[0] || a.asset_id))))),
        h('div', { class: 'grid-2', style: 'gap:8px' },
          h('div', { class: 'field' }, h('label', { for: 'fx-s' }, '開始（mm:ss.mmm）'), sIn, here(sIn)),
          h('div', { class: 'field' }, h('label', { for: 'fx-e' }, '結束（mm:ss.mmm）'), eIn, here(eIn))),
        err,
        h('div', { class: 'row', style: 'justify-content:flex-end' }, btn('取消', { sm: true, kind: 'ghost', onclick: () => sub.replaceChildren() }),
          btn('以此時段接受', { sm: true, kind: 'primary', icon: 'check', onclick: () => {
            const s = parseTime(sIn.value), e = parseTime(eIn.value);
            if (!isFinite(s) || !isFinite(e)) { err.textContent = '時間格式請用 mm:ss.mmm，例如 01:02.500。'; return; }
            if (s >= e) { err.textContent = '開始時間要早於結束時間。'; return; }
            if (!aid) { err.textContent = '請選擇素材。'; return; }
            send('accepted', { asset_id: aid, start_ms: s, end_ms: e, source: 'manual', reason: noteIn.value.trim() }, '人工修正時段 ' + fmtTime(s) + '–' + fmtTime(e));
          } })));
    };
    const excForm = () => {
      const rIn = h('textarea', { class: 'input', id: 'ex-r', rows: 3, placeholder: '例：客戶同意以 2.4 秒版本使用，剪接時放慢 80%' });
      const ok = btn('確認接受例外', { sm: true, kind: 'primary', icon: 'flag', disabled: true });
      rIn.addEventListener('input', () => { ok.disabled = !rIn.value.trim(); });
      ok.addEventListener('click', () => { if (rIn.value.trim()) send('overridden', Object.assign({}, rng, { source: rng.source, reason: rIn.value.trim() }), '人工接受例外'); });
      return h('div', { class: 'subform', role: 'group', 'aria-label': '人工接受例外' },
        h('strong', null, '人工接受例外'),
        h('p', { class: 'small muted' }, '片段不完全符合條件，但人工決定接受。理由為必填，會寫入報告。'),
        h('div', { class: 'field' }, h('label', { for: 'ex-r' }, '理由（必填）'), rIn),
        h('div', { class: 'row', style: 'justify-content:flex-end' }, btn('取消', { sm: true, kind: 'ghost', onclick: () => sub.replaceChildren() }), ok));
    };
    const reshootForm = () => h('div', { class: 'subform', role: 'group', 'aria-label': '需要補拍' },
      h('strong', null, '需要補拍'),
      h('p', { class: 'small muted' }, cand ? '會把目前候選記錄為「拒絕」（理由：需要補拍），然後前往複核／補拍板。補拍卡片會在下次分析後出現。' : '這個需求沒有候選；前往複核／補拍板查看建議。'),
      h('div', { class: 'row', style: 'justify-content:flex-end' }, btn('取消', { sm: true, kind: 'ghost', onclick: () => sub.replaceChildren() }),
        btn(cand ? '記錄並前往補拍板' : '前往補拍板', { sm: true, kind: 'primary', icon: 'camera', onclick: async () => {
          if (!cand) { go('#/board'); return; }
          if (await send('rejected', Object.assign({}, rng, { reason: '需要補拍' + (noteIn.value.trim() ? '：' + noteIn.value.trim() : '') }), '拒絕（需要補拍）')) go('#/board');
        } })));

    box.append(
      h('div', { class: 'field' }, h('label', { for: 'dc-note' }, '備註／拒絕理由'), noteIn),
      h('div', { class: 'actions-grid' },
        btn('接受', { kind: 'success', icon: 'check', disabled: !cand, onclick: () => send('accepted', Object.assign({}, rng, { reason: noteIn.value.trim() }), '接受候選 ' + fmtTime(cand.start_ms) + '–' + fmtTime(cand.end_ms)) }),
        btn('拒絕', { kind: 'danger', icon: 'x', disabled: !cand, onclick: () => send('rejected', Object.assign({}, rng, { reason: noteIn.value.trim() }), '拒絕候選') }),
        btn('修正時段', { icon: 'scissors', onclick: () => openSub(fixForm()) }),
        btn('人工接受例外', { icon: 'flag', disabled: !cand, onclick: () => openSub(excForm()) }),
        h('div', { class: 'full' }, btn('需要補拍', { icon: 'camera', block: true, onclick: () => openSub(reshootForm()) }))),
      sub, done,
      h('p', { class: 'faint small' }, '決策只套用在需求第 ' + req.revision + ' 版；需求修改後需重新確認。'));
    if (!cand) setTimeout(() => sub.childElementCount || sub.replaceChildren(fixForm()), 0);
    return panel('人工決策', box, { icon: 'user' });
  }

  // ---------- 6 review / reshoot board
  SCREENS.board = async function () {
    const cards = await api('GET', P() + '/reshoots');
    const cov = await api('GET', P() + '/coverage').catch(() => null);
    const out = [pageHead('複核／補拍板', '系統依已確認需求與證據整理；所有建議都要人工確認，不會自動改狀態。',
      [btn('匯出 CSV', { icon: 'download', onclick: () => doExport('csv') })])];
    if (cov && cov.run && cov.outdated) out.push(banner('warn', '需求或素材已變更，請重新分析', '卡片來自上一次分析；有修改的需求在重新分析前不會出現。'));
    if (!cov || !cov.run) {
      out.push(panel(null, empty('board', '尚無分析結果', '分析完成後才會產生複核與補拍建議。', [btn('前往素材庫', { href: '#/assets', kind: 'primary' })]), { raw: true }));
      return h('div', null, out);
    }
    const review = cards.filter((c) => c.kind === 'review_first' || (c.kind !== 'reshoot_proposed' && c.review_first));
    const reshoot = cards.filter((c) => !review.includes(c));
    const col = (title, ic, tone, list, emptyText, hint) => h('section', { class: 'panel', 'aria-label': title },
      h('div', { class: 'col-head' }, h('span', { class: 'chip tone-' + tone, 'aria-hidden': 'true' }, icon(ic)), h('h2', null, title), h('span', { class: 'count' }, String(list.length))),
      h('div', { class: 'col-body' }, h('p', { class: 'faint small' }, hint), list.length ? list.map(card) : h('p', { class: 'muted', style: 'padding:12px 0' }, emptyText)));
    out.push(h('div', { class: 'board' },
      col('先複核', 'eye', 'violet', review, '目前沒有需要先複核的需求。', '已有部分證據，先看片段再決定是否補拍。'),
      col('建議補拍（待確認）', 'camera', 'orange', reshoot, '目前沒有補拍建議。', '已分析範圍內找不到可用片段；確認後再排入拍攝。')));
    return h('div', null, out);
  };

  function card(c) {
    let status = c.status || 'proposed';
    const stBox = h('span');
    const drawSt = () => stBox.replaceChildren(chip({ zh: (RESHOOT_ST.find((s) => s[0] === status) || [0, status])[1], icon: RESHOOT_ICON[status] || 'circle', tone: RESHOOT_TONE[status] || 'slate' }, { aria: '狀態：' + status }));
    drawSt();
    const seg = h('div', { class: 'seg', role: 'group', 'aria-label': c.requirement_id + ' 狀態' });
    const drawSeg = () => seg.replaceChildren(...RESHOOT_ST.map(([k, zh]) => h('button', { type: 'button', 'aria-pressed': String(k === status), onclick: async () => {
      if (k === status) return;
      try {
        await api('POST', P() + '/reshoots/' + encodeURIComponent(c.requirement_id) + '/status', { revision: c.requirement_revision, status: k });
        status = k; drawSt(); drawSeg();
        toast({ kind: 'ok', title: c.requirement_id + ' 狀態已更新', text: zh });
      } catch (e) { showError(e, '狀態沒有更新'); }
    } }, zh)));
    drawSeg();
    const b = c.best_candidate;
    const fact = (k, v) => h('div', null, h('div', { class: 'k' }, k), h('div', null, v == null || v === '' ? '—' : String(v)));
    return h('article', { class: 'card', 'aria-label': c.requirement_id + ' ' + c.source_text },
      h('div', { class: 'card-top' }, h('span', { class: 'id mono faint' }, c.requirement_id), h('span', { class: 'src' }, c.source_text), stBox),
      h('div', { class: 'chips' }, (c.reasons || []).map((code, i) => h('span', { class: 'reason', title: code }, icon('info'), (c.reasons_zh && c.reasons_zh[i]) || REASON_ZH[code] || code))),
      b ? h('div', { class: 'best' }, thumb(b.asset_id, b.start_ms, c.source_text + ' 的最佳候選'),
        h('div', null, h('div', { class: 'small' }, '最佳候選 ', h('span', { class: 'mono' }, fmtTime(b.start_ms) + '–' + fmtTime(b.end_ms))),
          b.shortfalls && b.shortfalls.length ? h('ul', { class: 'shortfalls' }, b.shortfalls.map((s) => h('li', null, s))) : h('div', { class: 'faint small' }, '沒有列出不足之處。')))
        : h('div', { class: 'faint small' }, '沒有可用的候選片段。'),
      h('div', { class: 'facts' },
        fact('最短連續時長', c.min_continuous_s != null ? c.min_continuous_s + ' 秒' : null), fact('前後預留', c.handles),
        fact('構圖', c.composition), fact('道具／人物', c.props), h('div', { style: 'grid-column:1/-1' }, h('div', { class: 'k' }, '驗收方式'), h('div', null, c.verify_by || '—'))),
      h('div', { class: 'card-foot' }, seg,
        h('a', { class: 'btn sm', href: '#/evidence/' + encodeURIComponent(c.requirement_id) }, icon('eye'), h('span', null, '開啟證據'))));
  }

  // ---------- 7 device & diagnostics
  SCREENS.device = async function () {
    const [hl, dv] = await Promise.all([api('GET', '/health'), api('GET', '/device/status')]);
    S.health = hl; S.device = dv;
    const dev = dv.device || {};
    const be = dv.active_backend;
    const BE_TEXT = {
      'cpu-reference': 'CPU 參考後端：結果可重現，但不代表 NPU 的速度或功耗。',
      'cuda-reference': 'CUDA 參考後端（GPU）：用於開發比對，不代表 NPU 的速度或功耗。',
      'not loaded': '尚未載入模型；第一次分析時才會載入。',
    };
    const yes = (b, y, n) => b ? chip({ zh: y, icon: 'checkc', tone: 'green' }) : chip({ zh: n, icon: 'xc', tone: 'slate' });
    const out = [pageHead('裝置與診斷', '顯示實際執行的後端與模型；無法量測的指標一律顯示 N/A。', [btn('重新偵測', { icon: 'refresh', onclick: () => { refreshStatus(); render(); } })])];
    if (!dev.available) out.push(banner('info', 'UGen300 未連線', '目前使用明示的 CPU 參考後端執行；所有結果與報告都會標示實際後端。'));
    out.push(h('div', { class: 'grid-2' },
      panel('UGen300 裝置', kvs([
        ['連線狀態', dev.available ? chip({ zh: '已連線', icon: 'plug', tone: 'green' }) : chip({ zh: '未連線', icon: 'plugoff', tone: 'orange' })],
        ['型號', dev.model], ['介面', dev.interface], ['Runtime', dev.runtime], ['驅動程式', dev.driver], ['韌體', dev.firmware],
        ['相容性驗證', yes(dev.compatibility_verified, '已在實機驗證', '未驗證')],
        ['說明', dev.reason ? h('span', { class: 'mono small' }, dev.reason) : null]]), { icon: 'cpu' }),
      panel('執行後端', h('div', { class: 'stack' },
        h('div', null, chip({ zh: be === 'not loaded' ? '尚未載入' : be, icon: 'cpu', tone: be === 'not loaded' ? 'slate' : 'violet' }, { lg: true })),
        h('p', { class: 'muted' }, BE_TEXT[be] || '後端：' + be),
        kvs([['服務版本', hl.version], ['NPU 執行中', hl.npu_active == null ? 'N/A' : (hl.npu_active ? '是' : '否')], ['資料庫', hl.db]]),
        dv.note ? h('p', { class: 'faint small' }, dv.note) : null), { icon: 'activity' })));
    const m = dv.manifest;
    out.push(panel('模型 manifest', m ? h('div', { class: 'grid-2' },
      kvs(Object.entries(m).filter(([k]) => k !== 'compatibility_verified').slice(0, Math.ceil((Object.keys(m).length - 1) / 2))
        .map(([k, v]) => [k, h('span', { class: 'mono small' }, v == null ? 'N/A' : typeof v === 'object' ? JSON.stringify(v) : String(v))])),
      kvs(Object.entries(m).filter(([k]) => k !== 'compatibility_verified').slice(Math.ceil((Object.keys(m).length - 1) / 2))
        .map(([k, v]) => [k, h('span', { class: 'mono small' }, v == null ? 'N/A' : typeof v === 'object' ? JSON.stringify(v) : String(v))])
        .concat([['compatibility_verified', yes(m.compatibility_verified, '已驗證', '未驗證')]])))
      : h('p', { class: 'muted' }, '模型尚未載入，沒有 manifest。第一次分析時會載入並在此顯示。'), { icon: 'file' }));
    const na = (k, hint) => h('div', { class: 'na-tile' }, h('div', { class: 'k' }, k), h('div', { class: 'v' }, 'N/A'), h('div', { class: 'faint small' }, hint));
    const npuOn = dev.available && hl.npu_active === true;
    out.push(panel('NPU 指標', h('div', null,
      h('p', { class: 'muted small', style: 'margin-bottom:12px' }, 'NPU 指標無法量測時顯示 N/A。' + (npuOn ? '' : '目前沒有 NPU 在執行，因此不顯示任何 NPU 數字。')),
      h('div', { class: 'grid-3' }, na('NPU 使用率', '需要 UGen300 回報'), na('每影格推論延遲', '僅在 NPU 實際執行時量測'), na('功耗', '需要裝置感測器')),
    ), { icon: 'activity' }));
    out.push(panel('匯出報告', h('div', null,
      h('p', { class: 'muted small', style: 'margin-bottom:12px' }, '報告包含覆蓋結果、人工決策、補拍卡片與實際後端資訊。'),
      h('div', { class: 'exports' },
        btn('JSON', { icon: 'download', disabled: !S.pid, onclick: () => doExport('json') }),
        btn('CSV', { icon: 'download', disabled: !S.pid, onclick: () => doExport('csv') }),
        btn('HTML 報告', { icon: 'external', kind: 'primary', disabled: !S.pid, onclick: () => doExport('html') })),
      !S.pid ? h('p', { class: 'faint small', style: 'margin-top:8px' }, '請先選擇專案。') : null), { icon: 'download' }));
    return h('div', { class: 'stack' }, out);
  };

  // ------------------------------------------------------------------ boot
  function boot() {
    if (PREVIEW) {
      document.body.append(h('div', { class: 'preview-ribbon', role: 'note' }, icon('beaker'), '預覽資料（非實測）'));
    } else if (!TOKEN || TOKEN === '__SG_TOKEN__') {
      toast({ kind: 'error', title: '缺少工作階段權杖', text: '下一步：請從 SceneGap 啟動程式開啟本頁，不要直接開啟 HTML 檔。' });
    }
    window.addEventListener('hashchange', render);
    restoreJob();
    refreshStatus();
    render();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
