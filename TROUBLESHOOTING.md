# 🆘 排错手册 / Troubleshooting

> **文档范围** —— 本文件收录**装不上、跑不起来、跑到一半报错**的全部排查流程：启动失败、依赖缺失、
> `PYTHON_EXE` 配置、代理报错、凭据与站点选择，以及怎么报一个有用的 bug。
> README 只保留一张速查表，细节都在这里。
>
> **Scope** —— everything that can go wrong **before or during a run**: the launcher refusing to start,
> missing modules, `PYTHON_EXE`, proxy errors, credentials and site selection, and how to file a bug.
> The README keeps a cheat sheet; every detail lives here.

> **工具声明** —— 本文件的实测数据、复现过程与排版由 AI 编程助手 **WorkBuddy** 协助完成，
> 所有结论均在作者本机复现并人工复核。如有疑义，请以源码与文中的步骤为准。
>
> **Tooling disclosure** —— the measurements, reproductions and formatting here were produced with the
> assistance of the AI coding assistant **WorkBuddy**; every finding was reproduced on the author's
> machine and reviewed manually. Trust the source code and the steps below over this document.

**索引 / Index**

| § | 主题 |
|---|---|
| 1 | 双击没反应 / 窗口一闪就没 |
| 2 | `No module named ...` —— 依赖没装 |
| 3 | 用 `PYTHON_EXE` 指定解释器 |
| 4 | 实在找不到 Python 在哪 |
| 5 | 代理与网络报错 |
| 6 | 凭据、站点与下载异常 |
| 7 | 报 bug 要带什么 |

