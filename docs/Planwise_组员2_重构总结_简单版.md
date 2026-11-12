# INT6181 Planwise｜组员 2 代码重构总结（简单版）

**我的职责：** Code Refactoring & Object-Oriented Design（代码重构与面向对象设计）。

**一句话总结：** 我没有为 Planwise 增加新功能，而是让原有的 Python 代码分工更清楚、减少不必要的依赖，并通过测试检查原有功能是否保持正常。

## 一、今天做了什么？

| 阶段 | 修改前发现的问题 | 修改后做了什么 | 结果 |
|---|---|---|---|
| ① 时间模块重构 | `timetable.py` 导入 `events.py`；`events.py` 又反向导入 `timetable.py` 的时间解析函数，形成循环依赖。 | 新建 `time_slots.py` 放共用时间解析逻辑，保留原有函数接口，让 `events.py` 不再反向依赖 `timetable.py`。 | 模块关系更清楚；相关时间测试 39/39 通过。 |
| ② 重复业务逻辑审查 | NAS 与本地 Android 的“记录投入时间”流程有少量重复。 | 核对后发现核心规则已经通过共享模块复用，剩余重复不足以证明值得新建通用模块，因此决定**暂不修改代码**。 | 记录了审查与不重构的理由，避免过度设计。 |
| ③ NAS 代码重构 | `nas/application.py` 除接收网页请求，还混合了计划准备、保存流程和部分 SQL 操作。 | 新增 `prepare_plan_snapshot()` 与 `commit_plan_action()` 两个普通函数；把相关 SQL 操作整理进已有 `Database` 类。 | 职责更清楚，保留原有数据库事务行为。 |

## 二、第一阶段：循环依赖——最简单的例子

假设用户把一段私人时间从 **09:00 移到 09:30**。

- `events.py`：负责处理日程移动。
- `timetable.py`：安排时间表，需要向 `events.py` 查询哪些时间格被日程占用。
- 时间转换功能：把 `09:30` 解析成程序可使用的数值，例如 570 分钟。

| 修改前：谁找谁？ | 为什么？ |
|---|---|
| `timetable.py` → `events.py` | 查询日程占用了哪些时间格。 |
| `events.py` → `timetable.py` | 借用 `clock()` 进行时间转换。 |

这样就出现了 **A 找 B，B 又找 A** 的循环依赖。

| 修改后：谁找谁？ | 为什么？ |
|---|---|
| `timetable.py` → `events.py` | 仍然查询日程占用情况，这一合作不变。 |
| `events.py` → `time_slots.py` | 从独立模块获取时间解析功能。 |
| `timetable.py` → `time_slots.py` | 也可以使用相同的时间解析功能。 |

**一句话解释：** 原来 `timetable` 找 `events` 查询占用，`events` 又找 `timetable` 转换时间；现在把时间转换独立到 `time_slots`，就不用互相找了。

> 注意：这是**代码结构问题**，不是已经证实的时间计算错误或程序崩溃。用户原来的功能不需要改变。

## 三、第二阶段：为什么决定不改？

Planwise 有 NAS 和本地 Android 两个版本。它们保存数据的方法不同：NAS 使用 SQLite，本地 Android 使用 JSON 文件。这部分不应该强行统一。

两端的排程和事项规则已经主要共用 `planner.py`、`events.py`、`timetable.py`。确实还有一点“记录投入时间”的处理顺序重复，但新增 `plan_actions.py` 可能让简单代码分散到更多文件，也增加打包维护工作。

**最终决定：** 保留当前实现。以后如果两端出现行为不一致，或者这部分经常需要同时修改，再重新考虑提取共用函数。

**这也是 Code Review 的成果：** 发现可能的问题，并判断它是否真的值得改，而不是见到重复就必须重构。

## 四、第三阶段：NAS 保存计划——修改前 vs 修改后

例如用户修改私人时间，然后点击“保存计划”。

