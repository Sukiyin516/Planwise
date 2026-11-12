# Planwise 重构计划（组员 2，尚未执行）

依据 [第一轮体检](architecture-review-before.md)。目标是减少循环与重复编排，保持 NAS、本地 Android 的 UI、接口、JSON 格式及现有行为。此文档只列计划，不表示已获准重构或运行测试。

## 目标目录树

首轮保留根共享模块和现有入口，避免一次性移动所有导入。新增文件仅在实施时创建。

```text
Planwise/
├── planner.py / timetable.py / events.py / storage.py / holidays.py / i18n.py
├── time_slots.py                 # 新：共用半小时时间解析（普通函数）
├── plan_actions.py               # 新：NAS/本地共用的任务、事项、进度动作（普通函数）
├── nas/
│   ├── application.py            # Flask 装配、路由、安全与响应
│   ├── plan_service.py           # 新：NAS 快照、版本、幂等及事务用例
│   ├── database.py               # 现有 Database，逐步收拢计划读写 SQL
│   ├── domain.py                 # 视图计算与 NAS 特有适配
│   └── static/                  # 首轮保持现有 UI 文件
├── android/runtime/main.py       # 本地 HTTP、HTML、JSON 持久化适配
├── android/build-apk.sh
├── nas/Dockerfile
└── docs/
```

目标依赖：两个入口 → 各自应用协调层 → `plan_actions` → `planner/timetable/events` → `time_slots/holidays`。`storage` 继续承担 JSON 兼容；NAS `Database` 负责 SQLite 事务。`events` 不得再 import `timetable`。NAS 与本地 Android 的认证、版本、持久化不同，保持独立。

## Classes 与 Modules 的职责

| 组件 | 形式 | 单一职责与边界 | 预期改进 |
| --- | --- | --- | --- |
| `time_slots.py` | 普通函数 | 解析 00:00–24:00、半小时单位；由 `events.clock`/`timetable.clock` 的兼容包装保持旧错误文本 | 去除依赖环 |
| `plan_actions.py` | 普通函数 | 对显式状态、动作、日期、截止格执行共用任务/事件/进度规则；仅合并语义相同的动作 | NAS 与本地规则只维护一处 |
| `nas.plan_service.PlanService` | 小类，可选具体命名 | 持有 `Database` 和可注入时钟；在现有事务内执行读取、初始化、版本/幂等、提交；不接收 Flask `request` 对象 | API 路由易读，业务状态变化可直接测 |
| `nas.database.Database` | 现有类 | 连接、事务、用户、计划/请求/备份的窄数据方法；不包含 HTTP 或排程规则 | SQL 边界集中，沿用 SQLite 实现 |
| `nas.application.create_app` | 保留工厂函数 | 注册路由、解析请求、鉴权、错误/HTTP 响应；调用 PlanService | 缩小大闭包；保持端点和安全头 |
| `nas.domain.view` | 普通函数 | 按已定日期/状态计算 NAS 视图数据，不读写数据库 | 保留纯计算边界 |
| `android.runtime.main.Handler` | 现有框架类 | loopback HTTP、HTML、JSON 文件提交；调用共用动作函数 | 本地特有 UI 与存储保持稳定 |
| `planner.py`、`timetable.py`、`events.py` | 普通函数 | 排程、事件展开与规则计算；继续接受显式状态 | 保持现有可测试的算法边界 |

`Database` 与 `Handler` 有真实生命周期和资源/框架状态，适合类。`PlanService` 只有在承载事务和时钟依赖后才值得建类；若只是转发函数，应改为普通函数。不要新建 `Task`、`Event`、`Calendar` 类层级、抽象仓库基类或策略工厂，现有 JSON 字典与两个存储格式需要稳定。SOLID 以 SRP 为主，DIP 限于时钟和存储注入，OCP 通过集中动作入口实现；无证据要求 LSP/ISP 重构。

## 分阶段执行与验收条件

1. **建立行为基线。** 获批准后在隔离数据环境运行 README 的 Python/Node 测试；记录当前通过/失败/跳过、接口响应、JSON 导入导出、旧备份、两端动作差异。此前只做静态检查。
2. **解除 P0 环。** 提取 `time_slots.py`，保留 `events.clock`、`timetable.clock` 的外部入口及各自错误消息；确认 `events` 不再导入 `timetable`。验证 00:00、24:00、非法半小时、跨夜事项和移动。
3. **抽取共用用例。** 以取消单次事项、进度记录、事件移动、任务拖动为序，从 `nas/domain.py` 与 `android/runtime/main.py` 提取同义流程。每移一项，对比两端状态、通知、提议刷新和失败行为。NAS 限额、版本/请求 ID 留在 NAS 层；本地文件提交留在 Android 层。
4. **缩小 NAS 应用工厂。** 先迁移 `snapshot` 与 `/api/actions` 的提交协调，再考虑认证/邀请的独立路由模块。保持同一 SQLite 事务中的版本检查、幂等记录、备份和保存，不把事务拆成多个提交。`view` 仍为纯函数。
5. **同步分发与 CI。** 每新增共享文件同步 `nas/Dockerfile` 和 `android/build-apk.sh`；让根共享模块修改触发 `.github/workflows/nas-check.yml`。最后在批准后的隔离环境核对 Docker 与本地 APK 资源，实机测试另作验收。
6. **可选收尾。** 仅在核心边界稳定后考虑拆 `nas/static/ui.js`、整理跨测试夹具、细分 `storage.migrate`，并标记旧 `SPEC.md`/`TESTING.md` 为历史记录。

## 必须锁定的契约

- NAS `/api/state`、`/api/actions` 的字段、版本冲突、重复 `request_id`、CSRF、帐号隔离及离线只读；本地 Android 的 `/`、`/bubble`、`/export` 与表单响应。
- 七日窗口、香港时区、半小时边界、固定/私人事项优先、已接受日程优先、前移提议待确认和旧提议拒绝。
- JSON schema、v1 迁移、导入前验证/备份、原子写与损坏文件只读；SQLite 的事务和版本语义。
- NAS 浏览器静态资源与 NAS APK 内置界面、本地 Android runtime 清单；UI 文案、HTML 属性与交互不在本轮改变。

成功标准：共用规则图无环；两个入口的同义动作由一处规则驱动；NAS API 事务与响应保持一致；已有测试和分发验收通过。当前未执行这些步骤。
