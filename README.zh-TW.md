# SceneGap Edge（繁體中文說明）

**收工前，在自己的電腦上把 Shot list 和素材對一次：每個鏡頭都有可播放的片段，由人做最後決定。**

![拒絕一個候選並寫下原因，再接受拉花片段](docs/media/review-reject-accept.gif)

*片段檢視，實際速度（有剪接）。SH-05「咖啡倒入杯中或拉花，連續 3 秒」的第一個候選只拍到萃取流、畫面沒有杯子，所以拒絕並寫下原因；接著接受拉花的片段。*

[示範影片（YouTube）](https://youtu.be/CFYIqu2dkiM) ·
[專案網頁](https://yu9bryan.github.io/scenegap-edge/) ·
[提案簡報 PDF](docs/deck/SceneGapEdge_StageI_Proposal.pdf) ·
[評測報告（英文）](eval/results/REPORT.md) ·
[驗證過程](docs/VALIDATION_zh.md) ·
[English README](README.md)

SceneGap Edge 給小型拍攝團隊和接案剪輯師用。你先寫好 Shot list（例如「咖啡倒入杯中，連續 3 秒」「咖啡師工作畫面，至少兩個 Take」），SceneGap 在本機建立素材索引，找出候選片段和原始時間碼，檢查長度、Take 數和同框條件，逐一告訴你每個鏡頭找到了什麼、哪些判斷不了。每個答案都由人接受或拒絕；找不到可用片段的鏡頭進補拍清單。素材不會上傳。另外可以開啟確認層，主動標出可能沒拍到的鏡頭：在事前登記的 150 段新照片片段上，抓到 65% 的缺鏡頭，誤判要補拍 3.8%（見驗證結果）。

參賽：ASUS UGen AI League（Creator AI，Lightning 組，ASUS UGen300 USB AI 加速器，Hailo-10H）。團隊：rm-rf-1。本專案與 ASUS、Hailo 沒有合作或背書關係。

## 要解決的問題

兩個人一個下午拍一支 60 秒的咖啡店短片，17:40 收工；晚上 11 點剪輯時才發現倒咖啡的鏡頭兩秒就切走，也沒人拍客人喝咖啡。這時場地已經還回去了。

Premiere Pro、DaVinci Resolve、Final Cut Pro 都已經能用內容搜尋素材（Premiere 會回傳片段內的 In/Out 範圍），但它們的官方文件沒有描述檢查 Shot list 的功能：一個鏡頭要多長、要幾個 Take、哪些東西要同框。資料來源見 [`docs/research/BUSINESS_FACTS.md`](docs/research/BUSINESS_FACTS.md)。

## 運作方式

1. **Shot list**：用中文寫，再由人確認一句給模型讀的英文 Query（ADR-003），加上最短長度、Take 數、同框等條件。每次修改都產生新版本，舊結果標成過期，不會沿用。
2. **素材**：先探測格式、算 SHA-256（重複檔案不算第二個 Take）、切鏡頭，依原始時間戳記每秒取一格。
3. **證據**：CLIP ViT-B/32 影像特徵，和文字特徵的 cosine ≥ τ 就算通過。τ 只用 dev 組校準後凍結；沒有校準檔時回答 `UNCALIBRATED`，不猜門檻。
4. **條件檢查**：連續長度用保守的上下界判斷，判斷不了就改成每 250 ms 取一格再算；同框要求所有條件出現在同一格。
5. **三值邏輯**：每個條件是通過、不通過或未知，未知永遠不當成通過。動作、可讀文字、構圖這一版交給人判斷（ADR-004）。
6. **狀態與決定**：AI 只給「有候選／部分符合／沒找到／無法判斷」等狀態，不會自己標成完成；人的接受、拒絕（附原因）另外記錄，以最後一次決定為準。
7. **補拍清單**：找不到可用片段、或人決定要補拍的鏡頭，附上原因和最短長度。補拍回來的新檔案只分析新的那支。

細節見 [`docs/ALGORITHMS.md`](docs/ALGORITHMS.md)（英文）。

## 畫面

| Coverage 總覽 | 補拍清單 |
|---|---|
| ![Coverage](docs/screenshots/04_coverage.png) | ![補拍清單](docs/screenshots/06_reshoots.png) |

更多畫面和 GIF（匯入分析、加入補拍、補拍片段接受）見 [英文 README 的 Walkthrough](README.md#walkthrough)。

## 目前的結果

在 44 支 Wikimedia Commons 公開授權影片（共 25.3 分鐘）上評測，依作者分成 dev 18 支、test 26 支，test 只評一次。

| 項目 | 結果 |
|---|---|
| 找片段（前 5 名） | 11 個鏡頭中 7 個的正確片段在前 5 名（Recall@5 64%、Precision@5 33%）；單幀語意搜尋 8 個（73%／40%）；片名關鍵字 45%／36% |
| 自動判斷缺鏡頭 | **還做不到**：抓到缺鏡頭 0%。門檻是用逐幀 F1 選的，太寬鬆；第二階段改用專案層級的目標重新校準 |
| 檢查量（估算） | 候選片段合計 317 秒，整批 test 素材 839 秒（片長，不是實測的檢查時間） |
| 標註 | 兩個獨立的 AI 標註流程，κ 0.91；143 筆分歧由第三個 AI 流程裁定。還沒有人工標註 |
| 速度（桌機） | 每分鐘影片解碼加特徵擷取 2.3 秒（GPU）／3.1 秒（CPU）；在 10,000 段中文字搜尋 p95 13–14 ms |
| UGen300 | 還沒有實機跑過；G1 檢查腳本已準備好，目前的數字都來自桌機 CPU／GPU |
| 測試 | 46 個自動測試；PRD 36 個驗收案例中 30 個以自動測試通過 |

## 快速開始

```bash
python -m pip install -r requirements-ml.txt
python -m scenegap --workdir ./sg_work
```

打開印出的網址（`http://127.0.0.1:8765/`）。服務只綁定本機，每次啟動產生新的工作階段 token。Docker、參數、API、重跑評測的方式見[英文 README](README.md#quick-start)。

測試（不需要下載模型）：

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## UGen300 計畫

只把 CLIP ViT-B/32 的影像編碼器放到 UGen300（Hailo Model Zoo 的 `clip_vit_b_32_image_encoder`），文字編碼器留在主機 CPU，用同一份 fp32 權重。上線前要先過 G1：同一批 dev 影格分別送進 fp32 參考版和 HEF，比對每格 cosine、每個 Query 的排序相關、前 K 名重疊，以及 dev 上的 Recall@5。沒過就不啟用，繼續用 CPU／GPU 參考版。詳見 [`docs/MODEL_PLAN.md`](docs/MODEL_PLAN.md)。

## 素材來源與授權

程式碼採 Apache-2.0。評測素材不放在 repo 裡，每支影片保留各自的 Commons 授權（CC0、公眾領域、CC BY、CC BY-SA）；完整的作者與授權清單見 [`docs/CREDITS.md`](docs/CREDITS.md)。