| 需要做的事 | 修改前 | 修改后 |
|---|---|---|
| 接收网页提交、验证用户、返回结果 | `application.py` | 仍由 `application.py` 负责 |
| 准备计划数据快照 | 混在 `snapshot()` 中 | `prepare_plan_snapshot()` 负责明确的准备步骤 |
| 检查重复请求、版本并组织保存流程 | 混在较长的路由 `action()` 中 | `commit_plan_action()` 负责安排步骤 |
| 处理任务和日程业务规则 | `nas/domain.py` | 不改变，继续使用 `nas/domain.py` |
| 执行部分计划、备份、请求记录 SQL | 有些直接写在路由中 | 整理到已有的 `Database` 类方法中 |

**用生活例子记：**

- `application.py` = 接待员：接收请求、返回结果。
- `commit_plan_action()` = 协调员：安排保存流程。
- `Database` = 数据库管理员：负责真正读取、写入数据。

`prepare_plan_snapshot()` 负责准备计划快照。Codex **没有新增** `PlanService` 类，因为目前用两个普通函数和已有的 `Database` 类就足以把工作分清楚。

### 为什么强调“同一个事务”？

保存计划可能需要同时更新计划数据、导入前备份或请求记录。**要么一起成功，要么出错时一起撤销**，不能保存到一半。重构后仍保留相同的事务连接，并新增了模拟写入失败的回滚测试。

## 五、测试结果

| 测试 | 第三阶段修改前 | 第三阶段修改后 |
|---|---|---|
| Python 测试 | 104/104 通过 | **105/105 通过** |
| Node 测试 | 10/10 通过 | **10/10 通过** |
| JavaScript 语法检查 | 通过 | 通过 |

新增的 **1 项 Python 测试** 用于检查：数据库写入出错时，计划、备份和请求记录能一起回滚。

**测试范围提醒：** 以上是 Codex 报告的自动化测试结果；不等于 Docker 构建或 Android 真机测试已经完成。

## 六、对应老师要求的哪些知识？

| 英文术语 | 中文理解 | 我的实际工作 |
|---|---|---|
| Refactoring | 不改变功能，整理代码 | 两次小范围结构重构 |
| Module | 独立 Python 文件 | 新建 `time_slots.py` |
| Circular Dependency | 两个模块互相依赖 | 解除了 `events.py` 对 `timetable.py` 的反向依赖 |
| Function | 负责一个明确步骤的代码 | 新增两个 NAS 计划处理函数 |
| Class / Encapsulation | 把相关数据与操作集中管理 | 改善已有 `Database` 类的数据库操作封装 |
| Single Responsibility | 不同部分有清楚的职责 | 网页入口、处理流程、SQL 操作分工更清楚 |
| Testing | 检查修改没有破坏原功能 | 运行回归测试，新增回滚测试 |
| Code Review | 检查代码并作出判断 | 第二阶段审查后决定不做不必要的重构 |

## 七、如何向组员或老师介绍？

> 我是组员 2，负责 Planwise 的代码重构与面向对象设计。第一，我将共用时间转换逻辑提取到 `time_slots.py`，解决了时间表和日程模块的循环依赖。第二，我审查了 NAS 与 Android 的重复代码，发现主要规则已经共用，因此没有盲目增加模块。第三，我整理了 NAS 的计划保存流程，让普通函数负责处理步骤，已有 `Database` 类负责数据库操作。整个过程没有增加用户功能；第三阶段修改后，105 项 Python 测试和 10 项 Node 测试通过。

## 八、最终代码与交接

- **最终整合分支：** `oop-modularization`
- **GitHub：** https://github.com/Sukiyin516/Planwise/tree/oop-modularization
- **最终合并提交（根据 Codex 报告）：** `d4b1942f8393bcee15c75b56cb45f8da67b9cf73`
- **下一位组员：** 组员 3 从这个分支的最新代码创建自己的输入校验与异常处理分支，不直接修改我的重构分支。

### 相关详细记录

- `docs/architecture-review-before.md`：修改前代码体检。
- `docs/refactoring-plan.md`：重构计划。
- `docs/refactoring-02-review.md`：第二阶段审查及不重构决定。
- `docs/refactoring-03-nas-application.md`：第三阶段真实修改、测试与技术细节。
- 第一阶段具体报告：以仓库中实际保存的第一阶段 Markdown 文件为准。

---

**最短总结：第一阶段解决“两个文件互相找”；第三阶段解决“一个文件做太多事”；第二阶段则有理有据地决定不改。**
