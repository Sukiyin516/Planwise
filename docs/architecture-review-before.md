# Planwise 第一轮重构前质量体检

- 日期：2026-11-13；范围：`D:\eduhk_AIET\INT6181\group\Planwise` 当前工作树。
- 方法：按 project-quality-review 的架构、需求、质量属性、坏味道、结构、文档和演化清单进行静态审查。未运行测试、应用、构建或 skill 扫描脚本；以下度量为文件清单、文本搜索和源码人工核对，运行属性均标明推断。
- 评级口径：A 健康可长期演进；B 债务可控；C 需要专项治理；D 有阻碍演进的结构性问题。

## 总体评级：C

共享排程规则已有模块边界，NAS 也有 `domain.py` 与 `database.py`，因此不是整体失序。但存在一处明确的 Python 循环依赖；NAS Web 的单个应用工厂承担过多职责；本地 Android 与 NAS 的动作流程分叉。组员 2 的重构应围绕这些具体边界展开，避免重写功能。

| 维度 | 评级 | 依据 |
| --- | --- | --- |
| 架构设计 | C | `timetable.py:4` → `events.py:85` → `timetable.py`；`nas/application.py:30-344` 的大闭包 |
| 需求实现度 | B（静态） | README 主要能力可追踪到 `nas/domain.py`、`timetable.py`、`android/runtime/main.py`；未作运行验收 |
| 代码坏味道 | C | 大应用工厂、两端动作编排重复、NAS 前端单文件承担多种职责 |
| 目录结构 | B | NAS、Android、共享规则大体分区；根目录测试相互借用夹具 |
| 文档化 | B | README 与 NAS 安装说明完整；根 `SPEC.md`/`TESTING.md` 的早期版本命令已过期 |

## 项目画像与静态度量

根目录 `planner.py`、`timetable.py`、`events.py`、`storage.py`、`holidays.py`、`i18n.py` 是共享规则与 JSON 兼容层。NAS 使用 Flask、SQLite、原生 JS（`nas/application.py`、`nas/domain.py`、`nas/database.py`、`nas/static/ui.js`），本地 Android 使用 Python loopback HTTP 与 WebView（`android/runtime/main.py`），另有 NAS Android 外壳。生产依赖仅 NAS 的 Flask 与 gunicorn（`nas/requirements.txt:1-2`）。静态清单约 19 个非测试 Python/JS/Java 源文件；8 个 Python 测试文件、104 个 `test_` 方法，另有 `nas/test_client.cjs`。README 给出 unittest、Node 命令（`README.md:33-39`），CI 执行它们（`.github/workflows/nas-check.yml:18-22`）。本轮测试健康度为**未运行**，通过/失败/跳过数未知；历史 `TESTING.md` 不能当作本次结果。

手工确认的内部依赖环只有 `timetable → events → timetable`；这里的第二条边在函数内局部导入，故启动失败不能由此推断。`nas/domain.py` 静态导入五个共享规则模块（`nas/domain.py:5-10`）；NAS API 还直接导入 `timetable.initialize`（`nas/application.py:17`），表示应用规则仍有一部分留在接口层。Git 历史中 `README.md` 与 `nas/compose.yaml` 各出现 4 次，NAS UI、Android 打包脚本和 CI 各约 3 次；提交数有限，不能据此断言长期腐蚀。

## 质量属性与关键场景

