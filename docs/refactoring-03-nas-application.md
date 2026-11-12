# 第三阶段：整理 NAS 计划快照与提交职责

分支：`refactor/03-nas-application`。本阶段采用方案 B：提取少量普通函数，并复用现有 `Database` 类；没有新增 `PlanService`。目标是改进代码组织，不改变 Planwise 的用户功能、界面、API、JSON 格式或数据库事务行为。

## 原来的具体问题

`nas/application.py` 的 `create_app()` 同时注册 Flask 路由并在内部处理计划数据。原 `snapshot()`（修改前约 72–88 行）直接查询 `plans`、初始化日程、必要时写回数据库，还组装 API 响应；原 `/api/actions`（修改前约 245–275 行）在路由中混合版本冲突检查、重复 `request_id` 判断、业务动作、导入前备份及三段写入 SQL。理解“保存计划”需在 HTTP 响应与数据库步骤之间来回阅读。

这属于维护性问题，不是已证实的功能错误。NAS 的认证、邀请与安全检查本身属于接口层，本轮没有移动它们；`nas/domain.py` 的业务规则也保持原样。

## 修改文件与职责对比

| 位置 | 修改前 | 修改后 |
| --- | --- | --- |
| `nas/application.py` | `snapshot()` 内直接读取、初始化、可能写回计划；`/api/actions` 路由内完成版本、去重、应用动作、备份与提交。 | 新增普通函数 `prepare_plan_snapshot()`（约第 30 行）和 `commit_plan_action()`（约第 45 行），分别描述计划快照准备与一次动作的提交顺序。`snapshot()`（约第 111 行）保留用户资料和响应数据组装；`action()`（约第 276 行）保留输入、鉴权和 HTTP 响应。 |
| `nas/database.py` | `Database` 已管理连接与事务，但上述计划、请求记录和导入备份 SQL 仍写在路由里。 | 在现有类中加入 `plan()`、`save_initialized_plan()`、`request_fingerprint()`、`backup_before_import()`、`save_plan_action()`（约第 76–99 行），集中执行对应 SQL。它们都接收调用方传入的 `db`，**不会自行开启或提交事务**。 |
| `nas/test_api.py` | 已覆盖版本冲突、重复请求、正常导入备份和无效导入。 | 增加 `test_import_write_failure_rolls_back_plan_backup_and_request()`（约第 143 行）：写入后模拟 SQLite 故障，检查计划、备份与请求记录共同回滚。 |
| `nas/domain.py` | 处理任务、事项、排程动作及 NAS 视图。 | 未修改。 |

数据库事务仍由 `Database.transaction()` 在 API 路由外层打开一次；计划初始化、备份、计划更新和请求记录都使用同一个连接。请求去重仍先于版本冲突检查，成功后仍返回最新快照；错误提示、状态码和返回字段不变。

## 为什么选方案 B

`Database` 已经是有状态对象：它持有数据库路径，提供连接与事务管理。把计划相关的 SQL 放在这个类里，有实际的封装价值。计划初始化与提交顺序则是明确的流程，普通函数可以表达，不需要为它额外建立一个只转发调用的 `PlanService`。这也避免增加一个新模块和新的打包清单维护点。

- **Modularity（模块化）：** 路由、提交协调、SQL、业务规则各有可辨认的位置。
- **Encapsulation（封装）：** 计划、备份和请求记录的 SQL 由现有 `Database` 类集中维护；事务所有权仍清楚地留在调用方。
- **Single Responsibility Principle（单一职责）：** 路由负责 HTTP，普通函数负责计划流程，`Database` 负责数据库操作，`nas/domain.py` 继续负责业务规则。

## 用“保存计划”举例

用户在 NAS 页面调整私人时间后提交。Flask 路由先验证会话和请求格式，再在一个事务中读取当前计划。`commit_plan_action()` 检查这次 `request_id` 是否已处理、页面版本是否过期，接着调用原有 `domain.apply()` 更新状态。`Database.save_plan_action()` 在**同一个事务**里保存新计划及请求记录，路由最后返回原格式的 API 快照。如果写入中途出错，该事务会回滚，用户原计划不会被部分覆盖。

## 实际测试结果

| 检查 | 修改前 | 修改后 |
| --- | --- | --- |
| README 的 Python 全量测试（项目 `.venv`，`unittest discover`） | 104 项通过，0 失败 | 105 项通过，0 失败；增加 1 项事务回滚测试 |
| README 的 Node 测试 | 10 项通过，0 失败 | 10 项通过，0 失败 |
| 两条 JavaScript 语法检查 | 通过 | 通过 |

现有 NAS 测试覆盖旧版本冲突、重复 `request_id`、正常导入备份和 API 响应；新增测试验证写入后故障时计划、备份与请求记录共同回滚。本轮没有运行 Docker 构建或设备测试；未修改前端资源、数据库 schema 或共享排程算法。

## 初学者总结

修改前，`application.py` 同时接收请求、安排保存步骤和处理部分数据库操作。修改后，`application.py` 负责网页请求，`commit_plan_action()` 负责组织保存流程，`Database` 类负责数据库读写。这样不改变功能，但代码分工更清楚。
