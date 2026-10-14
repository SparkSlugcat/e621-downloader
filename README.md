# E621 下载器

面向 Windows 的 e621 / e926 图片下载工具，提供**图形界面**与**命令行**两种使用方式。

图形界面把五种常用下载方式集中在一个窗口内，无需记忆任何命令行参数；命令行脚本适合批量化、
脚本化，以及需要精确控制下载内容的场景。

当前版本：**v1.1.0**

## 主要特性

- **官方 API**：通过 e621 JSON API 获取数据；图片默认 4 线程并发下载，API 请求之间保持固定间隔。
- **五种下载模式**
  1. 标签下载 —— 按标签下载全部作品，顺序编号
  2. 标签分页下载 —— 只下载指定一页
  3. 艺术家分组下载 —— 下载某位艺术家的全部作品，按所属合集分文件夹保存
  4. 合集（Pool）下载（顺序）—— 按合集内顺序编号
  5. 合集（Pool）下载（反转）—— 反转编号，最后一张为 1
- **艺术家模式支持「先扫描、后勾选」**（v1.1.0 新增）：先扫描出该艺术家的全部合集与散图，
  在列表中勾选需要的项后再下载；支持「全选」。命令行对应 `--dry-run` 与 `--pick`。
- **断点续传**：中断后重新运行，会自动识别并跳过已下载的文件。
- **凭据安全**：API 用户名与 Key 仅在运行时填写，不写入代码。
- **代理支持**：可自动跟随系统代理，也可手动指定。
- **中英双语**：界面与日志可在右上角一键切换。

## 环境要求

- Windows
- Python 3.8 及以上（图形界面依赖 tkinter，通常随 Python 一同安装）
- 依赖：`requests`（`pip install requests`）
- 若不希望安装 Python，可直接使用 Releases 页面提供的独立 exe

## 快速开始

**方式一**：下载 Releases 页面提供的 exe，直接双击运行，无需安装 Python。

**方式二**：双击 `启动.bat`（以 `pythonw` 启动，不显示命令行窗口）。

**方式三**：在命令行中运行：

```bat
python app.py
```

> 若双击后没有反应，请在命令行执行 `python app.py`，查看具体错误信息。

## 使用说明

### 获取 API 用户名与 Key

1. 使用浏览器打开 https://e621.net 并登录账号；
2. 点击右上角头像 → **Account Settings**（账户设置）；
3. 找到 **API Access**（API 访问）一栏；
4. 点击 **Generate**（生成），得到一串随机字符，即 **API Key**；
5. 回到本软件，将用户名与 API Key 填入窗口顶部的凭据栏。

> 用户名与 Key 留空表示以游客身份访问，部分标签或原图可能无法获取。
> API Key 等同于账号的 API 凭据，请勿分享；如不慎泄露，可在同一页面重新生成。
> 勾选「记住（明文存本地）」后，下次启动会自动填入（保存在
> `%APPDATA%\E621Downloader\config.json`，建议仅在私人电脑上勾选）。
> 站点可选 `e621.net` 或 `e926.net`（后者内容更安全、更少）。

### 代理设置

需要代理才能访问外网时（例如本机运行 Clash 等代理软件），在「代理」一栏选择：

- **自动（跟随系统）**（默认）：读取 Windows 系统代理设置，例如 `127.0.0.1:7897`
- **不使用代理**：直连，适合可直连 e621 的网络
- **自定义…**：手动填写代理地址，例如 `http://127.0.0.1:7897`

> 中国大陆用户请注意：e621 在中国大陆无法直接访问，请自行准备可用的代理工具，
> 并在「代理」一栏选择「自动（跟随系统）」或「自定义…」并填写代理地址，否则将无法连接服务器。

任务启动时，日志区会显示实际使用的代理。下载卡住或报网络错误时，请先检查此项。

### 各下载模式

| 模式 | 说明 |
|---|---|
| ① 标签下载 | 按标签下载全部作品，顺序编号 `1.jpg, 2.png ...`，可限制数量 |
| ② 标签分页下载 | 按标签下载，可指定只下载某一页，并可自选每页数量（40/80/120/200/320） |
| ③ 艺术家分组下载 | 下载某位艺术家的全部作品，按所属合集分文件夹，散图存入 `others` |
| ④ 合集下载（顺序） | 下载整个合集，按顺序编号 |
| ⑤ 合集下载（反转） | 下载整个合集，反转编号（最后一张为 1） |

搜索标签支持 e621 的搜索语法，例如 `feline` 或 `feline,order:score`。输出目录留空时，
会自动以标签名或合集名创建文件夹。

### 艺术家分组下载与「扫描名单」

该模式将一位艺术家的作品按「合集（Pool）」分别存入不同文件夹，不属于任何合集的散图
存入 `others` 文件夹。界面提供三项操作：

- **扫描名单**：获取该艺术家的全部合集与散图，并显示在下方的名单表格中。
  此步骤只读取列表，不下载图片。
