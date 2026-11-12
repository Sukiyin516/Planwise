# 本地 Android 0.5.2 Preview

`hk.planwise.app`／versionCode 4，Android 7+，arm64-v8a 及 x86_64。與 `hk.planwise.nas` 是不同應用，可並存。

此版完全本地使用，不需要 NAS 或網絡；資料在應用私有目錄 `planwise.json`，不與 NAS 自動同步。第三頁可經 Android 系統檔案介面匯入／匯出 JSON。相同套件及簽章可覆蓋升級；移除應用或清除資料會刪除本機紀錄，請先匯出備份。

0.5.2 改為預設七日總覽，手機七欄適應畫面，點日期看完整單日。啟動時顯示本地載入提示。內置 UI 與 loopback server 在 `android/runtime/`，已移除 Mac／Windows 桌面啟動器、獨立網頁命令與分享包工具。

## 建置

需要 JDK 21、Android SDK Platform 36／Build Tools 36.0.0、Python 3.14。設定 `JAVA_HOME`、`ANDROID_HOME`，可選 `GRADLE_USER_HOME` 及 `PLANWISE_BUILD_PYTHON`：

```sh
bash android/build-apk.sh
```

未設定環境變數時，腳本仍可使用 `PLANWISE_ANDROID_TOOLS` 的舊工具鏈目錄。Gradle 8.14.3／AGP 8.13.0／Chaquopy 17.2。共用根目錄 Python 模組及翻譯 JSON、`android/runtime/` 的三個 UI 檔案複製入 APK，不包含個人資料。輸出 `output/android/Planwise-Local-0.5.2-preview.apk`。

預覽版使用本機 debug 簽章；需要相同金鑰才能保留資料覆蓋升級，私鑰不提交 GitHub。Android 真機觸控、覆蓋安裝保留資料及檔案選擇器仍需實機驗收；瀏覽器尺寸驗證不等於真機測試。
