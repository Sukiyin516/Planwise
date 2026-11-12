# 第二阶段审查：NAS 与本地 Android 的共用动作

审查范围：`oop-modularization` 分支的 `nas/domain.py`、`android/runtime/main.py` 及它们调用的共享规则。**本阶段仅做静态代码审查；没有修改业务代码，也没有运行新测试。** 此处不声称任何新的测试结果。

## 对比结果

| 操作 | NAS | 本地 Android | 判断 |
| --- | --- | --- | --- |
| 记录实际投入时间 `progress` | `nas/domain.py:61-68`：先调用 `record_clock()` 检查时段，再用 `mutate()` 写入投入记录，给最后一条 `work_log` 补起止时间，最后 `refresh()`。 | `android/runtime/main.py:328-333`：使用相同的四步顺序。 | **少量真正重复。** 若以后只改一端的步骤，可能出现行为差异；提取一个窄函数有潜在维护收益。 |
| 移动任务或事项、取消单次事项、保存事项 | `nas/domain.py:47-54,68` 调用共享规则后刷新日程。 | `android/runtime/main.py:310-321` 调用相同规则后刷新日程。 | 入口有相似的调用顺序，但复杂的验证和修改已在共享函数中；当前重复代码很短，暂不另建模块。 |
| 确认前移、保留原计划 | `nas/domain.py:44-45` 调用 `decide()`。 | `android/runtime/main.py:306-308` 调用 `decide()`。 | 核心规则已经共用，无需再次包装。 |
| 私人时间借用设置 | `nas/domain.py:55-56` 写入 `borrow_private`。 | `android/runtime/main.py:322-324` 写入同一状态字段。 | 只有简单赋值，不值得单独抽函数。 |

共享规则已经存在：任务和投入规则在 `planner.py:54-118`，事项规则在 `events.py:53-112`，排程、时间检查和提议规则在 `timetable.py:134-246`。两端调用这些模块，所以“代码看起来有两处调用”不等于“业务规则实现了两遍”。

## 两端本来就不同的部分

| 部分 | NAS | 本地 Android | 是否共用 |
| --- | --- | --- | --- |
| 请求输入 | `nas/domain.py:13-22` 把 JSON 字段整理为共享函数使用的列表形式，并检查字段数量与类型。 | `android/runtime/main.py:277-287` 读取 HTTP 表单及本地令牌。 | 保持各自的输入适配。 |
| 保存与冲突处理 | `nas/application.py:245-275` 在 SQLite 事务中检查帐号、版本和重复请求，再保存。 | `android/runtime/main.py:338-339` 保存本地 JSON 后更新内存状态。 | 不合并；两端存储和并发需求不同。 |
| 导入与备份 | `nas/domain.py:24-34` 有 NAS 数据量限制；`nas/application.py:269-275` 在数据库中保存导入前备份。 | `android/runtime/main.py:288-295` 在替换本地文件前复制原文件。 | JSON 校验仍用已有 `storage.import_state()`；备份方式保持分开。 |
| 可接受的动作 | NAS 有 `full_day`，并在 `nas/domain.py:59-67` 明确列出任务动作。 | Android 的 `android/runtime/main.py:328-330` 将其原有的其他表单动作交给 `mutate()`。 | 不为统一代码而改变动作范围。 |

## 决定：本阶段暂不重构

目前**没有必须新增 `plan_actions.py` 的证据**。记录投入时间的四步流程确实重复，抽取函数可能减少将来漏改一端的风险；但也会新增模块、导入关系和打包维护工作。NAS Docker 与本地 Android 打包脚本都显式列出共享 Python 文件（`nas/Dockerfile:9`、`android/build-apk.sh:10-14`），新模块须同步两份清单。

因此保留当前实现。未来若两端出现可证实的行为差异，或同一动作被频繁同步修改，再优先评估提取**只负责记录投入时间流程的窄函数**。不把 NAS 事务、帐号/版本检查或 Android 本地文件保存塞进同一个共用动作模块。
