# NAS 0.2.0 Preview 驗證紀錄

2026-11-12；使用臨時示例帳號及資料庫，沒有導入個人行程。

## 自動驗證

- Python **92 項通過**：原有排程／Android 內置介面測試、NAS API 測試及新增管理員 CLI 測試。命令：`python -m unittest discover -v`。
- `node --test nas/test_client.cjs`：6 項客戶端測試，驗證冷啟動先顯示快取、離線停用修改、8 秒中止卡住的請求、重連取得新版才開放寫入、手機預設七日／保留單日、首次無快取與損壞快取仍能顯示登入／重連頁。
- 新增 CLI 測試實際呼叫 `nas.manage`：建立管理員只儲存密碼雜湊、密碼不符不建帳號、重設密碼保留原資料並撤銷 session。
- `node --check nas/static/ui.js` 與 `node --check android/runtime/app.js`。
- GitHub Actions 配置檢查兩份 Compose、執行上述測試、建置 `linux/amd64` 映像，驗證 HTTP 登入與資料卷／容器重啟後讀回。結果見該提交的 [Actions](https://github.com/Z3ych1k/Planwise/actions)。歷史 0.1.0 容器驗證為 [run 1](https://github.com/Z3ych1k/Planwise/actions/runs/43186808600)。

## 瀏覽器實測

- 390 × 844：七欄都在時間表可見範圍，`clientWidth=scrollWidth=360`，整頁寬 390。
- 320 × 740：七欄都可見，`clientWidth=scrollWidth=290`，整頁寬 320。
- 點日期變成單日，再切「七日」恢復七欄，沒有橫向捲動。
- 模擬 NAS API 每次卡住 15 秒，冷啟動先顯示 7 份快取任務、唯讀提示及重連按鈕；本機瀏覽器操作量測約 64ms 即可讀到該畫面。這是本機瀏覽器觀察值，不是 Android 真機啟動時間保證。
- NAS APK 改為直接 `loadDataWithBaseURL` 開啟內置頁面，不再 `loadUrl` 等待 NAS HTML 失敗；API 計時器為 8000ms，計時邏輯由客戶端測試驗證。

## APK 與驗證邊界

NAS APK：`hk.planwise.nas`／`0.2.0-nas-preview`／code 2。本地 APK：`hk.planwise.app`／`0.5.2-preview`／code 4。兩者已完成建置、v2 簽章驗證及 16KB ZIP 對齊檢查。使用 AGP 8.13.0、Gradle 8.14.3、JDK 21、SDK 36，發布前另檢查內置來源。

尚未連入使用者 fnOS／ZeroTier 或 Android 真機；沒有聲稱已安裝到使用者設備。沒有實作離線寫入、共享表或自動合併衝突。舊版 JSON／資料庫及本地 APK 私有資料不因目錄整理自動刪除。
