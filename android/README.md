# 留白 Planwise Android 測試版

最新 APK：Releases 中的 `Planwise-0.5.1-preview.apk`，約 38.4 MB。

- App ID：`hk.planwise.app`
- 版本：`0.5.1-preview`，versionCode 3
- Android 7.0 / API 24 起；arm64-v8a、x86_64，沒有 32-bit-only 版本
- compile/target SDK 36，Build Tools 36.0.0
- 原生 WebView + Chaquopy 17.2 + Python 3.14；服務在裝置內的隨機 localhost 埠執行，不需要電腦
- debug 測試金鑰簽署，與 0.4.0 的簽署金鑰相同；WebView debugging 和 Android debuggable 關閉

## 本版內容

包含目前全部 v5.1 網頁功能：工作日／假日重複、香港 2026–2027 公眾假期、長期目標投入填色、完整手機單日／七日總覽、繁／簡／英設定、JSON 導入／導出、固定事項鎖定及單次移除，以及不阻擋操作的前移建議。

第三頁導出時使用 Android 系統保存檔案介面；導入使用系統檔案選擇器，也可貼上 JSON。沒有額外的全碟儲存權限。資料保存到應用私有目錄 `planwise.json`，不使用電腦資料，不自動備份到雲端。升級前建議自行導出；解除安裝或清除資料會移除紀錄。

## 建置

需要 JDK 21、Android SDK Platform 36、Build Tools 36.0.0 及 Python 3.14。本機腳本預設工具鏈目錄 `/private/tmp/planwise-android-toolchain`，結構為 `jdk/Contents/Home`、`sdk`、`gradle`。可用 `PLANWISE_ANDROID_TOOLS` 指向相同結構；`PLANWISE_BUILD_PYTHON` 可指定 Python 3.14 執行檔。

在原始碼根目錄執行：

```sh
bash android/build-apk.sh
```

Gradle wrapper 8.14.3、Android Gradle Plugin 8.13.0。腳本將根目錄的 Python、翻譯 JSON、CSS、JS 複製進 Android 工程；不複製個人紀錄。產物在 `output/android/`。

## 已驗證與待測

- Python 70 項測試及 JavaScript 語法檢查通過。
- Gradle assembleDebug / lint vital 通過。
- APK v2 簽章及 16 KB ZIP 對齊通過，簽署憑證與上一版相同。
- 38 個 ELF 檔案的 LOAD alignment 均至少 16,384 bytes。
- 包內 10 個共用來源檔與本版網頁原始碼逐位元一致，沒有電腦個人 JSON 或備份。
- **未連接 Android 真機或模擬器**。首次啟動、覆蓋安裝保留資料、觸控拖動、檔案選擇／保存和離線重開仍須在裝置驗證；瀏覽器手機尺寸檢查不等於真機測試。

APK SHA-256：

```text
3fca82fd562a239d45ba96bf208fe79517c5471acdca26b70a27c0d9b925dd8a
```
