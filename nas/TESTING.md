# NAS 0.1.0 Preview 驗證紀錄

日期：2026-11-12。測試只使用臨時示例帳號和臨時資料庫，沒有導入個人行程。

## 自動驗證

- Python 3.14 本機：`python -m unittest discover -q`，**89 項通過**（原有 70 項 + NAS API 19 項）。
- JavaScript：`node --check nas/static/ui.js` 通過。
- GitHub Actions 的 Python 3.12／Linux：同一套測試通過。
- Compose：GitHub runner 實際執行 `docker compose -f nas/compose.yaml config --quiet` 通過。
- `linux/amd64` Docker 映像實際建置成功；以 read-only rootfs、tmpfs 及 named volume 啟動 Gunicorn，health check、建立帳號、HTTP 登入、讀取行程及容器重啟後沿用 session 和資料通過。
- 初次容器驗證：[NAS preview checks run 1](https://github.com/Z3ych1k/Planwise/actions/runs/43186808600)。

NAS API 測試涵蓋：不同帳號的行程／匯出隔離、同帳號兩個 session、舊版本拒絕覆蓋、同時寫入只有一方成功、CSRF／跨來源拒絕、未登入拒絕、同 request ID 不重複記錄投入、錯誤匯入回滾、匯入前備份、長期目標投入比例、半小時限制、固定事項禁止移動、只取消一次、手動任務移動及重啟後讀回、前移建議不阻止記錄、修改密碼撤銷所有 session、管理員建立獨立帳號、登入限流、離線匯出不含 CSRF／不執行任務標題 HTML、香港時區、語言／工作日及舊版可用時段切換。

## 瀏覽器操作

- 臨時 demo 帳號登入；繁體中文設定切換英文後由 NAS 儲存，重新載入保留。
- 手機 390 × 844 視口：預設單日；時間軸涵蓋 00:00–24:00；DOM 量測頁面寬度為 390，沒有整頁水平溢出。
- 點長期目標圓點，從圓點位置展開互動氣泡；沒有右側抽屜。
- 第三頁下載唯讀離線 HTML 成功。
- 停止本機 Gunicorn：頁面保留行程，儲存／匯入／帳號操作停用；重新啟動後輪詢成功讀回資料並解除唯讀。
- 瀏覽器錯誤紀錄檢查沒有 JavaScript error。

## Android

- AGP 8.13.0 / Gradle 8.14.3 / JDK 21 / SDK 36：`assembleDebug` 成功，包含最新靜態介面資產。
- `apksigner verify --verbose` 通過（v2），`zipalign -c -P 16 4` 通過。
- 套件 `hk.planwise.nas`，版本 `0.1.0-nas-preview` / versionCode 1；原離線 APK 的套件和程式沒有修改。
- 尚未在 Android 真機驗證輸入 NAS 地址、冷啟動離線快取、系統檔案選擇器及匯入匯出；需部署後驗收。

## 驗證邊界

此處的 Docker 驗證在 GitHub Linux runner 完成；尚未連入使用者 fnOS NAS 或 ZeroTier 網路，不代表已安裝／部署到使用者設備。沒有大型負載測試，也沒有實作離線寫入、共享表或自動合併衝突。