- **勾选 / 全选**：点击名单每行最前方的方框可切换是否下载该项；「全选」可一次性
  选中或取消选中全部。
- **下载选中**：只下载被勾选的项。

名单中的顺序是固定的（合集按名称排序，`others` 始终位于最后），因此同一艺术家的名单
在多次扫描之间保持一致。若存在同名合集，界面会标出各自的 ID，保存目录也会附带 ID 以便区分。

命令行等价用法：

```bat
python e6_artist.py --tags artist_name --dry-run
python e6_artist.py --tags artist_name --pick 1,3
python e6_artist.py --from-manifest e6_artist_manifest.json --pick 2-4
```

- `--dry-run`：只列出名单（并保存为 `e6_artist_manifest.json`），不下载
- `--pick`：按名单编号挑着下载，支持 `2-4,7`、`3-`（第 3 项至末尾）、`-3`（前 3 项）、`all` 等写法
- `--from-manifest`：直接读取已保存的名单，跳过重新扫描

`--pick` 的编号即 `--dry-run` 输出中显示的编号。

> 若不需要下载散图，可勾选「跳过不属于任何 Pool 的帖子」；使用「下载选中」时，
> 是否下载散图以勾选结果为准。

## 打包为独立 exe（可选）

运行 `build_exe.bat`（会自动安装 PyInstaller 并完成打包），完成后使用
`dist\E621Downloader.exe`，无需安装 Python。已打包的版本也会发布在 Releases 页面。

## 文件结构

```
├── app.py           # 图形界面入口
├── core.py          # 统一下载引擎
├── i18n.py          # 中英双语文案
├── config.py        # "记住"功能的配置读写
├── test_offline.py  # 离线功能测试（模拟 API，无需联网）
├── e6_artist.py     # 艺术家模式命令行脚本
├── common.py        # 命令行脚本的共享模块
├── README.md
├── LICENSE          # MIT 许可证
├── 启动.bat          # 双击运行图形界面
└── build_exe.bat    # 打包 exe 的脚本（可选）
```

## 安全提示

请勿将真实的 e621 用户名或 API Key 提交到任何公开仓库。如不慎泄露，请在 e621 账户设置的
**API Access** 页面重新生成。

## 免责声明

- 本工具仅供个人学习与合法用途（如艺术欣赏与翻译）。请自行遵守 e621 / e926 的服务条款
  （Terms of Service）与 API 使用规范（请求频率、用途等）。
- 请勿高频使用。频繁、大量的 API 请求可能导致账号被限流甚至封禁。本工具默认已内置
  1 秒请求间隔，但大批量下载时仍建议分批进行，避免长时间连续运行。
- 使用者需自行承担使用本工具产生的任何后果；作者不对下载内容、账号安全，以及因违反
  平台规则导致的封禁负责。

## 相关项目

