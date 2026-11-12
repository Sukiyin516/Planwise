# fnOS 安裝教程與管理員密碼

適用 fnOS／x86-64／Docker Compose v2。預設埠 **9473**，網頁和 NAS APK 使用同一 NAS 地址。外出先連 ZeroTier，再使用可到達的 NAS IP。

**已經啟動本項目的 Docker 容器：直接看第三步「建立管理員」。**

## 第一步：取得 Compose

開啟 [根目錄 compose.yaml](../compose.yaml)，點 **Raw／原始檔**複製完整內容，或另存為 `compose.yaml`。不要存成 HTML 或 `compose.yaml.txt`。

| 檔案 | 用途 |
| --- | --- |
| 根目錄 `compose.yaml` | 單檔部署；建置時從 GitHub 的固定 `nas-v0.2.0-preview` 標籤取得程式，不需其他檔案 |
| `nas/compose.yaml` | 完整原始碼部署包使用，依賴整個專案，不能只拿這一份 |

第一次建置需要 NAS 能連 GitHub、Docker Hub 和 Python 套件來源。使用中的終端只需連到 NAS。

## 第二步：啟動服務

### A. fnOS Docker 圖形介面

選單名稱可能隨 fnOS 版本略有不同，操作對象是 Docker 的 Compose 專案及其容器。

1. 開啟 **Docker → Compose／專案 → 新增**。
2. 專案名稱可用 `planwise-nas`，選擇保存專案設定的資料夾。
3. 貼上第一步根目錄 Compose 的**全部內容**，或選擇你保存的檔案。
4. 啟動／建置。首次需下載映像和套件；查看建置日誌，等待容器進入「執行中／健康」。
5. 瀏覽器開啟 `http://NAS的IP:9473/`。例如 NAS 為 `192.168.1.100`，就是 `http://192.168.1.100:9473/`。

能看到登入畫面代表服務已啟動，**不代表帳號已建立**。

### B. NAS 主機終端／SSH，單檔部署

把根目錄 Compose 放入你選好的 NAS 資料夾，`cd` 到該資料夾，使用有 Docker 權限的 NAS 終端執行：

```sh
docker compose up -d --build
docker compose ps
docker compose logs --tail 80 planwise
```

若沒有 Docker 權限，使用 NAS 管理員終端，或依原本管理方式在指令前加 `sudo`。

### C. 完整原始碼部署包

完整解壓，`cd` 到含 `nas/` 的專案根目錄：

```sh
docker compose -f nas/compose.yaml up -d --build
docker compose -f nas/compose.yaml ps
```

之後也要沿用相同的 `-f nas/compose.yaml`。以下預設以根目錄 Compose 為主。

## 第三步：建立管理員與自己設定的密碼

**沒有預設帳號／密碼。密碼不寫入 Compose、GitHub 或 APK，由你在終端自行設定。**

### 在 fnOS 圖形介面操作

1. 在容器清單找到本專案的 `planwise` 容器，進入 **終端／執行命令／Console**。
2. 開啟**互動／TTY 終端**；若需選 shell，填 `/bin/sh`。
3. 在**容器裡面**執行：

```sh
python -m nas.manage create-user admin --admin
```

4. 分別輸入你自己的新密碼，再按 Enter：

```text
New password (12+ characters):
Repeat password:
```

密碼長度 **12–200 字元**，兩次需相同。輸入時**不顯示字元或星號**是正常的；不用把密碼寫入指令，也不要把上面提示文字當成密碼。

5. 顯示 `Account updated. Other plans were not changed.` 即成功。
6. 回網頁，以帳號 **`admin`** 和你剛才設定的密碼登入。

`admin` 是上述指令選用的帳號名，可換成自己的名稱（3–40 個英文字母、數字、點、底線或連字號）。它與 fnOS、ZeroTier、GitHub 的帳號和密碼獨立。

### 在 NAS 主機終端操作

尚未進入容器的 NAS SSH／終端，執行：

```sh
docker compose exec planwise python -m nas.manage create-user admin --admin
```

方法 C 則執行：

```sh
docker compose -f nas/compose.yaml exec planwise python -m nas.manage create-user admin --admin
```