| 属性 | 静态判断 | 证据及验证方法 |
| --- | --- | --- |
| 可维护性 | 差 | NAS 动作规则在 `nas/domain.py:13-71`，版本、初始化、保存又在 `nas/application.py:72-88,245-275`；本地动作在 `android/runtime/main.py:270-339`。改同类动作需检查两端。 |
| 可重用性 | 中 | 共享排程可直接调用；`planner.mutate`、`events.save_event` 接收 HTTP 风格字段列表（`planner.py:54-58`、`events.py:53-55`）。 |
| 可移植/可集成性 | 中 | 两端复用共享规则；新增共享模块须同步 `nas/Dockerfile:9-10` 与 `android/build-apk.sh:10-14`。 |
| 可测试性 | 中 | 规则测试可不启动服务；NAS API 用 Flask 配置时钟 `nas/application.py:34,42-44`；本地动作测试需模拟 Handler（`test_schedule_changes.py:22-33`）。 |
| 性能 | 待测（推断） | `nas/domain.py:74-92` 构造完整周视图，`timetable.py:51-60` 展开事项；以 500 任务/事项上限做隔离计时。 |
| 可靠性 | 有支撑，未实测 | NAS 事务 `nas/database.py:63-74`、版本/幂等 `nas/application.py:250-275`；本地原子替换 `storage.py:148-162`。模拟失败与并发再验。 |
| 安全性 | 有支撑，未实测 | NAS 同源/CSRF `nas/application.py:57-64,90-102`；密码 scrypt `nas/database.py:76-90`。本轮不作渗透测试。 |
| 用户/运维可用性 | 中（推断） | NAS 有 `/healthz`（`nas/application.py:135-139`）、离线只读（`nas/static/ui.js:82-125`）；Android 真机仍待验收（`android/README.md`）。 |

关键场景：S1 新增一种事项动作时，NAS 与本地 Android 都保持同样的规则（重要性高、难度中；当前动作编排分叉）。S2 NAS 两设备同时更新，旧版本被拒绝且不丢数据（高、中；`nas/application.py:254-275` 有机制，需运行验收）。S3 重构后 APK 与 Docker 仍包含全部共享模块（高、中；两个显式清单）。S4 大量重复事项的七日视图可接受（中、中；尚无本轮耗时数据）。敏感点是共享 JSON schema、时间解析错误文本、HTTP 字段与提议版本；权衡点是两端保留不同存储/认证方式以适应离线本地与 NAS 同步，属于 README 已说明的有意识选择。

## 需求实现度（静态）

| 声明来源 | 状态 | 证据与限度 |
| --- | --- | --- |
| README：七日 DDL、固定/私人时间、前移建议 | 有实现路径，未运行 | `timetable.py:51-168`、`nas/domain.py:13-92`、`android/runtime/main.py:270-339` |
| README：NAS 每帐号隔离、跨装置同步、离线只读 | 有实现路径，未运行 | `nas/database.py:31-47`、`nas/application.py:72-88,245-275`、`nas/static/ui.js:82-125` |
| README：本地 Android 独立 JSON | 有实现路径，未运行 | `android/runtime/main.py:373-381`、`storage.py:136-162` |
| README：邀请码注册、管理权限 | 有实现路径，未运行 | `nas/application.py:169-238`、`nas/database.py:48-53` |
| SPEC R9：目标空档建议 | 历史规格待澄清 | `planner.py:48-51` 有 `suggestions`，当前 NAS `view` 不调用它（`nas/domain.py:74-92`）；README 仅称“提醒”。不要仅凭旧规格修改当前行为。 |

## P0：结构性问题（必改）

**P0-1 循环依赖。** `timetable.py:4` 导入 `events.event_cells`；`events.py:85` 在 `move_occurrence` 内反向导入 `timetable.clock`。违反架构清单“依赖单向”判据，事件规则不能独立于上层排程时间解析。将共用解析逻辑放到叶子模块，旧函数保留原错误消息与导入路径，令事件不再依赖排程。局部导入使它不是已证实的启动故障。

## P1：维护性问题（本轮重构应处理）

**P1-1 NAS 应用工厂职责过宽。** `nas/application.py:30-344` 单个 `create_app` 闭包含认证、限流、邀请码、快照初始化、版本与幂等、备份、离线 HTML 拼装及路由；`snapshot` 在 `72-88` 读取时可能写库。按长函数/职责混杂清单，此处改动影响面大。先把快照及动作提交编排抽到独立应用模块，认证路由可保持在 Flask 适配层，数据库 SQL 逐步归入 `Database` 的窄方法；保留事务与响应格式。