- [felinepaw](https://github.com/SparkSlugcat/felinepaw) —— 覆盖 e621 / e-hentai /
  FurAffinity 等多个站点的命令行下载脚本集合。

## 许可证

[MIT License](LICENSE)

---

# E621 Downloader

A Windows downloader for e621 / e926, available both as a **desktop GUI** and as a **command-line
tool**.

The GUI brings five common download modes into a single window — no command-line arguments to
memorise. The command-line script is intended for batch, scripted, or fine-grained use.

Current version: **v1.1.0**

## Features

- **Official API**: fetches data through the e621 JSON API; images download with 4 concurrent
  threads by default, while API requests stay evenly spaced.
- **Five download modes**
  1. Tag download — download all posts for a tag, numbered in order
  2. Tag download by page — download a single page only
  3. Artist grouped download — download an artist's works, grouped into folders by pool
  4. Pool download (sequential) — numbered in pool order
  5. Pool download (reversed) — reversed numbering, the last post becomes 1
- **Artist mode supports "scan first, then tick"** (new in v1.1.0): scan the artist's pools and
  loose posts, tick the items you want, then download. A "select all" option is included.
  The command line offers the same via `--dry-run` and `--pick`.
- **Resume support**: interrupted downloads are recognised and skipped on the next run.
- **Credential safety**: the API username and key are entered at run time and never hard-coded.
- **Proxy support**: follow the Windows system proxy automatically, or configure one manually.
- **Bilingual UI**: switch between 中文 / English from the top-right corner.

## Requirements

- Windows
- Python 3.8+ (the GUI relies on tkinter, which ships with most Python installs)
- `requests` (`pip install requests`)
- Alternatively, use the standalone exe published under Releases — no Python required

## Quick Start

**Option 1**: download the standalone exe from Releases and run it directly (no Python needed).

**Option 2**: double-click `启动.bat` (launches with `pythonw`, no console window).

**Option 3**: run from the command line:

```bat
python app.py
```

> If double-clicking does nothing, run `python app.py` in a terminal to see the error message.

## Usage

### Getting an API username and key

1. Open https://e621.net in a browser and log in;
2. Click your avatar (top right) → **Account Settings**;
3. Find the **API Access** section;
4. Click **Generate** to create a random string — this is your **API key**;
5. Enter the username and API key into the credential fields at the top of the window.

> Leaving them empty runs in guest mode; some tags or original images may be unavailable.
> The API key is your account's API credential — never share it. If it leaks, regenerate it on
> the same page. Ticking "Remember (stored in plain text)" fills it in next time (saved to
> `%APPDATA%\E621Downloader\config.json`; recommended only on a private machine).
> The site can be set to `e621.net` or `e926.net` (the latter is safer and smaller).

### Proxy settings

If a proxy is required (for example, Clash running locally), choose one of the following in
the "Proxy" field:

- **Auto (follow system)** (default): reads the Windows system proxy, e.g. `127.0.0.1:7897`
- **No proxy**: direct connection, for networks with direct access to e621
- **Custom…**: enter a proxy address manually, e.g. `http://127.0.0.1:7897`

> Users in mainland China: e621 is not directly reachable there. Please set up a working proxy,
> then choose "Auto (follow system)" or "Custom…" and provide the address, otherwise the
> connection will fail.

The log panel shows the proxy actually in use when a task starts. If downloads stall or report
network errors, check this setting first.

### Download modes

| Mode | Description |
|---|---|
| ① Tag download | Download all posts for a tag, numbered `1.jpg, 2.png ...`, with an optional count limit |
| ② Tag download by page | Download a chosen page, with a selectable page size (40/80/120/200/320) |
| ③ Artist grouped download | Download an artist's works, grouped by pool; loose posts go to `others` |
| ④ Pool download (sequential) | Download a whole pool, numbered in order |
| ⑤ Pool download (reversed) | Download a whole pool with reversed numbering (last post becomes 1) |

Search tags accept e621 syntax, e.g. `feline` or `feline,order:score`. When the output folder is
left empty, one is created automatically from the tag or pool name.

### Artist grouped download and "Scan list"

This mode stores an artist's works in separate folders per pool; posts that belong to no pool go
into the `others` folder. The interface offers three actions:

- **Scan list**: fetch the artist's pools and loose posts and show them in the table below.
  This step only reads the list — no images are downloaded.
- **Tick / Select all**: click the box at the start of a row to toggle it; "Select all" selects
  or clears every row at once.
- **Download selected**: download only the ticked items.

The list order is fixed (pools sorted by name, `others` always last), so the same artist yields
a consistent list across scans. If two pools share a name, their IDs are shown and the folder
names include the ID for disambiguation.

Command-line equivalents:

```bat
python e6_artist.py --tags artist_name --dry-run
python e6_artist.py --tags artist_name --pick 1,3
python e6_artist.py --from-manifest e6_artist_manifest.json --pick 2-4
```

- `--dry-run`: list only (saved as `e6_artist_manifest.json`), without downloading
- `--pick`: download selected items by index; supports `2-4,7`, `3-` (3 to the end), `-3`
  (first 3) and `all`
- `--from-manifest`: read a previously saved list and skip the scan

The index used by `--pick` is exactly the number shown by `--dry-run`.

> To skip loose posts, tick "Skip posts that are not in any pool". When using
> "Download selected", the ticked rows take precedence.

## Packaging a standalone exe (optional)

Run `build_exe.bat` (it installs PyInstaller and builds automatically), then use
`dist\E621Downloader.exe` — no Python installation needed. Prebuilt versions are also published
under Releases.

## Project layout

```
├── app.py           # GUI entry point
├── core.py          # unified download engine
├── i18n.py          # bilingual text tables
├── config.py        # "remember" configuration storage
├── test_offline.py  # offline functional tests (mock API, no network)
├── e6_artist.py     # command-line script for artist mode
├── common.py        # shared module for the command-line script
├── README.md
├── LICENSE          # MIT
├── 启动.bat          # double-click to launch the GUI
└── build_exe.bat    # optional exe build script
```

## Security note

Never commit a real e621 username or API key to a public repository. If one leaks, regenerate it
on the **API Access** page in your e621 account settings.

## Disclaimer

- This tool is intended for personal learning and lawful use only (e.g. art appreciation and
  translation). You are responsible for complying with the e621 / e926 Terms of Service and API
  usage guidelines (request rate, intended use, etc.).
- Avoid heavy usage. Frequent or massive API requests may get your account rate-limited or even
  banned. A 1-second delay is built in by default, but large jobs should still be downloaded in
  batches rather than run continuously.
- You use this tool at your own risk. The author is not liable for downloaded content, account
  safety, or account bans caused by violating platform rules.

## Related

- [felinepaw](https://github.com/SparkSlugcat/felinepaw) — command-line downloader scripts
  covering e621 / e-hentai / FurAffinity and more.

## License

[MIT License](LICENSE)