> 🟢 **先看这一条**：如果你只是想用，不想折腾环境，直接去
> [Releases](https://github.com/SparkSlugcat/e621-downloader/releases/latest) 下载
> `E621Downloader.exe` 双击运行 —— **不需要 Python，也不需要看下面 §1–§4**。
> 下面四节只针对「从源码跑 `app.py` / 双击 `启动.bat`」这一条路径。

---

## 1 双击没反应 / 窗口一闪就没

`启动.bat` 的行为取决于 `pythonw.exe` 在不在 PATH 上，这决定了你能看到多少报错：

| 情况 | 启动器怎么做 | 你能看到什么 |
|---|---|---|
| 找得到 `pythonw.exe` | `start "" pythonw.exe app.py` —— **无控制台** | **什么都没有**。窗口不弹、报错也看不到 |
| 找不到 `pythonw.exe` | 回退 `python app.py`，会占一个黑窗口 | 报错停在窗口里，末尾有 `[FAIL] ... pause` |

**所以「双击之后完全没反应」本身就是一条线索** —— 说明程序在无控制台的 `pythonw` 里已经崩了，
而崩的原因最常见就是**依赖没装**或**Python 路径不对**。

排查办法：**别双击**，打开 cmd，进到项目目录手敲一次，报错就会打出来：

```bat
cd /d "你的路径\e621_gui"
python app.py
```

| 报错样例 | 含义 | 修法 |
|---|---|---|
| `'python' 不是内部或外部命令` | 系统找不到 `python.exe` | 走 §3，配 `PYTHON_EXE` |
| `ModuleNotFoundError: No module named 'requests'` | Python 找到了，但依赖没装 | 走 §2 |
| `DLL load failed while importing _tkinter` | conda 环境缺 tkinter（`pythonw` 下同样静默） | `conda install -n 你的环境 tk` |
| `pythonw.exe not found` | 启动器会自动回退到 `python` | 不算错误，只是会多一个控制台窗口 |

> 💡 想彻底不看到黑窗口、也不可能有环境问题：直接用 Release 里的 `E621Downloader.exe`。


---

## 2 `No module named ...` —— 依赖没装

完整报错一般长这样，**只看最后一行**就够：

```text
Traceback (most recent call last):
  File "D:\你的路径\e621_gui\common.py", line 26, in <module>
    import requests
ModuleNotFoundError: No module named 'requests'
```

这个项目只需要一个库：

```bat
python -m pip install requests
```

| 容易踩的坑 | 现象 | 怎么办 |
|---|---|---|
| 用 `pip install` 而不是 `python -m pip install` | 装完再跑，还是同一个 `No module named` | 电脑上有多个 Python 时，`pip` 可能装到别的上面。**一律用 `python -m pip`** |
| 装到了另一个 Python 上 | `python -c "import sys; print(sys.executable)"` 打印的路径跟报错里 `File "...\common.py"` 不是同一个环境 | 用那个环境自己的解释器执行 `-m pip install` |
| 下载卡住、最后报 `ReadTimeoutError` | pip 一直转圈然后超时 | 换国内镜像：`python -m pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `'pip' 不是内部或外部命令` | cmd 里根本找不到 pip | 用 `python -m pip`，绕开 PATH |

**装完验证**（打印 `ok` 才算装对）：

```bat
python -c "import requests; print('ok')"
```

> 💡 **GUI 窗口能正常打开，但一点「开始」日志框里就冒出 traceback** —— 这就是缺依赖的典型样子
> （GUI 启动时只需要 `tkinter`，真正干活的是它拉起来的子进程）。

---

## 3 用 `PYTHON_EXE` 指定解释器

如果你**已经有了**一个 Python / conda 环境（环境名不叫 `py39` 也行，`myenv` / `ai` / `work` 任意都行），
**不需要改名** —— 把它的 `python.exe` 完整路径告诉启动器就行。

**永久**（推荐，写到注册表，全局生效）—— 打开任意 cmd，复制粘贴下面这一行（把路径换成你自己的）：

```bat
:: 1. 先找你的 python.exe 在哪
where python
:: 输出类似: C:\Users\你的用户名\miniconda3\envs\myenv\python.exe

:: 2. 把上面那行复制，改造成下面这条，粘到 cmd 里执行
setx PYTHON_EXE "C:\Users\你的用户名\miniconda3\envs\myenv\python.exe"
```

`setx` 写注册表，**执行后必须重新打开一个 cmd 才生效**。然后再双击 `启动.bat` 即可。

**临时**（仅当前 cmd）：

```bat
set PYTHON_EXE=C:\Users\你的用户名\miniconda3\envs\myenv\python.exe
启动.bat
```

---

## 4 实在找不到 Python 在哪

打开任意 cmd，敲：

```bat
where python
```

输出的**第一行**就是 `python.exe` 的完整路径。把它配到 `PYTHON_EXE` 即可。

如果 `where python` 一行都没输出，说明你**根本没装 Python** —— 装一个就行：

- 官方：<https://www.python.org/downloads/>（**勾** "Add Python to PATH"）
- 或 Miniconda：<https://docs.conda.io/en/latest/miniconda.html>

或者干脆不装：用 [Release](https://github.com/SparkSlugcat/e621-downloader/releases/latest) 里的
`E621Downloader.exe`。

---

## 5 代理与网络报错

e621 在中国大陆**无法直接访问**，必须准备可用的代理。「代理」一栏有三个选项：
**自动（跟随系统）** / **不使用代理** / **自定义…**。

| 现象 | 含义 | 怎么办 |
|---|---|---|
| 一直是「连接中」然后超时 | 代理没生效，或节点死了 | 先看日志区开头那行「实际使用的代理」是不是你以为的地址；换节点再试 |
| 「自动（跟随系统）」不管用 | 系统代理没设，或设了但软件读不到 | 改成「自定义…」手填 `http://127.0.0.1:7897` |
| 下载到一半大面积失败 | 节点抖了 | 任务会自动重试 `500/502/503/504`；连续失败就先换节点再重跑 |
| 列表能拉、图片下不动 | 图片走的是另一个 CDN，可能被单独限速 | 降并发、隔一会儿再跑；本工具会跳过已下好的文件 |

> 💡 任务启动时日志区会打印**实际使用的代理**。网络类报错先核对那一行，比猜快得多。

---

## 6 凭据、站点与下载异常

| 现象 | 原因 | 怎么办 |
|---|---|---|
| 部分标签或原图拉不到 | 以**游客**身份访问，无权限内容不可见 | 填 API 用户名 + Key（见 README「获取 API 用户名与 Key」） |
| 填了凭据还是 401 / 拉不到 | Key 过期，或填成了登录密码 | 重新到 Account Settings → API Access 生成；**填的是 API Key，不是账号密码** |
| 重启后凭据没了 | 没勾「记住（明文存本地）」 | 勾上；它存在 `%APPDATA%\E621Downloader\config.json`（明文，仅在私人电脑上勾） |
| 切到 `e926.net` 内容少很多 | e926 是**安全版**（SFW 过滤），本来就少 | 想要全量请用 `e621.net` |
| 「扫描名单」出来的条目比预期少 | 名单来自当前标签/艺术家的实际结果 | 先确认标签语法（支持 `feline` / `feline,order:score` 这种 e621 语法） |
| 输出目录留空后找不到文件 | 留空会以**标签名或合集名**自动建文件夹 | 看日志里打印的落盘路径 |

> ⚠️ API Key 等同于账号的 API 凭据，**不要分享、不要截图**。万一泄露，去同一页面重新生成一份，
> 旧的就作废了。

---

## 7 报 bug 要带什么

带上这五项，通常一轮就能定位：

1. **你走的是哪条路**：Release 里的 `E621Downloader.exe`，还是源码跑 `app.py` / `启动.bat`
2. **哪个下载模式**（①–⑤）、站点是 `e621.net` 还是 `e926.net`
3. **日志区最后 10 行**（GUI 里可以直接选中复制）
4. 代理那一栏选的是哪项，以及日志里打印的「实际使用的代理」是什么
5. 你期望什么、实际发生了什么

提 issue：<https://github.com/SparkSlugcat/e621-downloader/issues>

---
---

# Troubleshooting (English)

Everything that can go wrong **before or during a run** — startup, missing modules, `PYTHON_EXE`,
proxy errors, credentials — is on this page. The README keeps a cheat sheet; details live here.

> 🟢 **Read this first**: if you just want to use the tool, grab `E621Downloader.exe` from
> [Releases](https://github.com/SparkSlugcat/e621-downloader/releases/latest) and double-click it —
> **no Python, and you can skip §1–§4 entirely**. Those four sections only apply to running from
> source (`app.py` / `启动.bat`).

## 1 Nothing happens on double-click

What `启动.bat` does depends on whether `pythonw.exe` is on PATH — and that decides how much of the
error you get to see:

| Situation | What the launcher does | What you see |
|---|---|---|
| `pythonw.exe` found | `start "" pythonw.exe app.py` — **no console** | **Nothing at all.** No window, no error |
| `pythonw.exe` missing | falls back to `python app.py`, which keeps a console | the traceback stays on screen, ending with `[FAIL] ... pause` |

**So "double-clicked and nothing happened" is itself a clue** — it means the program already crashed
inside the console-less `pythonw`, and the usual causes are a **missing dependency** or a **wrong Python**.

Diagnose by **not double-clicking**: open a cmd window, `cd` into the project and run it by hand —
the traceback will print:

```bat
cd /d "YOUR_PATH\e621_gui"
python app.py
```

| Error | Meaning | Fix |
|---|---|---|
| `'python' is not recognized` | `python.exe` not on PATH | §3 — set `PYTHON_EXE` |
| `ModuleNotFoundError: No module named 'requests'` | Python found, dependency missing | §2 |
| `DLL load failed while importing _tkinter` | the conda env has no tkinter (also silent under `pythonw`) | `conda install -n YOUR_ENV tk` |
| `pythonw.exe not found` | the launcher falls back to `python` | not an error — you just get an extra console window |

> 💡 Want no console window *and* no environment to get wrong? Use `E621Downloader.exe` from Releases.

## 2 `No module named ...` — install the dependencies

Only the **last line** of the traceback matters:

```text
Traceback (most recent call last):
  File "D:\path\to\e621_gui\common.py", line 26, in <module>
    import requests
ModuleNotFoundError: No module named 'requests'
```

This project needs exactly one library:

```bat
python -m pip install requests
```

| Pitfall | Symptom | Fix |
|---|---|---|
| Running `pip install` instead of `python -m pip install` | The same `No module named` after "installing" | With several Pythons installed, bare `pip` may install into a different one. **Always use `python -m pip`** |
| Installed into the wrong interpreter | `python -c "import sys; print(sys.executable)"` prints a path outside the environment shown in the traceback | Run `-m pip install` with that environment's own interpreter |
| Downloads hang, then `ReadTimeoutError` | pip spins forever and times out | Use a mirror: `python -m pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `'pip' is not recognized` | pip isn't on PATH | Use `python -m pip` |

Verify (it has to print `ok`):

```bat
python -c "import requests; print('ok')"
```

> 💡 **The GUI opens fine, but a traceback shows up in the log the moment you hit Start** — that's the
> classic missing-dependency symptom (the GUI itself only needs `tkinter`; the real download runs in
> the child process it spawns).

## 3 Point the launcher at your Python (`PYTHON_EXE`)

If you already have a Python / conda env (any name works — `myenv` / `ai` / `work`), you don't need to
rename it. Just tell the launcher where its `python.exe` is.

**Permanent (registry, global)** — open any cmd and paste:

```bat
:: 1. Find your python.exe
where python
:: Output is like: C:\Users\YOUR_NAME\miniconda3\envs\myenv\python.exe

:: 2. Adapt that path and paste this
setx PYTHON_EXE "C:\Users\YOUR_NAME\miniconda3\envs\myenv\python.exe"
```

`setx` writes to the registry; **reopen any cmd for it to take effect**, then double-click `启动.bat` again.

**Temporary (current cmd only)**:

```bat
set PYTHON_EXE=C:\Users\YOUR_NAME\miniconda3\envs\myenv\python.exe
启动.bat
```

## 4 Can't find Python at all

```bat
where python
```

The **first line** is the full path to `python.exe` — set it as `PYTHON_EXE`. If `where python` prints
nothing, you don't have Python installed:

- Official: <https://www.python.org/downloads/> (check **"Add Python to PATH"**)
- Or Miniconda: <https://docs.conda.io/en/latest/miniconda.html>

Or skip Python entirely and use `E621Downloader.exe` from Releases.

## 5 Proxy and network errors

e621 is not directly reachable from mainland China. The Proxy selector has three choices:
**Auto (follow system)** / **No proxy** / **Custom…**.

| Symptom | Meaning | Fix |
|---|---|---|
| Stuck on "connecting", then times out | the proxy isn't in effect, or the node is dead | check the "proxy actually used" line at the top of the log; switch nodes and retry |
| Auto (follow system) does nothing | no system proxy set, or it isn't visible to the app | switch to Custom… and enter `http://127.0.0.1:7897` |
| Mass failures mid-download | unstable node | requests are retried on `500/502/503/504`; if it keeps failing, switch nodes and re-run |
| Listing works, images don't download | images come from a separate CDN that may throttle harder | lower concurrency, wait a bit and resume — already-downloaded files are skipped |

> 💡 The log prints the **proxy actually used** when a task starts. Check that line before guessing.

## 6 Credentials, site selection and odd downloads

| Symptom | Cause | Fix |
|---|---|---|
| Some tags or originals are missing | browsing as a **guest** | fill in API username + key (see "Getting an API username and key" in the README) |
| Credentials filled in, still 401 / empty | the key expired, or a password was pasted instead | regenerate under Account Settings → API Access; it must be the **API key**, not your password |
| Credentials gone after restart | "Remember (plaintext, local)" wasn't ticked | tick it; stored in `%APPDATA%\E621Downloader\config.json` (plaintext — private machines only) |
| `e926.net` returns far less | e926 is the **safe-for-work** mirror | use `e621.net` for the full set |
| The "scan list" has fewer entries than expected | the list reflects the actual result set for that tag/artist | double-check the tag syntax (`feline`, `feline,order:score` — standard e621 syntax) |
| Can't find the output files | an empty output dir means folders are auto-created from the tag or pool name | read the path printed in the log |

> ⚠️ The API key is an account credential — don't share it, don't screenshot it. If it leaks, regenerate
> it on the same page and the old one stops working.

## 7 Filing a bug report

Include these five items and it can usually be diagnosed in one round-trip:

1. **Which path you took**: `E621Downloader.exe` from Releases, or running from source
2. **Which download mode** (①–⑤) and which site (`e621.net` / `e926.net`)
3. **The last 10 lines of the log** (selectable and copyable in the GUI)
4. Which proxy option you picked, plus the "proxy actually used" line from the log
5. What you expected vs. what happened

Open an issue at <https://github.com/SparkSlugcat/e621-downloader/issues>.