不在 Compose 資料夾，可先 `docker ps` 查看容器名稱，再用：

```sh
docker exec -it 你的容器名稱 python -m nas.manage create-user admin --admin
```

替換實際容器名稱。以上為替代做法，只做適合你的一種。**容器內直接執行 Python；NAS 主機才執行 Docker 指令。**

### 已建立帳號／忘記密碼

`Username already exists.` 表示帳號已有，重複建立不會覆寫它。忘記密碼時，在容器互動終端執行：

```sh
python -m nas.manage reset-password admin
```

NAS 主機終端則是：

```sh
docker compose exec planwise python -m nas.manage reset-password admin
```

再輸入兩次新密碼。重設會登出該帳號所有裝置，**保留行程**。已登入也可在第三頁「帳號與安全」改密碼。

## 第四步：組員、手機及舊資料

- 管理員登入後，第三頁可建立組員帳號；每人獨立空白表。組員可自行改密碼，管理員網頁不提供查看他人行程。
- 電腦／手機瀏覽器用相同 NAS 地址、相同帳號，即使用同一張表。
- **NAS APK** 首次輸入 `http://NAS的IP:9473` 後登入；外出先連 ZeroTier，可使用 NAS 的 ZeroTier IP。第三頁底部可改 NAS 地址。
- **本地 Android APK** 是另一個應用，不需要 NAS，與 NAS 表不自動同步。
- 舊版本第三頁匯出 JSON，再到 NAS 版第三頁匯入。只取代當前帳號，伺服器保留匯入前備份。
- NAS APK 立即顯示內置介面與快取，背景 API 最多等待 8 秒。離線僅查看；沒有快取的首次使用者會看到登入／重連畫面，需要連線才能取得資料。

## 第五步：端口、升級與備份

`9473:8080` 左邊 **9473** 是 NAS 對外埠，右邊 **8080** 是容器內埠。若 9473 被占用，可改左邊，網頁／APK 地址也要改。

舊部署若仍用 8088，可以繼續沿用舊映射；以你 Compose 左邊實際的埠為準。

資料在 named volume 對應的 `/data`。**升級沿用原專案名稱和資料卷**；另一個專案可能得到空白卷，看似帳號消失。請勿執行 `docker compose down -v` 或刪除資料卷。

日常第三頁匯出個人 JSON。完整資料庫備份（換成當天日期，不能覆寫同名檔）：

```sh
docker compose exec planwise python -m nas.manage backup-db /data/backup-2026-11-12.sqlite3
docker compose cp planwise:/data/backup-2026-11-12.sqlite3 ./backup-2026-11-12.sqlite3
```

單檔部署更新 Compose 版本後，在原專案重新建置：

```sh
docker compose up -d --build
```

方法 C 先更新完整原始碼，再 `docker compose -f nas/compose.yaml up -d --build`。從 GUI 改用終端、或兩份 Compose 互換前，先核對現有容器的專案名稱與掛載資料卷。

## 常見問題

| 情況 | 處理 |
| --- | --- |
| 從未設密碼，無法登入 | 第三步建立管理員，沒有預設密碼 |
| 密碼輸入沒反應 | 不顯示字元是正常的；確認互動／TTY 模式，輸入後 Enter |
| 容器內 `docker: not found` | 已在容器內，直接執行 `python -m nas.manage ...` |
| 找不到 Compose | 主機終端 `cd` 到檔案資料夾，或指定正確 `-f` |
| 網頁打不開 | 查容器健康、NAS IP、映射埠、局域網／ZeroTier 連線 |
| 建置卡在下載 | 查 NAS 到 GitHub／Docker Hub／Python 套件來源的連線；完整原始碼部署可減少建置對 GitHub 的依賴 |
| 升級後空白 | 查專案名稱、資料卷和登入帳號，先保留舊卷 |

本教程未宣稱已在你的 fnOS GUI 和 ZeroTier 網路實機安裝。參考：[Compose 互動終端](https://docs.docker.com/reference/cli/docker/compose/exec/)、[專案名稱與隔離](https://docs.docker.com/compose/how-tos/project-name/)。
