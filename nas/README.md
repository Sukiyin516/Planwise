# 留白 Planwise NAS 0.1.0 Preview

Python 排程後端 + 獨立 HTML/CSS/JavaScript 前端，部署於 fnOS x86-64 Docker。電腦、手機瀏覽器和 NAS APK 連接同一個服務。

- 每個帳號獨立一張表，同帳號跨裝置共用資料；沒有共享表或成員協作權限。
- 以版本號阻止舊畫面覆蓋新資料；15 秒輪詢及回到頁面時檢查。編輯中的輸入不會被輪詢覆蓋。
- 離線只查看上次快取，不接受修改、不排隊同步；重新連線先讀取最新版。
- 原有半小時排程、手動拖動、固定事項、私人時間、只取消一次、可選前移、長期目標填色、三種語言及 JSON 匯入匯出保留。
- `main.py`、原離線 APK 及組員分支不受此版影響。新套件為 `hk.planwise.nas`。

## fnOS 部署

需要 Docker Engine 與 Compose v2。下載**整個 feature/nas-server 分支**的 ZIP 後解壓；保留根目錄的 Python 模組，不能只複製 `nas/`。

在專案根目錄執行：

```sh
docker compose -f nas/compose.yaml up -d --build
docker compose -f nas/compose.yaml exec planwise python -m nas.manage create-user yourname --admin
```

終端會要求輸入並確認密碼（12–200 字元），不顯示密碼；**沒有預設帳號或密碼**。帳號使用 3–40 個英文字母、數字、點、底線或連字號。隨後開啟 `http://NAS的局域網IP:8088/`。管理員可以在第三頁建立組員帳號，每個新帳號均為獨立空白表。

外出先連 ZeroTier，再使用 `http://NAS的ZeroTierIP:8088/`；本版不需要路由器端口轉發或公開域名。Compose 預設監聽 NAS 所有介面；可在專案根目錄 `.env` 設定 `PLANWISE_BIND_IP=NAS的指定IP`，或 `PLANWISE_PORT=8088`。只綁局域網 IP 時，請讓 VPN 使用者能路由至該 IP；直接使用 ZeroTier IP 則需包含該介面。

原有本機版資料：先從原版第三頁匯出 JSON，再登入 NAS 版第三頁匯入。匯入只取代目前帳號，會保留最近 10 份匯入前備份於資料庫，不會複製其他帳號或登入憑證。

## 持久化、升級及備份

資料庫在容器 `/data/planwise.sqlite3`，由 `planwise-data` named volume 保存。SQLite 只由 NAS 服務存取；裝置使用 API，不直接經 SMB 掛載資料庫。兩個 Gunicorn worker 的版本檢查及儲存都在 SQLite 交易內完成。

日常匯出用第三頁的 JSON，僅包含自己的表。完整帳號、密碼雜湊及全部資料的管理員備份：

```sh
docker compose -f nas/compose.yaml exec planwise python -m nas.manage backup-db /data/backup-2026-11-12.sqlite3
docker compose -f nas/compose.yaml cp planwise:/data/backup-2026-11-12.sqlite3 ./backup-2026-11-12.sqlite3
```

使用 SQLite backup API 取得一致快照，請勿直接複製運作中的主檔而漏掉 WAL。備份檔包含所有帳號資料，需自行妥善保存。CLI 不覆寫已有備份檔。可用新日期備份，確認成功後自行處理舊備份。

更新版本：先備份，再在原專案位置更新程式並再次執行 `up -d --build`。正常 `docker compose down` 保留資料；**不要使用 `down -v`，它會刪除資料卷**。此預覽版沒有跨大版本的自動資料庫遷移工具。

忘記密碼（需 NAS Docker 管理權限）：

```sh
docker compose -f nas/compose.yaml exec planwise python -m nas.manage reset-password yourname
```

修改或重設密碼後，該帳號所有裝置都需重新登入。管理員介面不提供查看別人的行程；NAS 主機管理者可讀取資料庫，並非端對端加密。

