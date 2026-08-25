# E621 Downloader (GUI)

A lightweight desktop downloader for [e621.net](https://e621.net) / e926, built with Python + tkinter.
It bundles 5 common download modes into one window — **no command-line knowledge required**.

## Features

- **Tag download** — sequential numbering (`1.jpg, 2.png ...`), optional count limit
- **Tag download by page** — download a single page (320 posts max per page)
- **Artist download** — downloads an artist's works, auto-grouped into folders by pool
- **Pool download** — forward or reversed numbering
- **Resume support** — interrupted downloads continue where they left off
- **Credential safety** — username & API key entered at every launch, never hardcoded; optional "remember" (plain text, stored locally)
- **Proxy support** — auto-follows the Windows system proxy, or manual config

## Requirements

- Windows, Python 3.8+
- `pip install requests`

## Quick Start

Double-click `启动.bat` (launches with `pythonw`, no console window), or run:

```bat
python app.py
```

## Getting an e621 API Key

1. Log in at [e621.net](https://e621.net)
2. Click your avatar (top right) → **Account Settings**
3. Find the **API Access** section
4. Click **Generate** to create your API key (a long random string)
5. Enter your username and the API key in the credential fields at the top of the window

> Leaving credentials empty runs in guest mode — some tags or original images require login.
> Treat the API key as your account's API credential: never share it, and regenerate it on
> the same page if it ever leaks.

---

# E621 下载器（GUI 版）

一个基于 Python tkinter 的 **e621 / e926 图片下载图形界面工具**，把 5 种常用的下载方式
集成到一个窗口里，**无需记忆任何命令行参数**。

## ✨ 功能特性

| 功能 | 说明 |
|---|---|
| ① 标签下载 | 按标签下载全部图片，顺序编号 `1.jpg, 2.png ...`，可限制数量 |
| ② 标签分页下载 | 按标签下载，可指定只下某一页（每页最多 320 张） |
| ③ 艺术家分组下载 | 下载某艺术家全部作品，按所属 Pool 分文件夹，非池作品存 `others` |
| ④ Pool 下载（顺序） | 下载整个 Pool，图片按顺序编号 |
| ⑤ Pool 下载（反转） | 下载整个 Pool，图片反转编号（最后一张 → 1.jpg） |
| ♻️ 断点续传 | 中断后再次运行，自动跳过已下载文件继续 |
| 🔑 凭据安全 | API 用户名 / Key 每次启动填写，不写入代码；可选"记住"（明文存本地） |
| 🌐 代理支持 | 自动跟随系统代理，也支持手动配置 |

## 环境要求

- Windows（启动脚本为批处理），Python 3.8+
- 依赖：`requests`（`pip install requests`）

## 运行方式

**方式一**：双击 `启动.bat` —— 使用 `pythonw` 无窗口启动，不弹命令行黑窗。

**方式二**：命令行执行：

```bat
python app.py
```

> 如果双击后没有反应，在命令行运行 `python app.py` 查看具体报错信息。

## 使用说明

### API 用户名 / Key 的创建方法

1. 用浏览器打开 https://e621.net 并**登录**你的账号；
2. 点击右上角你的头像 → **Account Settings**（账户设置）；
3. 在设置页面里找到 **API Access**（API 访问）一栏；
4. 点击 **Generate**（生成）按钮，得到一串长随机字符，这就是你的 **API Key**；
5. 回到本软件，把**用户名**和生成的 **API Key** 填进窗口顶部的凭据栏。

> - 用户名和 Key 留空 = 游客身份，部分标签或原图可能无法访问；
> - API Key 等同于你账号的 API 凭证，**请勿分享给他人**；如不慎泄露，可在同一页面重新生成（旧 Key 立即作废）；
> - 勾选 **"记住（明文存本地）"** 后下次启动自动填入（保存在 `%APPDATA%\E621Downloader\config.json`，建议只在私人电脑上勾选）；
> - 站点可选 `e621.net` 或 `e926.net`（e926 内容更安全、更少）。

### 代理设置

需要代理才能访问外网时（例如本机运行 Clash 类代理软件），在"代理"一栏选择：

- **自动（跟随系统）**（默认）：读取 Windows 系统代理设置，例如 `127.0.0.1:7897`；
- **不使用代理**：直连，适合能直接访问 e621 的网络；
- **自定义...**：手动填写代理地址，例如 `http://127.0.0.1:7897`。

启动任务时日志区会显示实际使用的代理；下载卡住或报网络错误时，先检查这一栏。

### 各选项卡参数

- **搜索标签**：支持 e621 搜索语法，例如 `aubrey_(iceink)` 或 `arcanis_(hahaluckyme) order:hot`；
- **数量限制 / 页码**：留空表示不限制 / 下载全部页；
- **输出目录**：留空时自动以标签名或 Pool 名创建文件夹；
- **艺术家分组下载**：可勾选"跳过非池作品"只下载属于 Pool 的图片。

## 打包成独立 .exe（可选）

双击 `build_exe.bat`（自动安装 PyInstaller 并打包），完成后双击
`dist\E621下载器.exe` 即可，**无需安装 Python**。

## 文件结构

```
├── app.py          # 图形界面入口
├── core.py         # 统一下载引擎（5 种下载方式的核心逻辑）
├── config.py       # "记住"功能的配置读写
├── test_offline.py # 离线功能测试（模拟 API，无需联网）
├── README.md       # 说明文档（中英双语）
├── LICENSE         # MIT 许可证
├── 启动.bat         # 双击运行 GUI
└── build_exe.bat   # 打包 exe 的脚本（可选）
```

## 安全提示

- 本程序**不会**把用户名 / API Key 写进代码；只有勾选"记住"时才会明文保存在
  `%APPDATA%\E621Downloader\config.json`，**切勿把该文件提交到仓库**；
- 请勿提交任何真实的 e621 用户名或 API Key 到 GitHub；如有泄露，请在 e621
  账户设置的 **API Access** 页面重新生成。

## 免责声明

- 本工具仅供个人学习与合法用途，请遵守 e621 / e926 的服务条款与 API 使用规范（请求频率、用途等）；
- 使用者需自行承担使用本工具产生的任何后果，作者不对下载内容及账号安全负责。

## 许可证

[MIT License](LICENSE)
