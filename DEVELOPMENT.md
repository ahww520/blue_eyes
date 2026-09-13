# CareEyes Pro 开发规范

本文档是 CareEyes Pro 的本地开发规范，仅适用于本仓库，不与任何远端仓库（GitHub/GitLab 等）关联。所有开发、测试、打包流程以本地 git 仓库为准。

## 1. 项目定位与运行环境

- 平台：仅 Windows 10/11，不跨平台。
- 解释器：Python 3.10+，不使用虚拟环境的特殊布局。
- 依赖：见 `requirements.txt`，只允许新增有明确用途的依赖；禁止引入 `pywin32`（已移除）。
- 入口：`mainpro.py`；运行命令：`python mainpro.py`。

## 2. 代码组织

- 两层结构，保持现有边界：
  - `careeyes_runtime.py`：纯 Windows API 封装与可测试的运行时逻辑（Gamma、单实例、活动检测、计时），不 import PyQt。
  - `mainpro.py`：UI、业务编排、配置读写。业务规则尽量下沉到 runtime，便于单元测试。
- 命名：
  - 模块/类：`PascalCase`；函数/变量：`snake_case`；常量：`UPPER_SNAKE_CASE`。
  - UI 内私有工具函数一律 `_` 前缀。
- 类型：关键函数保留简洁的类型注解或 docstring；不强制完整 typing。
- 注释：注释说明“为什么”，不重复“做什么”；保留代码内既有中文注释风格。

## 3. 编码约定

- Windows API 一律走 `careeyes_runtime.py` 的封装，`mainpro.py` 不直接 `ctypes` 调用（`_is_admin`、系统指标采集等历史例外保持现状，新增逻辑必须封装进 runtime）。
- 外部数据（配置文件、注册表、系统 API）必须先经过 `_bounded_int` / `_bounded_float` / `_parse_position` 等净化函数再使用。
- 异常处理：
  - runtime 层：API 失败抛 `OSError`，由调用方决定降级策略；
  - UI 层：非致命错误静默降级（显示“不可用”），不弹框、不崩进程；
  - 单实例失败、Gamma 写入失败等必须记录到对应 `errors` 字典。
- 配置持久化：始终“先写临时文件再原子替换”，不直接覆盖 `~/.care_eyes_pro.json`。
- 定时任务（QTimer）统一 1s 粒度；空闲检测阈值常量（`IDLE_PAUSE_SECONDS` 等）集中在 `mainpro.py` 顶部。
- 全屏进程名判断走 `FULLSCREEN_WHITELIST` / `FULLSCREEN_FORCE_DEFER` 两个集合，新增例外直接改集合，不写散落的 `if`。

## 4. 测试规范

- 框架：`unittest`，不引入 pytest。
- 位置与命名：`tests/test_<模块>.py`，测试函数 `test_<行为>`。
- 覆盖底线（见现有 `tests/`）：
  - Gamma 恢复（`GammaController`）；
  - 单实例互斥与激活消息（`SingleInstance`）；
  - 休息调度 / 全屏顺延（`WorkClock`、调度函数）；
  - 配置净化与启动清理；
  - UI 冒烟（`test_ui_smoke.py`）。
- 运行：
  ```powershell
  python -m unittest discover -s tests -v
  ```
- 规则：纯逻辑改动必须同步更新或新增用例；提交前必须本地全绿，不提交“跳过的测试”。

## 5. 构建与发布

- 打包：PyInstaller，入口 `build.ps1`，配置 `CareEyesPro.spec`。
  ```powershell
  pip install pyinstaller
  powershell -ExecutionPolicy Bypass -File .\build.ps1
  ```
- 产物：`dist/CareEyesPro.exe`；同步生成/更新根目录 `CareEyesPro.exe.sha256`。
- 版本：`mainpro.py` 顶部 `APP_VER` 与版本号同步；发布版本命名 `vX.Y`（次要版本=功能，不维护独立 changelog 分支）。

## 6. Git 提交规范

- 本地仓库（`.git`）为唯一事实来源，不配置任何 remote，不推送。
- 提交信息格式：`<type>: <简述>`，type 限 `feat` / `fix` / `chore` / `docs` / `test` / `refactor`。
- 粒度：一个可独立验证的改动一次提交；UI + runtime 解耦时分别提交。
- 提交前检查：`git status` 确认未把 `__pycache__/`、`build/`、`dist/`、`tmp/` 带入（见 `.gitignore`，`tmp/` 需手动保持不跟踪）。
- 大文件（exe、图片）不入库；截图仅保留 `docs/images/` 下被 README 引用的部分。

## 7. 目录约定

- `docs/`：开发日志、文档；`docs/images/`：README 引用的图片；`docs/previews/`：预览生成脚本（工具性质，不参与构建）。
- `tmp/`：本地实验区，永不提交。
- `tests/` 只放测试代码，不放 fixture 外的临时产物。

## 8. 文档同步

- 改动影响以下任一时必须同步 `README.md`：
  - 快捷键、配置字段、默认值；
  - 打包方式、环境要求；
  - 新增 UI 截图。
- 每个 `vX.Y` 发布在 `docs/CHANGELOG.md` 追加一节，记录：新增 / 修复 / 破坏性变更 / 已知问题。
