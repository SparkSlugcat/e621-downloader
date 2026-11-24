# 已知问题 / Known issues

> **文档范围** —— 本文件记录**已确认、尚未修复**的问题及其修复线索。
> 安装、启动、运行出错的排查流程见 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)；功能用法见 README。
>
> **Scope** —— confirmed problems that are **not fixed yet**, together with enough detail to fix them.
> For installation and runtime failures see [TROUBLESHOOTING.md](TROUBLESHOOTING.md);
> for usage see the README.

> **工具声明** —— 本文档的整理与排版由 AI 编程助手 **WorkBuddy** 协助完成，结论均在本机核实。
>
> **Tooling disclosure** —— compiled and formatted with the assistance of the AI coding assistant
> **WorkBuddy**; the findings were verified on the author's machine.

**当前没有已知的未修复问题。**

**No known unresolved issues at this time.**

---

## 已修复 / Fixed

| 版本 | 问题 / Issue |
|---|---|
| v1.2.1 | e621 于 2026-11 更换了 posts 接口：响应从 `{"posts": [...]}` 变成顶层数组，字段从 `file.url` 变成 `files.original.url`。v1.2.0 及更早版本会报 `'list' object has no attribute 'get'`，无法下载任何内容。 |
| v1.2.1 | 提示文案仍写 `1.jpg, 2.png`，与实际的零填充命名 `001.jpg` 不符（6 条词条）。 |

### v1.2.1 说明

**接口改版的影响范围**比表面更大：不只是外层结构变了，取图 URL 的位置也变了。只把
`data.get("posts")` 改掉还不够——`get_download_url()` 会取不到任何 URL，表现为「可下载作品: 0」。

现在的处理是可兼容两套结构：`iter_posts()` 同时认顶层数组和 `{"posts": [...]}`；
`get_download_url()` 同时认 `files.original.url` 与旧的 `file.url`，原图缺失时降级到
`files.sample.jpg` / `webp`。离线测试里有专门的两个用例（`[new api tags]` / `[new api pool]`）
盯着这条路径，下次接口再改会立刻暴露。

**The API change went deeper than the wrapping.** The image URL also moved, so merely fixing
`data.get("posts")` would still yield "downloadable: 0". Both shapes are now accepted:
`iter_posts()` handles a top-level array or the legacy `{"posts": [...]}`, while
`get_download_url()` handles `files.original.url` or the legacy `file.url` and falls back to
`files.sample.jpg` / `webp`. Two offline cases (`[new api tags]` / `[new api pool]`) guard this path.
