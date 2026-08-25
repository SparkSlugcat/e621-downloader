#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
i18n：中英双语词库（供 app.py 界面与 core.py 日志共用）。

用法：
    import i18n
    i18n.set_lang("en")          # "zh" / "en"
    i18n.t("key")                # 返回当前语言的字符串
    i18n.t("key", name="x")      # 支持 str.format 参数
"""

_CURRENT = "zh"

ZH = {
    # ---------- 通用 ----------
    "core_cancelled": "已收到停止请求，任务中止。",

    # ---------- 帖子 ID 获取 ----------
    "core_page_fetched": "  第 {page} 页，获取到 {n} 个帖子（累计 {total}）",
    "core_bad_json": "    响应不是 JSON，前200字节: {head}",
    "core_fetch_fail": "获取帖子列表失败（第 {page} 页）: {err}",
    "core_fetch_fail_retry": "获取帖子列表失败（第 {page} 页）: {err}，等待 5 秒后重试...",
    "core_too_many_fails": "连续失败次数过多，已中止。请检查网络/代理设置后重试。",

    # ---------- 批量信息 ----------
    "core_batch_fetching": "  获取批次 ({a}-{b}/{total})",
    "core_batch_fail": "  批次请求失败，等待 5 秒后重试...",
    "core_batch_fail2": "  重试仍失败: {err}，跳过该批次",
    "core_downloadable_count": "  可下载作品: {n}",
    "core_no_url_suffix": "，无可用 URL: {n}",
    "core_batch_info_fail": "  批量获取帖子信息失败: {err}",
    "core_no_post_info": "  没有找到帖子信息",
    "core_info_fail": "批量获取帖子信息失败: {err}",

    # ---------- 标签下载 ----------
    "core_tags_empty": "错误：标签不能为空。",
    "core_tags_label": "搜索标签: {tags}",
    "core_page_only": "（仅第 {page} 页）",
    "core_limit_only": "（仅前 {n} 个）",
    "core_no_matches": "没有找到匹配的帖子。",
    "core_no_images": "没有可下载的图片。",
    "core_found_posts": "共找到 {n} 个帖子",
    "core_resume_from": "检测到已有 {n} 个文件，从序号 {m} 继续下载",
    "core_task_pending": "待下载任务数: {n}",
    "core_task_exists": "[{i}/{total}] #{pid} -> {name} 已存在，跳过",
    "core_dl_done": "[{i}/{total}] 下载 #{pid} 完成",
    "core_dl_start": "[{i}/{total}] 下载 #{pid} -> {name}",
    "core_dl_fail": "  下载 #{pid} 失败: {err}",
    "core_dl_fail_seq": "  下载失败: {err}",
    "core_done_header": "===== 下载完成 =====",
    "core_tags_summary": "标签: {tags}",
    "core_total_posts": "总计帖子: {n}",
    "core_success": "成功下载: {n}",
    "core_skipped": "已存在跳过: {n}",
    "core_failed_ids": "下载失败: {n} (ID: {ids})",
    "core_no_url_ids": "无可用 URL: {n} (ID: {ids})",
    "core_saved_to": "文件保存至: {path}",

    # ---------- 艺术家分组 ----------
    "core_artist_empty": "错误：艺术家标签不能为空。",
    "core_artist_label": "艺术家标签: {tag}",
    "core_fetching_artist": "正在获取艺术家所有帖子 ID...",
    "core_artist_no_posts": "没有找到任何帖子。",
    "core_fetching_details": "正在获取帖子详细信息以提取 Pool 信息...",
    "core_pool_info_summary": "发现 {pools} 个相关 Pool，{posts} 个帖子不属于任何池",
    "core_processing_pool": "正在处理 Pool ID: {pid}",
    "core_pool_name_count": "  Pool 名称: {name}, 作品数: {n}",
    "core_pool_fetch_fail": "  获取 Pool {pid} 失败: {err}",
    "core_downloading_others": "下载 {n} 个无 Pool 帖子到 others 文件夹",
    "core_skipped_others": "已跳过 {n} 个无 Pool 帖子（已勾选跳过）",
    "core_all_done": "全部完成！文件保存在: {path}",
    "core_post_dl_fail": "  下载帖子 #{pid} 失败: {err}",
    "core_posts_dir_done": "  下载完成：成功 {ok}，失败/跳过 {fail}",

    # ---------- Pool 下载 ----------
    "core_err": "错误: {err}",
    "core_pool_url_invalid": "无法从 URL 中提取 Pool ID: {url}",
    "core_pool_id": "解析到 Pool ID: {pid}",
    "core_fetching_pool": "正在获取 Pool 信息...",
    "core_pool_fail": "获取 Pool 信息失败: {err}",
    "core_pool_empty": "该 Pool 中没有作品。",
    "core_pool_name": "Pool 名称: {name}",
    "core_post_count": "作品数量: {n}",
    "core_fetching_details2": "正在获取作品详细信息...",
    "core_no_downloadable": "没有可下载的作品。",
    "core_resume_rev": "检测到已有 {n} 个文件，从序号 {m} 开始续传{rev}",
    "core_rev_suffix": "（反转顺序）",
    "core_rev_start": "开始下载，图片将按 Pool 反转顺序编号：最后一张 -> 1.jpg, 倒数第二张 -> 2.png ...",
    "core_post_exists": "[{i}/{total}] 作品 #{pid} -> {name} 已存在，跳过",
    "core_post_dl": "[{i}/{total}] 下载作品 #{pid} -> {name}",
    "core_post_dl_simple": "[{i}] 下载作品 #{pid} -> {name}",
    "core_pool_summary": "Pool: {name} (ID: {pid})",
    "core_total_works": "总计作品: {n}",
    "core_downloadable": "可下载作品: {n}",

    # ---------- 界面 ----------
    "app_title": "E621 下载器 v1.0",
    "auth_frame": "认证信息（每次启动填写；用户名和 Key 留空则游客访问）",
    "site_label": "站点:",
    "user_label": "用户名:",
    "key_label": "API Key:",
    "remember": "记住（明文存本地）",
    "lang_label": "语言:",
    "proxy_label": "代理:",
    "proxy_auto": "自动（跟随系统）",
    "proxy_off": "不使用代理",
    "proxy_custom": "自定义...",
    "proxy_addr_label": "代理地址（自定义时填写）:",
    "proxy_hint": "例: http://127.0.0.1:7897",
    "tab_tag": "① 标签下载",
    "tab_tag_page": "② 标签分页下载",
    "tab_artist": "③ 艺术家分组下载",
    "tab_pool_seq": "④ Pool 下载（顺序）",
    "tab_pool_rev": "⑤ Pool 下载（反转）",
    "tags_label": "搜索标签:",
    "limit_label": "数量限制（留空=全部）:",
    "out_label": "输出目录（留空=自动）:",
    "browse": "浏览...",
    "hint_tags": "示例: aubrey_(iceink) 或 aubrey_(iceink) order:hot",
    "page_label": "页码（留空=全部页）:",
    "hint_page": "填入页码则只下载该页（每页最多 320 张），留空则下载全部",
    "artist_label": "艺术家标签:",
    "skip_others": "跳过不属于任何 Pool 的帖子（只下池内作品）",
    "hint_artist": "按 Pool 分文件夹保存，非池作品存到 others 文件夹",
    "pool_url_label": "Pool 链接:",
    "hint_pool_seq": "例如 https://e621.net/pools/12345，图片按 1.jpg, 2.png ... 顺序命名",
    "hint_pool_rev": "Pool 中最后一张 -> 1.jpg，倒数第二张 -> 2.png ...（倒序编号）",
    "start_btn": "▶ 开始下载",
    "stop_btn": "■ 停止",
    "status_idle": "空闲",
    "status_running": "运行中...",
    "status_stopping": "正在停止...（等待当前请求结束）",
    "status_done": "完成（空闲）",
    "status_stopped": "已停止",
    "log_frame": " 运行日志 ",
    "msg_running": "任务正在运行中，请先停止或等待完成。",
    "msg_need_tags": "请填写搜索标签。",
    "msg_need_artist": "请填写艺术家标签。",
    "msg_need_pool": "请填写合法的 Pool 链接（应包含 /pools/）。",
    "msg_limit_int": "{label}必须是整数。",
    "msg_limit_pos": "{label}必须是正整数。",
    "field_limit": "数量限制",
    "field_page": "页码",
    "msg_unknown_tab": "未知的选项卡。",
    "msg_param_error": "参数错误",
    "msg_task_start": "开始任务：{name}",
    "msg_task_done": "===== 任务结束 =====",
    "msg_task_error": "任务出错: {err}",
    "msg_init_error": "初始化失败: {err}",
    "msg_proxy_enabled": "已启用代理: {p}",
    "msg_proxy_direct": "未使用代理（直连）",
    "msg_logged_in": "已使用认证信息登录 {site}",
    "msg_guest": "警告：用户名/API Key 为空，以游客身份访问 {site}（部分内容可能受限）",
    "msg_stop_requested": "已请求停止，将在当前下载完成后中止。",
    "msg_lang_switched": "已切换语言: {lang}",
}

EN = {
    # ---------- Common ----------
    "core_cancelled": "Stop requested; task aborted.",

    # ---------- Post ID fetching ----------
    "core_page_fetched": "  Page {page}: got {n} posts (total {total})",
    "core_bad_json": "    Response is not JSON; first 200 bytes: {head}",
    "core_fetch_fail": "Failed to fetch post list (page {page}): {err}",
    "core_fetch_fail_retry": "Failed to fetch post list (page {page}): {err}; retrying in 5s...",
    "core_too_many_fails": "Too many consecutive failures; aborted. Check network/proxy settings and retry.",

    # ---------- Batch info ----------
    "core_batch_fetching": "  Fetching batch ({a}-{b}/{total})",
    "core_batch_fail": "  Batch request failed; retrying in 5s...",
    "core_batch_fail2": "  Retry failed: {err}; skipping this batch",
    "core_downloadable_count": "  Downloadable posts: {n}",
    "core_no_url_suffix": ", without URL: {n}",
    "core_batch_info_fail": "  Failed to fetch post info batch: {err}",
    "core_no_post_info": "  No post info found",
    "core_info_fail": "Failed to fetch post info batch: {err}",

    # ---------- Tag download ----------
    "core_tags_empty": "Error: tags cannot be empty.",
    "core_tags_label": "Search tags: {tags}",
    "core_page_only": " (page {page} only)",
    "core_limit_only": " (first {n} only)",
    "core_no_matches": "No matching posts found.",
    "core_no_images": "No downloadable images.",
    "core_found_posts": "Found {n} posts in total",
    "core_resume_from": "Detected {n} existing files; continuing from {m}",
    "core_task_pending": "Pending download tasks: {n}",
    "core_task_exists": "[{i}/{total}] #{pid} -> {name} already exists, skipped",
    "core_dl_done": "[{i}/{total}] Downloaded #{pid}",
    "core_dl_start": "[{i}/{total}] Downloading #{pid} -> {name}",
    "core_dl_fail": "  Download #{pid} failed: {err}",
    "core_dl_fail_seq": "  Download failed: {err}",
    "core_done_header": "===== Download complete =====",
    "core_tags_summary": "Tags: {tags}",
    "core_total_posts": "Total posts: {n}",
    "core_success": "Downloaded: {n}",
    "core_skipped": "Skipped (existing): {n}",
    "core_failed_ids": "Failed: {n} (ID: {ids})",
    "core_no_url_ids": "No URL: {n} (ID: {ids})",
    "core_saved_to": "Files saved to: {path}",

    # ---------- Artist grouped download ----------
    "core_artist_empty": "Error: artist tag cannot be empty.",
    "core_artist_label": "Artist tag: {tag}",
    "core_fetching_artist": "Fetching all post IDs of the artist...",
    "core_artist_no_posts": "No posts found.",
    "core_fetching_details": "Fetching post details to extract pool info...",
    "core_pool_info_summary": "Found {pools} related pools; {posts} posts not in any pool",
    "core_processing_pool": "Processing pool ID: {pid}",
    "core_pool_name_count": "  Pool name: {name}, posts: {n}",
    "core_pool_fetch_fail": "  Failed to fetch pool {pid}: {err}",
    "core_downloading_others": "Downloading {n} non-pool posts to the 'others' folder",
    "core_skipped_others": "Skipped {n} non-pool posts (skip option enabled)",
    "core_all_done": "All done! Files saved to: {path}",
    "core_post_dl_fail": "  Failed to download post #{pid}: {err}",
    "core_posts_dir_done": "  Download done: {ok} ok, {fail} failed/skipped",

    # ---------- Pool download ----------
    "core_err": "Error: {err}",
    "core_pool_url_invalid": "Unable to extract pool ID from URL: {url}",
    "core_pool_id": "Resolved pool ID: {pid}",
    "core_fetching_pool": "Fetching pool info...",
    "core_pool_fail": "Failed to fetch pool info: {err}",
    "core_pool_empty": "This pool has no posts.",
    "core_pool_name": "Pool name: {name}",
    "core_post_count": "Post count: {n}",
    "core_fetching_details2": "Fetching post details...",
    "core_no_downloadable": "No downloadable posts.",
    "core_resume_rev": "Detected {n} existing files; resuming from {m}{rev}",
    "core_rev_suffix": " (reversed)",
    "core_rev_start": "Downloading with reversed numbering: last post -> 1.jpg, second-last -> 2.png ...",
    "core_post_exists": "[{i}/{total}] Post #{pid} -> {name} already exists, skipped",
    "core_post_dl": "[{i}/{total}] Downloading post #{pid} -> {name}",
    "core_post_dl_simple": "[{i}] Downloading post #{pid} -> {name}",
    "core_pool_summary": "Pool: {name} (ID: {pid})",
    "core_total_works": "Total posts: {n}",
    "core_downloadable": "Downloadable posts: {n}",

    # ---------- UI ----------
    "app_title": "E621 Downloader v1.0",
    "auth_frame": " Credentials (enter at every launch; leave empty for guest access) ",
    "site_label": "Site:",
    "user_label": "Username:",
    "key_label": "API Key:",
    "remember": "Remember (stored in plain text)",
    "lang_label": "Language:",
    "proxy_label": "Proxy:",
    "proxy_auto": "Auto (follow system)",
    "proxy_off": "No proxy",
    "proxy_custom": "Custom...",
    "proxy_addr_label": "Proxy address (for custom):",
    "proxy_hint": "e.g. http://127.0.0.1:7897",
    "tab_tag": "① Tag download",
    "tab_tag_page": "② Tag download by page",
    "tab_artist": "③ Artist grouped download",
    "tab_pool_seq": "④ Pool download (sequential)",
    "tab_pool_rev": "⑤ Pool download (reversed)",
    "tags_label": "Search tags:",
    "limit_label": "Count limit (empty = all):",
    "out_label": "Output folder (empty = auto):",
    "browse": "Browse...",
    "hint_tags": "e.g. aubrey_(iceink) or aubrey_(iceink) order:hot",
    "page_label": "Page (empty = all pages):",
    "hint_page": "Enter a page number to download only that page (max 320 posts/page); leave empty for all",
    "artist_label": "Artist tag:",
    "skip_others": "Skip posts that are not in any pool (download pool posts only)",
    "hint_artist": "Saved in a folder per pool; non-pool posts go to the 'others' folder",
    "pool_url_label": "Pool URL:",
    "hint_pool_seq": "e.g. https://e621.net/pools/12345; images named 1.jpg, 2.png ... in order",
    "hint_pool_rev": "Last post -> 1.jpg, second-last -> 2.png ... (reversed numbering)",
    "start_btn": "▶ Start",
    "stop_btn": "■ Stop",
    "status_idle": "Idle",
    "status_running": "Running...",
    "status_stopping": "Stopping... (waiting for current request)",
    "status_done": "Done (idle)",
    "status_stopped": "Stopped",
    "log_frame": " Log ",
    "msg_running": "A task is already running; stop it or wait for it to finish.",
    "msg_need_tags": "Please enter search tags.",
    "msg_need_artist": "Please enter the artist tag.",
    "msg_need_pool": "Please enter a valid pool URL (should contain /pools/).",
    "msg_limit_int": "{label} must be an integer.",
    "msg_limit_pos": "{label} must be a positive integer.",
    "field_limit": "Count limit",
    "field_page": "Page",
    "msg_unknown_tab": "Unknown tab.",
    "msg_param_error": "Invalid parameters",
    "msg_task_start": "Starting task: {name}",
    "msg_task_done": "===== Task finished =====",
    "msg_task_error": "Task error: {err}",
    "msg_init_error": "Initialization failed: {err}",
    "msg_proxy_enabled": "Proxy enabled: {p}",
    "msg_proxy_direct": "No proxy (direct connection)",
    "msg_logged_in": "Authenticated to {site}",
    "msg_guest": "Warning: empty username/API key; running as guest on {site} (some content may be restricted)",
    "msg_stop_requested": "Stop requested; will abort after the current download finishes.",
    "msg_lang_switched": "Language switched: {lang}",
}

LANGS = ("zh", "en")
LANG_NAMES = ("中文", "English")


def set_lang(lang: str) -> None:
    """切换当前语言：'zh' 或 'en'。"""
    global _CURRENT
    _CURRENT = lang if lang in LANGS else "zh"


def get_lang() -> str:
    return _CURRENT


def t(key: str, **kwargs) -> str:
    """取当前语言的字符串；支持 {name} 占位符。"""
    table = EN if _CURRENT == "en" else ZH
    s = table.get(key)
    if s is None:
        s = ZH.get(key, key)
    if kwargs:
        try:
            return s.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return s
    return s
