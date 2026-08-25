#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E621 / E926 下载器（GUI 版）
==============================================
统一封装 5 个爬虫脚本，无需再记命令行参数：
  1. 标签下载             (原 e6_scraper.py)
  2. 标签分页下载          (原 e6_taged_page_scraper.py)
  3. 艺术家分组下载         (原 e6_artist.py)
  4. Pool 下载（顺序编号）  (原 pool_scraper.py)
  5. Pool 下载（反转编号）  (原 e621.py)

API 用户名 / Key 每次启动时填写；勾选"记住"后下次自动填入（明文存本地）。
运行方式：python app.py
"""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import config as cfg
import core

# Windows 控制台编码兜底（防止中文报错乱码/编码异常）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

APP_TITLE = "E621 下载器 v1.0"
SITES = ["https://e621.net", "https://e926.net"]
PROXY_MODES = ["自动（跟随系统）", "不使用代理", "自定义..."]


class E621App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("840x700")
        root.minsize(740, 580)

        self.msg_queue = queue.Queue()          # 工作线程 -> 界面 消息队列
        self.cancel_event = threading.Event()   # 停止信号
        self.worker = None                      # 当前工作线程
        self.current_task = None                # (函数, 参数字典)

        self._build_auth_bar()
        self._build_notebook()
        self._build_action_bar()
        self._build_log()

        self._load_saved_config()
        root.after(100, self._poll_queue)

    # ------------------------------------------------------------
    # 界面构建
    # ------------------------------------------------------------
    def _build_auth_bar(self):
        bar = ttk.LabelFrame(self.root, text=" 认证信息（每次启动填写；用户名和 Key 留空则游客访问） ")
        bar.pack(fill="x", padx=10, pady=(10, 4))

        self.site_var = tk.StringVar(value=SITES[0])
        ttk.Label(bar, text="站点:").grid(row=0, column=0, padx=(8, 2), pady=6, sticky="e")
        ttk.Combobox(bar, textvariable=self.site_var, width=18, state="readonly",
                     values=SITES).grid(row=0, column=1, padx=2, pady=6, sticky="w")

        ttk.Label(bar, text="用户名:").grid(row=0, column=2, padx=(16, 2), pady=6, sticky="e")
        self.user_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self.user_var, width=14).grid(row=0, column=3, padx=2, pady=6, sticky="w")

        ttk.Label(bar, text="API Key:").grid(row=0, column=4, padx=(16, 2), pady=6, sticky="e")
        self.key_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self.key_var, width=24, show="*").grid(row=0, column=5, padx=2, pady=6, sticky="w")

        self.remember_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="记住（明文存本地）", variable=self.remember_var
                        ).grid(row=0, column=6, padx=10, pady=6)
        bar.columnconfigure(7, weight=1)

        # ---- 第二行：代理设置 ----
        ttk.Label(bar, text="代理:").grid(row=1, column=0, padx=(8, 2), pady=6, sticky="e")
        self.proxy_mode_var = tk.StringVar(value=PROXY_MODES[0])
        self.proxy_combo = ttk.Combobox(bar, textvariable=self.proxy_mode_var, width=18,
                                        state="readonly", values=PROXY_MODES)
        self.proxy_combo.grid(row=1, column=1, padx=2, pady=6, sticky="w")
        self.proxy_combo.bind("<<ComboboxSelected>>", self._on_proxy_mode)

        ttk.Label(bar, text="代理地址（自定义时填写）:").grid(row=1, column=2, padx=(16, 2), pady=6, sticky="e")
        self.proxy_custom_var = tk.StringVar()
        self.proxy_entry = ttk.Entry(bar, textvariable=self.proxy_custom_var, width=24)
        self.proxy_entry.grid(row=1, column=3, columnspan=2, padx=2, pady=6, sticky="w")
        self.proxy_hint = ttk.Label(bar, text="例: http://127.0.0.1:7897", foreground="gray")
        self.proxy_hint.grid(row=1, column=5, padx=2, pady=6, sticky="w")
        self._on_proxy_mode()

    def _on_proxy_mode(self, event=None):
        """根据代理模式启用/禁用自定义地址输入框。"""
        if self.proxy_mode_var.get() == "自定义...":
            self.proxy_entry.config(state="normal")
        else:
            self.proxy_entry.config(state="disabled")

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="x", padx=10, pady=4)

        # ---- Tab 1：标签下载（原 e6_scraper.py）----
        f1 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(f1, text="① 标签下载")
        ttk.Label(f1, text="搜索标签:").grid(row=0, column=0, sticky="e", pady=4)
        self.tags_var = tk.StringVar()
        ttk.Entry(f1, textvariable=self.tags_var, width=52).grid(row=0, column=1, columnspan=3, sticky="we", pady=4)
        ttk.Label(f1, text="数量限制（留空=全部）:").grid(row=1, column=0, sticky="e", pady=4)
        self.limit_var = tk.StringVar()
        ttk.Entry(f1, textvariable=self.limit_var, width=10).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(f1, text="输出目录（留空=自动）:").grid(row=2, column=0, sticky="e", pady=4)
        self.out1_var = tk.StringVar()
        ttk.Entry(f1, textvariable=self.out1_var, width=40).grid(row=2, column=1, columnspan=2, sticky="we", pady=4)
        ttk.Button(f1, text="浏览...", command=lambda: self._pick_dir(self.out1_var)).grid(row=2, column=3, padx=4)
        ttk.Label(f1, text="示例: aubrey_(iceink) 或 aubrey_(iceink) order:hot",
                  foreground="gray").grid(row=3, column=1, columnspan=3, sticky="w")
        f1.columnconfigure(2, weight=1)

        # ---- Tab 2：标签分页下载（原 e6_taged_page_scraper.py）----
        f2 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(f2, text="② 标签分页下载")
        ttk.Label(f2, text="搜索标签:").grid(row=0, column=0, sticky="e", pady=4)
        self.page_tags_var = tk.StringVar()
        ttk.Entry(f2, textvariable=self.page_tags_var, width=52).grid(row=0, column=1, columnspan=3, sticky="we", pady=4)
        ttk.Label(f2, text="页码（留空=全部页）:").grid(row=1, column=0, sticky="e", pady=4)
        self.page_var = tk.StringVar()
        ttk.Entry(f2, textvariable=self.page_var, width=10).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(f2, text="输出目录（留空=自动）:").grid(row=2, column=0, sticky="e", pady=4)
        self.out2_var = tk.StringVar()
        ttk.Entry(f2, textvariable=self.out2_var, width=40).grid(row=2, column=1, columnspan=2, sticky="we", pady=4)
        ttk.Button(f2, text="浏览...", command=lambda: self._pick_dir(self.out2_var)).grid(row=2, column=3, padx=4)
        ttk.Label(f2, text="填入页码则只下载该页（每页最多 320 张），留空则下载全部",
                  foreground="gray").grid(row=3, column=1, columnspan=3, sticky="w")
        f2.columnconfigure(2, weight=1)

        # ---- Tab 3：艺术家分组下载（原 e6_artist.py）----
        f3 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(f3, text="③ 艺术家分组下载")
        ttk.Label(f3, text="艺术家标签:").grid(row=0, column=0, sticky="e", pady=4)
        self.artist_var = tk.StringVar()
        ttk.Entry(f3, textvariable=self.artist_var, width=52).grid(row=0, column=1, columnspan=3, sticky="we", pady=4)
        ttk.Label(f3, text="输出目录（留空=自动）:").grid(row=1, column=0, sticky="e", pady=4)
        self.out3_var = tk.StringVar()
        ttk.Entry(f3, textvariable=self.out3_var, width=40).grid(row=1, column=1, columnspan=2, sticky="we", pady=4)
        ttk.Button(f3, text="浏览...", command=lambda: self._pick_dir(self.out3_var)).grid(row=1, column=3, padx=4)
        self.skip_others_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f3, text="跳过不属于任何 Pool 的帖子（只下池内作品）",
                        variable=self.skip_others_var).grid(row=2, column=1, columnspan=3, sticky="w", pady=4)
        ttk.Label(f3, text="按 Pool 分文件夹保存，非池作品存到 others 文件夹",
                  foreground="gray").grid(row=3, column=1, columnspan=3, sticky="w")
        f3.columnconfigure(2, weight=1)

        # ---- Tab 4：Pool 下载（顺序编号，原 pool_scraper.py）----
        f4 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(f4, text="④ Pool 下载（顺序）")
        ttk.Label(f4, text="Pool 链接:").grid(row=0, column=0, sticky="e", pady=4)
        self.pool1_var = tk.StringVar()
        ttk.Entry(f4, textvariable=self.pool1_var, width=52).grid(row=0, column=1, columnspan=3, sticky="we", pady=4)
        ttk.Label(f4, text="输出目录（留空=自动）:").grid(row=1, column=0, sticky="e", pady=4)
        self.out4_var = tk.StringVar()
        ttk.Entry(f4, textvariable=self.out4_var, width=40).grid(row=1, column=1, columnspan=2, sticky="we", pady=4)
        ttk.Button(f4, text="浏览...", command=lambda: self._pick_dir(self.out4_var)).grid(row=1, column=3, padx=4)
        ttk.Label(f4, text="例如 https://e621.net/pools/12345，图片按 1.jpg, 2.png ... 顺序命名",
                  foreground="gray").grid(row=2, column=1, columnspan=3, sticky="w")
        f4.columnconfigure(2, weight=1)

        # ---- Tab 5：Pool 下载（反转编号，原 e621.py）----
        f5 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(f5, text="⑤ Pool 下载（反转）")
        ttk.Label(f5, text="Pool 链接:").grid(row=0, column=0, sticky="e", pady=4)
        self.pool2_var = tk.StringVar()
        ttk.Entry(f5, textvariable=self.pool2_var, width=52).grid(row=0, column=1, columnspan=3, sticky="we", pady=4)
        ttk.Label(f5, text="输出目录（留空=自动）:").grid(row=1, column=0, sticky="e", pady=4)
        self.out5_var = tk.StringVar()
        ttk.Entry(f5, textvariable=self.out5_var, width=40).grid(row=1, column=1, columnspan=2, sticky="we", pady=4)
        ttk.Button(f5, text="浏览...", command=lambda: self._pick_dir(self.out5_var)).grid(row=1, column=3, padx=4)
        ttk.Label(f5, text="Pool 中最后一张 -> 1.jpg，倒数第二张 -> 2.png ...（倒序编号）",
                  foreground="gray").grid(row=2, column=1, columnspan=3, sticky="w")
        f5.columnconfigure(2, weight=1)

    def _build_action_bar(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=10, pady=6)
        self.start_btn = ttk.Button(bar, text="▶ 开始下载", command=self._start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(bar, text="■ 停止", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        self.status_var = tk.StringVar(value="空闲")
        ttk.Label(bar, textvariable=self.status_var).pack(side="left", padx=12)

    def _build_log(self):
        frame = ttk.LabelFrame(self.root, text=" 运行日志 ")
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_text = tk.Text(frame, wrap="word", state="disabled",
                                font=("Microsoft YaHei UI", 9))
        sb = ttk.Scrollbar(frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

    # ------------------------------------------------------------
    # 配置读写
    # ------------------------------------------------------------
    def _load_saved_config(self):
        data = cfg.load()
        if data.get("remember"):
            self.user_var.set(data.get("username", ""))
            self.key_var.set(data.get("api_key", ""))
            self.remember_var.set(True)
        last = data.get("last_output", "")
        if last:
            for var in (self.out1_var, self.out2_var, self.out3_var, self.out4_var, self.out5_var):
                var.set(last)
        mode = data.get("proxy_mode", "")
        if mode in PROXY_MODES:
            self.proxy_mode_var.set(mode)
        self.proxy_custom_var.set(data.get("proxy_custom", ""))
        self._on_proxy_mode()

    def _pick_dir(self, var: tk.StringVar):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            var.set(d)

    # ------------------------------------------------------------
    # 任务控制
    # ------------------------------------------------------------
    def log(self, msg: str):
        """工作线程调用：把日志放进队列，由主线程刷新到界面。"""
        self.msg_queue.put(("log", str(msg)))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "log":
                    self.log_text.configure(state="normal")
                    self.log_text.insert("end", payload + "\n")
                    self.log_text.see("end")
                    self.log_text.configure(state="disabled")
                elif kind == "done":
                    self._on_done()
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _start(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("提示", "任务正在运行中，请先停止或等待完成。")
            return

        tab = self.notebook.index(self.notebook.select())
        try:
            fn, kwargs, out_dir = self._collect_params(tab)
        except ValueError as e:
            messagebox.showwarning("参数错误", str(e))
            return

        self.current_task = (fn, kwargs)
        self.cancel_event.clear()
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set("运行中...")
        self.worker.start()

        # 保存配置（记住或上次输出目录）
        remember = bool(self.remember_var.get())
        cfg.save({
            "remember": remember,
            "username": self.user_var.get().strip() if remember else "",
            "api_key": self.key_var.get().strip() if remember else "",
            "last_output": out_dir or "",
            "proxy_mode": self.proxy_mode_var.get(),
            "proxy_custom": self.proxy_custom_var.get().strip(),
        })

    def _collect_params(self, tab: int):
        """按当前选项卡收集参数，返回 (函数, kwargs, 输出目录字符串)。"""
        if tab == 0:    # 标签下载
            tags = self.tags_var.get().strip()
            if not tags:
                raise ValueError("请填写搜索标签。")
            limit = self._parse_int(self.limit_var.get(), "数量限制")
            out = self.out1_var.get().strip()
            return (core.download_by_tags,
                    dict(tags=tags, output_dir=out or None, limit=limit, page=None, workers=1),
                    out)

        if tab == 1:    # 标签分页下载
            tags = self.page_tags_var.get().strip()
            if not tags:
                raise ValueError("请填写搜索标签。")
            page = self._parse_int(self.page_var.get(), "页码")
            out = self.out2_var.get().strip()
            return (core.download_by_tags,
                    dict(tags=tags, output_dir=out or None, limit=None, page=page, workers=2),
                    out)

        if tab == 2:    # 艺术家分组下载
            artist = self.artist_var.get().strip()
            if not artist:
                raise ValueError("请填写艺术家标签。")
            out = self.out3_var.get().strip()
            return (core.download_artist,
                    dict(artist_tag=artist, output_root=out or None,
                         skip_others=bool(self.skip_others_var.get())),
                    out)

        if tab == 3:    # Pool 顺序
            url = self.pool1_var.get().strip()
            if not url or "/pools/" not in url:
                raise ValueError("请填写合法的 Pool 链接（应包含 /pools/）。")
            out = self.out4_var.get().strip()
            return (core.download_pool, dict(pool_url=url, output_dir=out or None, reverse=False), out)

        if tab == 4:    # Pool 反转
            url = self.pool2_var.get().strip()
            if not url or "/pools/" not in url:
                raise ValueError("请填写合法的 Pool 链接（应包含 /pools/）。")
            out = self.out5_var.get().strip()
            return (core.download_pool, dict(pool_url=url, output_dir=out or None, reverse=True), out)

        raise ValueError("未知的选项卡。")

    @staticmethod
    def _parse_int(s: str, label: str):
        s = (s or "").strip()
        if not s:
            return None
        try:
            v = int(s)
        except ValueError:
            raise ValueError(f"{label}必须是整数。")
        if v <= 0:
            raise ValueError(f"{label}必须是正整数。")
        return v

    def _worker(self):
        try:
            user = self.user_var.get().strip()
            key = self.key_var.get().strip()
            base = self.site_var.get()

            # 代理设置
            mode = self.proxy_mode_var.get()
            if mode == "不使用代理":
                proxy = "off"
            elif mode == "自定义...":
                proxy = self.proxy_custom_var.get().strip() or "off"
            else:
                proxy = "auto"
            session = core.create_session(user, key, base, proxy=proxy)

            if session.proxies:
                self.log(f"已启用代理: {list(session.proxies.values())[0]}")
            else:
                self.log("未使用代理（直连）")
            if user and key:
                self.log(f"已使用认证信息登录 {base}")
            else:
                self.log(f"警告：用户名/API Key 为空，以游客身份访问 {base}（部分内容可能受限）")

            fn, kwargs = self.current_task
            self.log("=" * 40)
            self.log(f"开始任务：{getattr(fn, '__name__', str(fn))}")
            try:
                fn(session, log=self.log, cancel=self.cancel_event, **kwargs)
                self.log("\n===== 任务结束 =====")
            except Exception as e:
                self.log(f"\n任务出错: {e}")
        except Exception as e:
            self.log(f"\n初始化失败: {e}")
        finally:
            self.msg_queue.put(("done", None))

    def _on_done(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        if self.cancel_event.is_set():
            self.status_var.set("已停止")
        else:
            self.status_var.set("完成（空闲）")

    def _stop(self):
        self.cancel_event.set()
        self.status_var.set("正在停止...（等待当前请求结束）")
        self.log("已请求停止，将在当前下载完成后中止。")


def main():
    root = tk.Tk()
    E621App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
