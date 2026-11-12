# 已有 NAS 的保留資料更新：0.2.0 → 0.3.0

本次需更新 **NAS Docker 程式**。GitHub 上的程式更新不會自動替換已運行的容器。更新完成後，瀏覽器重新整理即可；**NAS APK 需覆蓋安裝 0.3.0**，因為它內置介面以支援快速離線顯示。本地 Android 仍用 0.5.2，無須更新。

資料庫更新只新增 `invitations` 資料表，保留原帳號、密碼雜湊、任務、課程、私人時間、偏好和有效登入狀態。**沿用原專案及原 `/data` 掛載**；不用重建管理員或重新匯入個人 JSON。

## 1. 先確認目前專案和資料位置

在 fnOS Docker 管理介面，打開**原本的 Compose 專案**，記下：

- 專案名稱及原 Compose 內容。
- NAS 對外埠，例如 9473；舊版也可能是 8088。
- 容器掛載到 `/data` 的**實際來源**：資料卷名稱，或你自訂的 NAS 資料夾。

預設資料卷通常是 `planwise-nas_planwise-data`，但 fnOS 的專案名稱可能改變它；以實際掛載為準。不要為這次更新新建另一個 Compose 專案，也不要直接把自訂掛載改回預設值。

NAS 主機終端可以查看（替換實際容器名稱）：

```sh
docker inspect 你的容器名稱 --format '{{index .Config.Labels "com.docker.compose.project"}}'
docker inspect 你的容器名稱 --format '{{json .Mounts}}'
```

第二條輸出中，找 `Destination` 為 `/data` 的一項，記下 `Name`／`Source`。若切換到主機終端更新，須用相同專案名稱；必要時每條 Compose 指令加 `-p 原專案名稱`。不要僅依資料夾名稱猜測。

## 2. 更新前備份，另存到容器外

先暫停所有裝置上的編輯，直到更新完成。以下選一種方法；備份檔名若已存在，改用另一個日期／時間，指令不會覆寫舊備份。

**原 Compose 資料夾內的 NAS 主機終端：**

```sh
docker compose exec planwise python -m nas.manage backup-db /data/before-0.3.0-2026-11-12.sqlite3
docker compose cp planwise:/data/before-0.3.0-2026-11-12.sqlite3 ./before-0.3.0-2026-11-12.sqlite3
```

確認 NAS 資料夾已出現非空的 `.sqlite3` 備份檔，最好再複製一份到電腦。這是完整資料庫備份，包含所有帳號和行程，請妥善保管。

**只用 fnOS 圖形介面：**

1. 打開原容器的互動終端，執行 `python -m nas.manage backup-db /data/before-0.3.0-2026-11-12.sqlite3`。
2. 從容器的檔案／資料卷管理功能，把該備份複製到另一個 NAS 資料夾或電腦。若 GUI 沒有複製功能，在主機終端用 `docker cp 你的容器名稱:/data/before-0.3.0-2026-11-12.sqlite3 ./before-0.3.0-2026-11-12.sqlite3`。

請用上述 SQLite 備份命令，不要在運行中只複製主資料庫檔而漏掉 WAL。第三頁個人 JSON 可以另外匯出，不能代替全部帳號的資料庫備份。

## 3. 更新原有 Compose 專案

### 單檔 Compose：fnOS 圖形介面

在**原專案**編輯 Compose，保留原 `name`、對外埠、環境設定及 `/data` 掛載。只更新以下兩個版本值：

```yaml
build:
  context: "https://github.com/Z3ych1k/Planwise.git#nas-v0.3.0-preview"
  dockerfile: nas/Dockerfile
image: planwise-nas:0.3.0
```

保留這些欄位原本的縮排和位置，不要只貼這一段取代整份 Compose。也可參照 [完整新版 compose.yaml](../compose.yaml) 比對；有自訂埠和掛載時保留你的設定。

保存後對原專案執行**重新建置並啟動／重新部署**，查看建置日誌。這次需從 GitHub、Docker Hub 和 Python 套件來源下載。單純按「重啟舊容器」不會取得新程式；只拉取映像也不適用，這個 Compose 使用原始碼建置。

### 單檔 Compose：NAS 主機終端

在原 Compose 資料夾，修改上述版本值後執行：

```sh
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail 80 planwise
```

不用先執行 `down`。Compose 會重建程式容器並沿用原掛載，服務會短暫中斷；裝置可在恢復後重新整理。

### 完整原始碼部署包

下載 0.3.0 完整原始碼，更新原部署目錄內的程式，保留自己的 Compose 設定、專案名稱及掛載。原本使用 `nas/compose.yaml` 的，以上每一條 Compose 指令都要加 `-f nas/compose.yaml`，例如：

```sh
docker compose -f nas/compose.yaml up -d --build
```

不要只換 `nas/compose.yaml` 卻留下舊程式；此模式的建置來源是本機完整原始碼。

## 4. 驗證，然後更新 NAS APK

1. 打開 `http://NAS的IP:原埠/healthz`，應有 `"version":"0.3.0"` 和 `"ok":true`。
2. 網頁重新整理，登入**原管理員帳號及原密碼**，核對原有行程。
3. 第三頁出現「邀請碼管理」；產生單次、7 天有效的邀請碼。新使用者由登入頁「以邀請碼建立帳號」，自選密碼；不影響其他人的表。
4. 手機下載新版 `Planwise-NAS-0.3.0-preview.apk`，直接覆蓋安裝同一應用，**不要先卸載**，保留 NAS 地址與本機快取。發布版沿用舊簽章。舊 0.2.0 NAS APK 仍可登入舊帳號，但看不到新註冊／邀請碼介面。

管理員建立和忘記密碼的方式沿用 [安裝教程第三步](INSTALL.md#第三步建立管理員與自己設定的密碼)，沒有新預設密碼。若原帳號突然找不到或變空白，先檢查 `/data` 是否仍掛到第一步記錄的來源，保留舊資料卷，不要立刻重建帳號。

## 必須保留的項目

不要執行 `docker compose down -v`、刪除原資料卷或勾選「刪除資料」；不要把備份覆蓋到正在運行的資料庫。若需回復備份，先停服務、保留當前資料副本，再在獨立資料卷驗證備份，避免覆蓋更新後新增的資料。

參考 Docker 官方：[up 重新建立容器時保留掛載資料卷](https://docs.docker.com/reference/cli/docker/compose/up/)、[專案名稱優先次序](https://docs.docker.com/compose/how-tos/project-name/)、[down -v 會移除資料卷](https://docs.docker.com/reference/cli/docker/compose/down/)。尚未在你的 fnOS 主機上代為更新。