## 同步與離線行為

每次儲存攜帶整張表的版本號，過期會回傳 HTTP 409，保留輸入並提示先複製輸入、重新整理及檢查。不同裝置修改不同任務也會保守地視為同一張表的衝突，首版不自動合併。每次提交亦有唯一 request ID，重送同一次請求不會重複記錄投入。網路在儲存中斷開時，介面會明確顯示「尚未確認」，重新連線後需檢查最新資料。

最近快照儲存在當前網站的 localStorage，**不含密碼、session cookie 或 CSRF token**。同一裝置的登出會清除快照，切換帳號／線上遇到登入失效也會清除。共用裝置請用完登出；瀏覽器無法遠端刪除一台完全離線裝置已快取的資料。

- **局域網 HTTP 瀏覽器**：頁面仍開著時，斷線可查看；關閉後重新離線開啟不保證可用。先在第三頁下載「唯讀離線快照」HTML，用瀏覽器開啟即可獨立查看，無法更新伺服器。快照是匯出檔，登出不會刪除已下載的檔案。
- **HTTPS 或 localhost 瀏覽器**：可使用 Service Worker 快取介面，帳號 API 永不被 Service Worker 快取。本 Compose 提供 HTTP；如自行加設 HTTPS，還須正確設定 WSGI scheme、Host 及 `PLANWISE_COOKIE_SECURE=1`。本版未附反向代理配置，也不盲目信任轉送標頭。
- **NAS APK**：內置介面殼，斷線重新開啟時可讀取最近同站快照；首次登入必須連線。重連後取得最新資料才可修改。切換 NAS 地址會清除客戶端舊 cookies 與快取。

帳號 session 有效期 7 天；HttpOnly / SameSite=Strict cookies、CSRF 檢查、同來源驗證及登入速率限制。HTTP 模式 cookie 不加 Secure 以便局域網使用；僅在可信局域網／ZeroTier 網路使用。此版不提供公開註冊、郵件找回、社交登入、離線寫入或即時 WebSocket 同步。

## NAS Android 客戶端

與舊本機版並存，不含 Python 排程執行環境；需要 NAS 服務。首次啟動輸入 `http://NAS的IP:8088`，或 ZeroTier IP。從設定頁底部可改地址。要求 Android 8+ 及可更新的現代 Android System WebView。

使用 JDK 17／21、Android SDK platform 36、build-tools 36.0.0 建置：

```sh
export JAVA_HOME=/path/to/jdk
export ANDROID_HOME=/path/to/android-sdk
bash nas/android/build-apk.sh
```

沿用根目錄 `android/` 的 Gradle wrapper，輸出 `output/nas/Planwise-NAS-0.1.0-preview.apk`。預覽 APK 使用本機 debug 簽章，正式持續升級前需固定並備份專用簽章；不將簽章私鑰提交 GitHub。

## 開發與驗證

```sh
python3 -m venv .venv
.venv/bin/pip install -r nas/requirements.txt
.venv/bin/python -m unittest discover -v
node --check nas/static/ui.js
PLANWISE_DATABASE=./development.sqlite3 .venv/bin/python -m nas.manage create-user dev --admin
PLANWISE_DATABASE=./development.sqlite3 .venv/bin/gunicorn --bind 127.0.0.1:8770 'nas.application:create_app()'
```

前端：`nas/static/`；JSON API：`nas/application.py`；帳號與儲存：`nas/database.py`；排程介接：`nas/domain.py`；帳號 CLI：`nas/manage.py`。核心排程直接沿用根目錄模組，沒有另抄一套規則。API 固定同來源 `/api/*`，不開跨來源 CORS。

容量首版限制：每帳號 500 個任務、500 個事項系列、5000 筆投入，單次請求 8 MB，儲存狀態 4 MB。適合個人／小組 NAS 自用，未聲稱可承載大型公開服務。
