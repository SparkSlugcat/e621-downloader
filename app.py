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
界面语言可在右上角切换 中文 / English。
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
import i18n

# Windows 控制台编码兜底（防止中文报错乱码/编码异常）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITES = ["https://e621.net", "https://e926.net"]
PROXY_KEYS = ("auto", "off", "custom")


class E621App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.geometry("940x700")
        root.minsize(820, 580)

        self.msg_queue = queue.Queue()          # 工作线程 -> 界面 消息队列
        self.cancel_event = threading.Event()   # 停止信号
        self.worker = None                      # 当前工作线程
        self.current_task = None                # (函数, 参数字典)

        self.lang_key = "zh"
        self.proxy_mode_key = "auto"

        self._init_vars()
        self._load_saved_config()
        self._build_ui()
        root.after(100, self._poll_queue)

    # ------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------
    def t(self, key: str, **kw) -> str:
        return i18n.t(key, **kw)

    def _save_config(self):
        remember = bool(self.remember_var.get())
        cfg.save({
            "remember": remember,
            "username": self.user_var.get().strip() if remember else "",
            "api_key": self.key_var.get().strip() if remember else "",
            "last_output": self._current_out_dir(),
            "proxy_mode": self._current_proxy_key(),
            "proxy_custom": self.proxy_custom_var.get().strip(),
            "lang": self.lang_key,
        })

    def _load_saved_config(self):
        data = cfg.load()
        lang = data.get("lang", "zh")
        self.lang_key = lang if lang in i18n.LANGS else "zh"
        i18n.set_lang(self.lang_key)

        if data.get("remember"):
            self.user_var.set(data.get("username", ""))
            self.key_var.set(data.get("api_key", ""))
            self.remember_var.set(True)

        mode = data.get("proxy_mode", "auto")
        self.proxy_mode_key = mode if mode in PROXY_KEYS else "auto"
        self.proxy_custom_var.set(data.get("proxy_custom", ""))

        last = data.get("last_output", "")
        if last:
            for var in (self.out1_var, self.out2_var, self.out3_var, self.out4_var, self.out5_var):
                var.set(last)

    def _current_out_dir(self) -> str:
        out_vars = (self.out1_var, self.out2_var, self.out3_var, self.out4_var, self.out5_var)
        for v in out_vars:
            if v.get().strip():
                return v.get().strip()
        return ""

    def _current_proxy_key(self) -> str:
        disp = self.proxy_mode_var.get()
        for key in PROXY_KEYS:
            if self.t("proxy_" + key) == disp:
                return key
        return "auto"

    # ------------------------------------------------------------
    # 变量（跨界面重建保留用户输入）
    # ------------------------------------------------------------
    def _init_vars(self):
        self.site_var = tk.StringVar(value=SITES[0])
        self.user_var = tk.StringVar()
        self.key_var = tk.StringVar()
        self.remember_var = tk.BooleanVar(value=False)
        self.proxy_mode_var = tk.StringVar()
        self.proxy_custom_var = tk.StringVar()

        self.tags_var = tk.StringVar()
        self.limit_var = tk.StringVar()
        self.out1_var = tk.StringVar()
        self.page_tags_var = tk.StringVar()
        self.page_var = tk.StringVar()
        self.page_size_var = tk.StringVar(value="320")
        self.out2_var = tk.StringVar()
        self.artist_var = tk.StringVar()
        self.out3_var = tk.StringVar()
        self.skip_others_var = tk.BooleanVar(value=False)
        self.pool1_var = tk.StringVar()
        self.out4_var = tk.StringVar()
        self.pool2_var = tk.StringVar()
        self.out5_var = tk.StringVar()
        self.status_var = tk.StringVar()

    # ------------------------------------------------------------
    # 界面构建（语言切换时整体重建）
    # ------------------------------------------------------------
    def _build_ui(self):
        # 保留日志内容
        log_text = ""
        try:
            if hasattr(self, "log_text"):
                log_text = self.log_text.get("1.0", "end-1c")
        except Exception:
            log_text = ""

        for attr in ("_auth_frame", "_notebook", "_action_frame", "_log_frame"):
            w = getattr(self, attr, None)
            if w is not None:
                w.destroy()
                setattr(self, attr, None)

        self.root.title(self.t("app_title"))
        self._build_auth_bar()
        self._build_notebook()
        self._build_action_bar()
        self._build_log()

        if log_text:
            self.log_text.configure(state="normal")
            self.log_text.insert("1.0", log_text)
            self.log_text.configure(state="disabled")

        running = bool(self.worker and self.worker.is_alive())
        if running:
            self.status_var.set(self.t("status_running"))
        else:
            self.status_var.set(self.t("status_idle"))
        self.start_btn.config(state="disabled" if running else "normal")
        self.stop_btn.config(state="normal" if running else "disabled")
        self._on_proxy_mode()

    def _build_auth_bar(self):
        bar = ttk.LabelFrame(self.root, text=self.t("auth_frame"))
        bar.pack(fill="x", padx=10, pady=(10, 4))
        self._auth_frame = bar

        # ---- 行 0：语言 | 站点 | 用户名 | API Key ----
        # 语言切换放在最左侧；每行内容都远小于窗口宽度，任何窗口大小都不会被裁剪
        ttk.Label(bar, text=self.t("lang_label")).grid(row=0, column=0, padx=(8, 2), pady=6, sticky="e")
        self.lang_var = tk.StringVar(value=i18n.LANG_NAMES[0 if self.lang_key == "zh" else 1])
        lang_cb = ttk.Combobox(bar, textvariable=self.lang_var, width=9, state="readonly",
                               values=list(i18n.LANG_NAMES))
        lang_cb.grid(row=0, column=1, padx=2, pady=6, sticky="w")
        lang_cb.bind("<<ComboboxSelected>>", self._on_lang_change)

        ttk.Label(bar, text=self.t("site_label")).grid(row=0, column=2, padx=(14, 2), pady=6, sticky="e")
        ttk.Combobox(bar, textvariable=self.site_var, width=18, state="readonly",
                     values=SITES).grid(row=0, column=3, padx=2, pady=6, sticky="w")

        ttk.Label(bar, text=self.t("user_label")).grid(row=0, column=4, padx=(14, 2), pady=6, sticky="e")
        ttk.Entry(bar, textvariable=self.user_var, width=14).grid(row=0, column=5, padx=2, pady=6, sticky="w")

        ttk.Label(bar, text=self.t("key_label")).grid(row=0, column=6, padx=(14, 2), pady=6, sticky="e")
        ttk.Entry(bar, textvariable=self.key_var, width=20, show="*").grid(row=0, column=7, padx=2, pady=6, sticky="w")

        # ---- 行 1：记住 | 代理模式 ----
        ttk.Checkbutton(bar, text=self.t("remember"), variable=self.remember_var
                        ).grid(row=1, column=0, columnspan=2, padx=(8, 2), pady=6, sticky="w")

        ttk.Label(bar, text=self.t("proxy_label")).grid(row=1, column=2, padx=(14, 2), pady=6, sticky="e")
        self.proxy_mode_var.set(self.t("proxy_" + self.proxy_mode_key))
        proxy_cb = ttk.Combobox(bar, textvariable=self.proxy_mode_var, width=18, state="readonly",
                                values=[self.t("proxy_" + k) for k in PROXY_KEYS])
        proxy_cb.grid(row=1, column=3, padx=2, pady=6, sticky="w")
        proxy_cb.bind("<<ComboboxSelected>>", self._on_proxy_mode)

        # ---- 行 2：代理地址 ----
        ttk.Label(bar, text=self.t("proxy_addr_label")).grid(row=2, column=2, padx=(14, 2), pady=6, sticky="e")
        self.proxy_entry = ttk.Entry(bar, textvariable=self.proxy_custom_var, width=24)
        self.proxy_entry.grid(row=2, column=3, padx=2, pady=6, sticky="w")
        ttk.Label(bar, text=self.t("proxy_hint"), foreground="gray").grid(row=2, column=4, padx=2, pady=6, sticky="w")

        bar.columnconfigure(8, weight=1)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="x", padx=10, pady=4)
        self._notebook = self.notebook

        def bind_enter(entry):
            entry.bind("<Return>", lambda e: self._start())

        # ---- Tab 1：标签下载 ----
        f1 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(f1, text=self.t("tab_tag"))
        ttk.Label(f1, text=self.t("tags_label")).grid(row=0, column=0, sticky="e", pady=4)
        e1 = ttk.Entry(f1, textvariable=self.tags_var, width=52)
        e1.grid(row=0, column=1, columnspan=3, sticky="we", pady=4)
        bind_enter(e1)
        ttk.Label(f1, text=self.t("limit_label")).grid(row=1, column=0, sticky="e", pady=4)
        ttk.Entry(f1, textvariable=self.limit_var, width=10).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(f1, text=self.t("out_label")).grid(row=2, column=0, sticky="e", pady=4)
        ttk.Entry(f1, textvariable=self.out1_var, width=40).grid(row=2, column=1, columnspan=2, sticky="we", pady=4)
        ttk.Button(f1, text=self.t("browse"), command=lambda: self._pick_dir(self.out1_var)).grid(row=2, column=3, padx=4)
        ttk.Label(f1, text=self.t("hint_tags"), foreground="gray").grid(row=3, column=1, columnspan=3, sticky="w")
        f1.columnconfigure(2, weight=1)

        # ---- Tab 2：标签分页下载 ----
        f2 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(f2, text=self.t("tab_tag_page"))
        ttk.Label(f2, text=self.t("tags_label")).grid(row=0, column=0, sticky="e", pady=4)
        e2 = ttk.Entry(f2, textvariable=self.page_tags_var, width=52)
        e2.grid(row=0, column=1, columnspan=3, sticky="we", pady=4)
        bind_enter(e2)
        ttk.Label(f2, text=self.t("page_label")).grid(row=1, column=0, sticky="e", pady=4)
        ttk.Entry(f2, textvariable=self.page_var, width=10).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(f2, text=self.t("page_size_label")).grid(row=1, column=2, sticky="e", pady=4)
        ttk.Combobox(f2, textvariable=self.page_size_var, width=7, state="readonly",
                     values=["40", "80", "120", "200", "320"]).grid(row=1, column=3, sticky="w", pady=4)
        ttk.Label(f2, text=self.t("out_label")).grid(row=2, column=0, sticky="e", pady=4)
        ttk.Entry(f2, textvariable=self.out2_var, width=40).grid(row=2, column=1, columnspan=2, sticky="we", pady=4)
        ttk.Button(f2, text=self.t("browse"), command=lambda: self._pick_dir(self.out2_var)).grid(row=2, column=3, padx=4)
        ttk.Label(f2, text=self.t("hint_page"), foreground="gray").grid(row=3, column=1, columnspan=3, sticky="w")
        f2.columnconfigure(2, weight=1)

        # ---- Tab 3：艺术家分组下载 ----
        f3 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(f3, text=self.t("tab_artist"))
        ttk.Label(f3, text=self.t("artist_label")).grid(row=0, column=0, sticky="e", pady=4)
        e3 = ttk.Entry(f3, textvariable=self.artist_var, width=52)
        e3.grid(row=0, column=1, columnspan=3, sticky="we", pady=4)
        bind_enter(e3)
        ttk.Label(f3, text=self.t("out_label")).grid(row=1, column=0, sticky="e", pady=4)
        ttk.Entry(f3, textvariable=self.out3_var, width=40).grid(row=1, column=1, columnspan=2, sticky="we", pady=4)
        ttk.Button(f3, text=self.t("browse"), command=lambda: self._pick_dir(self.out3_var)).grid(row=1, column=3, padx=4)
        ttk.Checkbutton(f3, text=self.t("skip_others"), variable=self.skip_others_var
                        ).grid(row=2, column=1, columnspan=3, sticky="w", pady=4)
        ttk.Label(f3, text=self.t("hint_artist"), foreground="gray").grid(row=3, column=1, columnspan=3, sticky="w")
        f3.columnconfigure(2, weight=1)

        # ---- Tab 4：Pool 下载（顺序编号）----
        f4 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(f4, text=self.t("tab_pool_seq"))
        ttk.Label(f4, text=self.t("pool_url_label")).grid(row=0, column=0, sticky="e", pady=4)
        e4 = ttk.Entry(f4, textvariable=self.pool1_var, width=52)
        e4.grid(row=0, column=1, columnspan=3, sticky="we", pady=4)
        bind_enter(e4)
        ttk.Label(f4, text=self.t("out_label")).grid(row=1, column=0, sticky="e", pady=4)
        ttk.Entry(f4, textvariable=self.out4_var, width=40).grid(row=1, column=1, columnspan=2, sticky="we", pady=4)
        ttk.Button(f4, text=self.t("browse"), command=lambda: self._pick_dir(self.out4_var)).grid(row=1, column=3, padx=4)
        ttk.Label(f4, text=self.t("hint_pool_seq"), foreground="gray").grid(row=2, column=1, columnspan=3, sticky="w")
        f4.columnconfigure(2, weight=1)

        # ---- Tab 5：Pool 下载（反转编号）----
        f5 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(f5, text=self.t("tab_pool_rev"))
        ttk.Label(f5, text=self.t("pool_url_label")).grid(row=0, column=0, sticky="e", pady=4)
        e5 = ttk.Entry(f5, textvariable=self.pool2_var, width=52)
        e5.grid(row=0, column=1, columnspan=3, sticky="we", pady=4)
        bind_enter(e5)
        ttk.Label(f5, text=self.t("out_label")).grid(row=1, column=0, sticky="e", pady=4)
        ttk.Entry(f5, textvariable=self.out5_var, width=40).grid(row=1, column=1, columnspan=2, sticky="we", pady=4)
        ttk.Button(f5, text=self.t("browse"), command=lambda: self._pick_dir(self.out5_var)).grid(row=1, column=3, padx=4)
        ttk.Label(f5, text=self.t("hint_pool_rev"), foreground="gray").grid(row=2, column=1, columnspan=3, sticky="w")
        f5.columnconfigure(2, weight=1)

    def _build_action_bar(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=10, pady=6)
        self._action_frame = bar
        self.start_btn = ttk.Button(bar, text=self.t("start_btn"), command=self._start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(bar, text=self.t("stop_btn"), command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        ttk.Label(bar, textvariable=self.status_var).pack(side="left", padx=12)

    def _build_log(self):
        frame = ttk.LabelFrame(self.root, text=self.t("log_frame"))
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._log_frame = frame
        self.log_text = tk.Text(frame, wrap="word", state="disabled",
                                font=("Microsoft YaHei UI", 9))
        sb = ttk.Scrollbar(frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

    # ------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------
    def _on_lang_change(self, event=None):
        new_key = "zh" if self.lang_var.get() == i18n.LANG_NAMES[0] else "en"
        if new_key == self.lang_key:
            return
        self.lang_key = new_key
        i18n.set_lang(new_key)
        self._save_config()
        self.log(self.t("msg_lang_switched",
                        lang="中文" if new_key == "zh" else "English"))
        self._build_ui()

    def _on_proxy_mode(self, event=None):
        custom = self._current_proxy_key() == "custom"
        self.proxy_entry.config(state="normal" if custom else "disabled")

    def _pick_dir(self, var: tk.StringVar):
        d = filedialog.askdirectory(title=self.t("out_label"))
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
            messagebox.showinfo(self.t("app_title"), self.t("msg_running"))
            return

        tab = self.notebook.index(self.notebook.select())
        try:
            fn, kwargs, out_dir = self._collect_params(tab)
        except ValueError as e:
            messagebox.showwarning(self.t("msg_param_error"), str(e))
            return

        self.current_task = (fn, kwargs)
        self.cancel_event.clear()
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set(self.t("status_running"))
        self.worker.start()
        self._save_config()

    def _collect_params(self, tab: int):
        """按当前选项卡收集参数，返回 (函数, kwargs, 输出目录字符串)。"""
        if tab == 0:    # 标签下载
            tags = self.tags_var.get().strip()
            if not tags:
                raise ValueError(self.t("msg_need_tags"))
            limit = self._parse_int(self.limit_var.get(), self.t("field_limit"))
            out = self.out1_var.get().strip()
            return (core.download_by_tags,
                    dict(tags=tags, output_dir=out or None, limit=limit, page=None,
                         workers=4),
                    out)

        if tab == 1:    # 标签分页下载
            tags = self.page_tags_var.get().strip()
            if not tags:
                raise ValueError(self.t("msg_need_tags"))
            page = self._parse_int(self.page_var.get(), self.t("field_page"))
            try:
                page_size = int(self.page_size_var.get())
            except ValueError:
                page_size = 320
            out = self.out2_var.get().strip()
            return (core.download_by_tags,
                    dict(tags=tags, output_dir=out or None, limit=None, page=page,
                         page_size=page_size, workers=4),
                    out)

        if tab == 2:    # 艺术家分组下载
            artist = self.artist_var.get().strip()
            if not artist:
                raise ValueError(self.t("msg_need_artist"))
            out = self.out3_var.get().strip()
            return (core.download_artist,
                    dict(artist_tag=artist, output_root=out or None,
                         skip_others=bool(self.skip_others_var.get())),
                    out)

        if tab == 3:    # Pool 顺序
            url = self.pool1_var.get().strip()
            if not url or "/pools/" not in url:
                raise ValueError(self.t("msg_need_pool"))
            out = self.out4_var.get().strip()
            return (core.download_pool,
                    dict(pool_url=url, output_dir=out or None, reverse=False, workers=4),
                    out)

        if tab == 4:    # Pool 反转
            url = self.pool2_var.get().strip()
            if not url or "/pools/" not in url:
                raise ValueError(self.t("msg_need_pool"))
            out = self.out5_var.get().strip()
            return (core.download_pool,
                    dict(pool_url=url, output_dir=out or None, reverse=True, workers=4),
                    out)

        raise ValueError(self.t("msg_unknown_tab"))

    @staticmethod
    def _parse_int(s: str, label: str):
        s = (s or "").strip()
        if not s:
            return None
        try:
            v = int(s)
        except ValueError:
            raise ValueError(i18n.t("msg_limit_int", label=label))
        if v <= 0:
            raise ValueError(i18n.t("msg_limit_pos", label=label))
        return v

    def _worker(self):
        try:
            user = self.user_var.get().strip()
            key = self.key_var.get().strip()
            base = self.site_var.get()

            mode = self.proxy_mode_key
            if mode == "off":
                proxy = "off"
            elif mode == "custom":
                proxy = self.proxy_custom_var.get().strip() or "off"
            else:
                proxy = "auto"
            session = core.create_session(user, key, base, proxy=proxy)

            if session.proxies:
                self.log(self.t("msg_proxy_enabled", p=list(session.proxies.values())[0]))
            else:
                self.log(self.t("msg_proxy_direct"))
            if user and key:
                self.log(self.t("msg_logged_in", site=base))
            else:
                self.log(self.t("msg_guest", site=base))

            fn, kwargs = self.current_task
            self.log("=" * 40)
            self.log(self.t("msg_task_start", name=getattr(fn, "__name__", str(fn))))
            try:
                fn(session, log=self.log, cancel=self.cancel_event, **kwargs)
                self.log("\n" + self.t("msg_task_done"))
            except Exception as e:
                self.log("\n" + self.t("msg_task_error", err=e))
        except Exception as e:
            self.log("\n" + self.t("msg_init_error", err=e))
        finally:
            self.msg_queue.put(("done", None))

    def _on_done(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        if self.cancel_event.is_set():
            self.status_var.set(self.t("status_stopped"))
        else:
            self.status_var.set(self.t("status_done"))

    def _stop(self):
        self.cancel_event.set()
        self.status_var.set(self.t("status_stopping"))
        self.log(self.t("msg_stop_requested"))


def main():
    root = tk.Tk()
    E621App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
