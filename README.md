# 留白 Planwise

安排大學生的 DDL，保留課程、私人時間與長期目標。以半小時為單位，不使用 AI。

| 使用方式 | 資料與連線 | 安裝 |
| --- | --- | --- |
| NAS 網頁＋NAS APK 0.2.0 Preview | NAS 上每帳號一張表，同帳號跨裝置同步；離線唯讀 | [詳細教程與管理員密碼設定](nas/INSTALL.md) |
| 本地 Android 0.5.2 Preview | 手機內獨立 JSON，不需要 NAS 或網絡 | [本地 Android 說明](android/README.md) |

原 Mac／Windows 本地網頁版、桌面啟動器及分享工具已移除。Android 需要的內置介面移至 `android/runtime/`，只作 APK 執行環境。NAS 網頁版繼續提供服務。

## NAS 入口

- **[直接查看／複製 Compose](compose.yaml)**：只取這一個檔案即可在 fnOS 建置；預設網址 `http://NAS的IP:9473/`。
- **[安裝教程](nas/INSTALL.md)**：fnOS 圖形介面、終端部署、管理員帳號與密碼、重設密碼、升級與備份。
- **[版本下載](https://github.com/Z3ych1k/Planwise/releases/tag/nas-v0.2.0-preview)**：部署包、NAS APK、本地 APK。
- [NAS 說明與驗證](nas/README.md)。版本在 `feature/nas-server`，組員 fork 分支未改動。

已啟動容器但未設帳號：在**容器互動終端**執行：

```sh
python -m nas.manage create-user admin --admin
```

按提示輸入兩次**自己設定、至少 12 字元**的密碼。不顯示字元或星號是正常的。沒有預設密碼，也不是 fnOS 密碼。已存在帳號請看教程中的 `reset-password`。

## 介面與開發

期限優先，同期限再看重要性；課程、固定事項及私人時間先扣除。長期目標只提醒，圓點隨投入填滿。提前完成後先保留原安排，前移僅作建議。

重複事項、香港 2026–2027 假日、固定事項單次取消、任務拖動、繁／簡／英文及 JSON 匯入匯出均保留。手機預設一次看全七天；點日期看單日，點任務看氣泡詳情。

```sh
python -m pip install -r nas/requirements.txt
python -m unittest discover -v
node --check nas/static/ui.js
node --test nas/test_client.cjs
node --check android/runtime/app.js
```

根目錄 Python 模組為共用規則；NAS API 與前端在 `nas/`，本地 Android 在 `android/`，NAS Android 在 `nas/android/`。歷史規格及審查紀錄作課程開發記錄保留，當前安裝方法以本頁和安裝教程為準。
