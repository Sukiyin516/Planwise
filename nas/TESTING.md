# NAS 0.3.0 Preview 驗證紀錄

2026-11-12；使用臨時示例帳號及資料庫，沒有導入個人行程。

## 自動驗證

- Python **104 項通過**：原有排程／Android 內置介面測試、NAS API／管理員 CLI，以及 12 項邀請碼註冊與資料庫更新測試。命令：`python -m unittest discover -v`。
- `node --test nas/test_client.cjs`：**10 項通過**，驗證冷啟動先顯示快取、離線停用修改、8 秒中止卡住的請求、重連取得新版才開放寫入、手機預設七日／保留單日、首次無快取與損壞快取仍能顯示登入／重連頁；另驗證註冊欄位、一般帳號隱藏管理設定、輪詢不替換正在填寫的註冊表單，以及不改行程版本也能更新邀請碼使用狀態。
- 邀請碼測試涵蓋雜湊儲存、7 天有效、過期／撤銷／重複使用拒絕、同時註冊只有一人成功、傳入管理員欄位仍為一般帳號、跨來源／CSRF／權限檢查、失敗限流，以及失敗不消耗有效碼。
- 舊資料庫啟動更新僅補建缺少的邀請碼表，逐列核對既有 `users`／`plans`／`sessions` 完全相同；備份後重啟仍可使用未消耗邀請碼。
- 新增 CLI 測試實際呼叫 `nas.manage`：建立管理員只儲存密碼雜湊、密碼不符不建帳號、重設密碼保留原資料並撤銷 session。
- `node --check nas/static/ui.js` 與 `node --check android/runtime/app.js`。
- GitHub Actions 配置檢查兩份 Compose、執行上述測試、建置 `linux/amd64` 映像，驗證 HTTP 登入與資料卷／容器重啟後讀回。結果見該提交的 [Actions](https://github.com/Z3ych1k/Planwise/actions)。歷史 0.1.0 容器驗證為 [run 1](https://github.com/Z3ych1k/Planwise/actions/runs/43186808600)。
- 另以固定 0.2.0 標籤建置舊容器，在獨立臨時卷建立兩個帳號、目標、課程和私人時間，完成 SQLite 備份，再替換為新容器；逐列比對既有帳號、整份行程、session，沿用舊 cookie 登入並測試新邀請註冊。腳本 `nas/check_upgrade.py`；僅操作隨機名稱的 CI 專用卷。是否通過以該提交 Actions 結果為準，本機沒有 Docker engine。

## 瀏覽器實測

0.3.0 使用獨立臨時資料庫，實際完成「原管理員登入 → 第三頁產生邀請碼 → 登出 → 登入頁建立帳號 → 自動登入一般帳號」。一般帳號設定頁保留語言、時間、備份及自己的密碼設定，不顯示邀請碼管理。沒有修改真實管理員密碼或個人行程。

以下七日及離線渲染尺寸為 0.2.0 實測；0.3.0 保留這些版面與對應自動回歸測試：

- 390 × 844：七欄都在時間表可見範圍，`clientWidth=scrollWidth=360`，整頁寬 390。
- 320 × 740：七欄都可見，`clientWidth=scrollWidth=290`，整頁寬 320。
- 點日期變成單日，再切「七日」恢復七欄，沒有橫向捲動。
- 模擬 NAS API 每次卡住 15 秒，冷啟動先顯示 7 份快取任務、唯讀提示及重連按鈕；本機瀏覽器操作量測約 64ms 即可讀到該畫面。這是本機瀏覽器觀察值，不是 Android 真機啟動時間保證。
- NAS APK 改為直接 `loadDataWithBaseURL` 開啟內置頁面，不再 `loadUrl` 等待 NAS HTML 失敗；API 計時器為 8000ms，計時邏輯由客戶端測試驗證。

## APK 與驗證邊界

NAS APK：`hk.planwise.nas`／`0.3.0-nas-preview`／code 3。已完成建置、v2 簽章驗證及 16KB ZIP 對齊檢查，並核對內置介面與來源一致、沿用 0.2.0 簽章。使用 AGP 8.13.0、Gradle 8.14.3、JDK 21、SDK 36。本地 APK 保留此前驗證的 `hk.planwise.app`／`0.5.2-preview`／code 4，本次沒有重建。

尚未連入使用者 fnOS／ZeroTier 或 Android 真機；沒有聲稱已安裝到使用者設備。沒有實作離線寫入、共享表或自動合併衝突。舊版 JSON／資料庫及本地 APK 私有資料不因目錄整理自動刪除。
