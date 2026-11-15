# 已知问题 / Known issues

> **文档范围** —— 本文件列出**已经确认、但暂未修复**的问题及其修复线索。
> 安装、启动、运行出错的排查流程见 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)；功能用法见 README。
>
> **Scope** —— confirmed problems that are **not fixed yet**, together with enough detail to fix them.
> For installation and runtime failures see [TROUBLESHOOTING.md](TROUBLESHOOTING.md);
> for usage see the README.

> **工具声明** —— 本文档的整理与排版由 AI 编程助手 **WorkBuddy** 协助完成，结论均在本机核实。
>
> **Tooling disclosure** —— compiled and formatted with the assistance of the AI coding assistant
> **WorkBuddy**; the findings were verified on the author's machine.

| # | 问题 | 影响 / Affects | 状态 |
|---|---|---|---|
| 1 | 界面与日志的示例文案仍写 `1.jpg, 2.png`，与实际的 `001.jpg` 不符 | 仅提示文字，不影响文件名 | 待修，随下次发版 |

---

## 1. 提示文案与实际的零填充命名不符

**现象**

v1.2.0 起下载文件改为零填充命名（`001.jpg`、`002.png` …），但界面上几处示例文案仍写作
`1.jpg, 2.png ...`。实际下载出来的文件是 `001.jpg`，与提示不一致。

**出现在** `i18n.py`，共 6 条（中英各 3 条）。行号为 v1.2.0 时的位置，以词条名为准：

| 词条 | 语言 | 现有文字 |
|---|---|---|
| `core_rev_start` | 中 | 开始下载，图片将按 Pool 反转顺序编号：最后一张 -> 1.jpg, 倒数第二张 -> 2.png ... |
| `hint_pool_seq` | 中 | 例如 https://e621.net/pools/12345，图片按 1.jpg, 2.png ... 顺序命名 |
| `hint_pool_rev` | 中 | Pool 中最后一张 -> 1.jpg，倒数第二张 -> 2.png ...（倒序编号） |
| `core_rev_start` | 英 | Downloading with reversed numbering: last post -> 1.jpg, second-last -> 2.png ... |
| `hint_pool_seq` | 英 | e.g. https://e621.net/pools/12345; images named 1.jpg, 2.png ... in order |
| `hint_pool_rev` | 英 | Last post -> 1.jpg, second-last -> 2.png ... (reversed numbering) |

`core.py` 的注释与 docstring 里也有同样的旧写法（不出现在界面上，可一并清理）：
`download_by_tags` 的 docstring、`download_pool` 的 docstring，以及「反转编号」「顺序编号」
两个分支前的注释。

**修法**

把示例里的 `1.jpg` 改为 `001.jpg`、`2.png` 改为 `002.png`。命名规则本身见 README 的
「文件命名」一节：至少 3 位零填充，超过 999 个时自动加宽。

**为什么不立即修**

只改一句文案就需要重新打包并重新发布 exe，为它单独发一个版本不值得。
留到下次有实质改动时一并带上——源码改完重新打包即可，无需其它配合。

**顺带可考虑（非缺陷）**

标签下载、标签分页两个选项卡的提示没有说明命名规则（只有 Pool 的两个选项卡写了）。
如果需要，可在那两处补一句指向「文件命名」的说明。

---

# Known issues (English)

## 1. Hint text does not match the zero-padded naming

**Symptom**

Since v1.2.0 downloaded files use zero-padded names (`001.jpg`, `002.png`, …), but several
hint strings still show `1.jpg, 2.png ...`. What actually lands on disk is `001.jpg`.

**Where**

Six entries in `i18n.py`, three per language:

| Key | Language | Current text |
|---|---|---|
| `core_rev_start` | zh | 开始下载，图片将按 Pool 反转顺序编号：最后一张 -> 1.jpg, 倒数第二张 -> 2.png ... |
| `hint_pool_seq` | zh | 例如 https://e621.net/pools/12345，图片按 1.jpg, 2.png ... 顺序命名 |
| `hint_pool_rev` | zh | Pool 中最后一张 -> 1.jpg，倒数第二张 -> 2.png ...（倒序编号） |
| `core_rev_start` | en | Downloading with reversed numbering: last post -> 1.jpg, second-last -> 2.png ... |
| `hint_pool_seq` | en | e.g. https://e621.net/pools/12345; images named 1.jpg, 2.png ... in order |
| `hint_pool_rev` | en | Last post -> 1.jpg, second-last -> 2.png ... (reversed numbering) |

The same old style also appears in comments and docstrings in `core.py` (`download_by_tags`,
`download_pool`, and the two numbering branches). Those are not shown in the UI and can be
cleaned up at the same time.

**Fix**

Replace `1.jpg` with `001.jpg` and `2.png` with `002.png` in the examples. The naming rule itself
is documented in the README's "File naming" section: at least three digits, widening past 999.

**Why it was not fixed immediately**

Changing one sentence would require rebuilding and republishing the exe, which is not worth a
release on its own. It will go out with the next change that has substance.

**Optional, not a defect**

The tag-download and page-download tabs do not mention the naming rule (only the two pool tabs
do). A one-line pointer to "File naming" could be added there if desired.