**P1-2 两个入口对同一业务动作分别编排。** NAS 在 `nas/domain.py:35-68` 调用共享 `mutate`/`refresh`，本地 Android 在 `android/runtime/main.py:288-339` 另有同类分支；进度记录还分别补写 `work_log[-1]`（`nas/domain.py:62-65`；`android/runtime/main.py:328-333`）。这是可证实的散落功能，修改规则易漏一端。逐个提取纯用例函数供两端调用，保留 NAS 版本事务与 Android 文件保存边界。不要强行统一不同产品的账号和离线策略。

**P1-3 分发清单和 CI 范围约束重构。** `nas/Dockerfile:9-10`、`android/build-apk.sh:10-14` 显式列出文件。`.github/workflows/nas-check.yml:5-7` 的 PR path 仅含 `nas/**` 等，单独改根共享模块时可能不触发这套 CI（推断；用针对根模块的 PR 验证）。重构每新增模块同步清单，并让共享规则路径触发检查。

**P1-4 NAS 前端职责集中。** `nas/static/ui.js:82-150` 管缓存、同步和请求；`152-200` 管认证/邀请；`200-281` 管页面与表单；`281-348` 管事件和拖动。约 348 行不满足“500 行上帝模块”硬阈值，故不判 God Module；但单文件多状态与多职责增加维护成本。待 Python 边界稳定后，按网络/状态/视图拆为少量模块，注意 APK 内置资源同步。此项属于后续重构而非当前阻塞。

## P2：可选优化

- `storage.py:25-133` 的 `migrate` 较长，但职责集中在旧 JSON schema 校验/迁移。先保留入口；仅在夹具足够时拆内部校验函数。
- 根测试互相导入夹具（`test_preferences.py:15-16`、`test_schedule_changes.py:16-18`）。可在后续迁至 `tests/fixtures.py`，先锁定发现命令。
- 旧 `TESTING.md:8,66,87` 仍用 `planner_demo` 路径；README 已给当前命令。更新历史文档时标明“历史记录”，避免误用。
- `planner.py:26-51` 的旧 `schedule`/`suggestions` 有测试引用；不能仅因当前 NAS 未调用就删除。

## SOLID 与设计判断

SRP 最适用：分开接口适配、应用动作、持久化和视图。DIP 只在应用用例对时钟/存储有真实替换需求时采用轻量依赖注入；现有 Flask 配置时钟已是可用做法。OCP 通过集中动作分派减轻多处修改即可，无需插件框架。当前没有业务继承树，LSP 无违规证据；ISP 对单一 JSON/SQLite 实现也无需预设大型接口。`nas.database.Database` 已合理封装连接、事务和帐号操作；HTML 渲染、时间换算、排程算法继续用普通函数。不要把 JSON `Task`/`Event` 全部改造成类，避免破坏 schema 与两端兼容。

## 技术债、Quick Wins 与顺序

| 类型 | 债务 | 优先级 | 时机 |
| --- | --- | --- | --- |
| 设计债 | 事件↔排程环 | P0 | 首先 |
| 设计/代码债 | NAS 应用工厂与两端动作编排 | P1 | 核心重构 |
| 测试/分发债 | 根模块改动 CI 触发与双清单 | P1 | 每次迁移同步 |
| 文档债 | 旧路径和历史规格 | P2 | 收尾 |

Quick wins：先画定两端动作对照表；抽出共用时间解析；记录 `nas/Dockerfile` 与 Android 文件清单；为新模块写清单/CI 守护；标注 `TESTING.md` 的历史命令。重构顺序为 P0 环 → P1 共享用例边界与 NAS 应用工厂 → P1 分发/测试门禁 → P2 前端与文档。腐蚀最小化靠每次 PR 检查两端行为，预防靠依赖方向与双分发检查，修补靠重构后再比较依赖图；本轮没有足够历史数据断言腐蚀趋势。
