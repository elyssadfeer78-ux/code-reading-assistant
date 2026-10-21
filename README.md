# 代码阅读助手 · Code Reading Assistant

> 工程代码阅读理解陪练 Skill —— AI 不替你读完整个仓库，而是每轮陪你把一个模块真正读懂。

**版本 0.4.0** · **零外部依赖**（不依赖任何 MCP、服务账号或网络额度）· MIT License

## 这是什么

一个「强制学习」型 AI Skill：当你让它帮忙理解工程代码时，它不会一次性代读整库、甩给你一份综述了事，而是每轮只聚焦一个小单元，**先把知识框架搭好、把知识点完整讲透，再基于所讲内容出题考你**——你用自己的话解释清楚、指出代码依据，才推进下一单元。

适合场景：接手陌生工程、修复缺陷前理解机制、读懂核心算法/配置/接口/测试。

## 核心教学规则

| 规则 | 说明 |
| --- | --- |
| **三段式教学** | 先搭框架 → 再讲重点 → 最后出题。框架与重点未完整呈现前，不得抛出任何问题 |
| **完整讲透** | 教学正文不设字数上限，像期末复习冲刺课：是什么/为什么/怎么用/边界/常见误区，逐点讲清 |
| **框架辅助记忆** | 除文字讲解外必须给出知识框架图（层级/流程图/关系图，文字图或 Mermaid），作为记忆锚点 |
| **问题必有依据** | 只基于已讲框架与重点出 1–2 个聚焦问题；没讲过的概念、例子、条件不得作为题目 |
| **不替写、不伪造** | 跳关/要答案时只给小结与问题；「懂了，继续」和沉默不作为理解证据 |
| **大代码库预处理** | 一次性遇到大量代码时，先轻量化索引出「代码地图大纲」，确认后逐块陪读，不一次性代读 |
| **收官综合测验** | 全部单元通过后，需跨模块串联数据流 + 综合场景判断通过，才宣布学完 |

代码状态（`not_read` / `verified` / `insufficient`）与学习状态分离记录；`verified` 只表示主张有代码依据，不代表代码被运行或测试通过。

## 快速开始

需要 Python 3.8+，无第三方依赖。在本目录（包含 `install.py`）运行：

```bash
# 预览将要写入哪些文件（不落盘）
python3 install.py --platform workbuddy --user --dry-run

# 安装到用户级（WorkBuddy 宿主）
python3 install.py --platform workbuddy --user

# 或只安装到某个项目
python3 install.py --platform workbuddy --project /path/to/your/project

# Codex 宿主
python3 install.py --platform codex --user
```

安装后**新建会话**，直接用自然语言下达代码阅读任务即可，例如：

> 「带我读这个项目的入口，弄清请求从路由到数据库经过了哪些函数」

每轮流程：定位少量代码 → 画知识框架图 + 完整讲透知识点 → 出 1–2 个基于所讲内容的问题 → 等你回答 → 核对通过后进入下一单元。

卸载：移走安装的 Skill 目录与规则文件（Codex 只删除规则文件中 `<!-- code-reading-assistant:start -->` 到 `<!-- code-reading-assistant:end -->` 之间的块），保留项目学习记录，然后新建会话。

| 平台 | 用户级 Skill 目录 | 用户级默认规则 |
| --- | --- | --- |
| WorkBuddy | `~/.codebuddy/skills/code-reading-assistant/` | `~/.codebuddy/rules/code-reading-assistant.md` |
| Codex | `~/.agents/skills/code-reading-assistant/` | `$CODEX_HOME/AGENTS.md`，存在有效 override 时使用它 |

## 仓库结构

```
code-reading-assistant/
├── code-reading-assistant/          # Skill 本体
│   ├── SKILL.md                     #   核心规则（教学流程、状态机、边界）
│   ├── agents/openai.yaml
│   ├── assets/                      #   模板：学习卡/代码地图/学习记录/代码证据
│   └── references/                  #   代码读取流程 + 评价规则
├── docs/                            # 用法与示例、优化记录
├── cases/                           # 示例输入任务
├── integrations/                    # 默认规则模板（安装器消费）
├── scripts/build_packages.py        # 构建独立发行包（无第三方依赖）
├── install.py                       # 本地安装器（计划/执行分离、原子写入、失败回滚）
└── tests/                           # 安装器与打包测试
```

## 文档

- [Skill 使用说明](docs/SKILL-README.md) —— 一轮流程、适用场景、安装卸载、默认开启说明
- [用法与示例](docs/用法与示例.md) —— 一轮完整陪读示例
- [优化记录 v0.4.0](docs/优化记录-v0.4.0.md) —— 全面性评估结论与补全明细
- [核心规则](code-reading-assistant/SKILL.md) —— 教学流程、状态机与边界条款

## 开发

```bash
python3 -m unittest discover -s tests -v        # 跑测试
python3 scripts/build_packages.py               # 构建发行包到 dist/
```

## 边界声明

- 本 Skill 依据**可观察的回答**陪学，不能证明输入由谁完成、真实心理理解或长期学习效果。
- 默认开启是可暂停、可卸载的教学约定，不是权限锁；安装测试不证明每个宿主每次都会遵守。
- 只读到函数签名/片段时如实说明读取层级；未运行不评价性能或正确性。
- 学习记录写在项目 `.learning/` 下；若 `progress.md` 已被其他学习任务占用，本版自动改用 `code-reading-progress.md`。

## License

MIT，见 [LICENSE](LICENSE)。
