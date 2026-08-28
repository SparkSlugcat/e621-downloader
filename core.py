#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
e621 / e926 统一下载引擎
==============================================
将原 5 个脚本的功能统一封装为可调用函数：
    e6_scraper.py            ->  download_by_tags(workers=1)
    e6_taged_page_scraper.py ->  download_by_tags(page=..., workers=2)
    e6_artist.py             ->  download_artist(...)
    pool_scraper.py          ->  download_pool(reverse=False)
    e621.py                  ->  download_pool(reverse=True)

API 用户名 / Key 由调用方传入（不再硬编码），留空则以游客身份访问。
日志文案通过 i18n 模块支持中英双语（默认中文，可用 i18n.set_lang("en") 切换）。
"""

import os
import re
import time
import threading
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import i18n

# ---------- 默认配置 ----------
POSTS_PER_REQUEST = 320          # API 单次最多帖子数
REQUEST_DELAY = 1.0              # API 请求间隔（秒）
MAX_RETRIES = 3
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1",
    "Connection": "keep-alive",
}

LogFunc = Callable[[str], None]
CancelEvent = Optional[threading.Event]


def _fix_proxy_scheme(url: str) -> str:
    """修正 Windows 注册表代理的 https 前缀问题。

    注册表里 https 代理常写成 https://127.0.0.1:port，但本机 Clash 类
    代理实际是普通 HTTP 代理；https 前缀会让 urllib3 对代理本身做 TLS
    握手而导致失败。对回环地址统一改用 http:// 前缀。
    """
    low = url.strip().lower()
    if low.startswith("https://"):
        try:
            from urllib.parse import urlparse
            host = (urlparse(url).hostname or "").lower()
        except Exception:
            host = ""
        if host in ("127.0.0.1", "localhost", "::1") or host.startswith("127."):
            return "http://" + url[len("https://"):]
    return url


def detect_proxy() -> str:
    """自动检测可用代理，返回代理 URL 字符串；找不到返回空字符串。

    检测顺序：
      1. 环境变量 HTTPS_PROXY / HTTP_PROXY
      2. Windows 系统代理设置（注册表，例如 127.0.0.1:7897）
    若检测到的代理不可用，可在 GUI 中手动指定或关闭。
    """
    # 1. 环境变量
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        v = os.environ.get(key, "").strip()
        if v:
            return _fix_proxy_scheme(v)
    # 2. Windows 系统代理（注册表）
    try:
        import urllib.request
        proxies = urllib.request.getproxies()
        for key in ("https", "http"):
            v = (proxies.get(key) or "").strip()
            if v and "://" in v:
                return _fix_proxy_scheme(v)
    except Exception:
        pass
    return ""


def normalize_proxy(proxy: Optional[str]) -> str:
    """把用户在 GUI 里填的代理整理成标准 URL；'off'/'direct'/'自动' 分别处理。"""
    p = (proxy or "").strip()
    if not p:
        return ""
    low = p.lower()
    if low in ("off", "direct", "none", "不使用代理", "关闭"):
        return ""
    if low in ("auto", "自动", "跟随系统", "系统"):
        return detect_proxy()
    if "://" not in p:
        p = "http://" + p
    return _fix_proxy_scheme(p)


# ============================================================
# 基础工具
# ============================================================

def create_session(api_user: str, api_key: str,
                   api_base: str = "https://e621.net",
                   proxy: Optional[str] = None) -> requests.Session:
    """创建带重试和认证的会话。api_user/api_key 留空则以游客身份访问。

    proxy: 代理设置。
      None / ""        -> 自动检测（环境变量 -> Windows 系统代理）
      "off"/"direct"   -> 不使用代理，直连
      其它字符串        -> 视为代理 URL（如 http://127.0.0.1:7897）
    """
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    headers = dict(DEFAULT_HEADERS)
    headers["Referer"] = api_base.rstrip("/") + "/"
    session.headers.update(headers)
    if api_user and api_key:
        session.auth = (api_user, api_key)
    session.api_base = api_base.rstrip("/")   # 供内部函数取用

    # ---- 代理设置 ----
    # 注意：requests 2.27 下仅设置 session.proxies 不生效（环境代理合并逻辑会
    # 把请求变成直连），必须同时关闭 trust_env 才会使用显式代理。
    if proxy is None or str(proxy).strip() == "":
        detected = detect_proxy()
        if detected:
            session.proxies = {"http": detected, "https": detected}
            session.trust_env = False
    else:
        p = normalize_proxy(proxy)
        if p:
            session.proxies = {"http": p, "https": p}
            session.trust_env = False
    return session


def sanitize_filename(name: str) -> str:
    """去除文件名中的非法字符，保证文件夹名合法。"""
    name = re.sub(r'[\\/*?:"<>|]', '_', name)   # Windows 非法字符
    name = re.sub(r'[\s.]+$', '', name)         # 去除末尾空格或点
    name = name.strip()
    if not name:
        name = "untitled"
    return name


def extract_pool_id(pool_url: str) -> str:
    """从 Pool 页面 URL 中提取 Pool ID。"""
    path = urlparse(pool_url).path.rstrip("/")
    parts = path.split("/")
    if "pools" in parts:
        idx = parts.index("pools")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    raise ValueError(i18n.t("core_pool_url_invalid", url=pool_url))


def find_existing_max(out_dir: Path) -> int:
    """扫描目录中已有的数字文件名，返回最大序号（用于断点续传）。"""
    max_num = 0
    try:
        for f in out_dir.iterdir():
            if f.is_file() and f.stem.isdigit():
                try:
                    n = int(f.stem)
                except ValueError:
                    continue
                if n > max_num:
                    max_num = n
    except OSError:
        pass
    return max_num


def _cancelled(cancel: CancelEvent, log: LogFunc = print) -> bool:
    if cancel is not None and cancel.is_set():
        log(i18n.t("core_cancelled"))
        return True
    return False


# ============================================================
# API 请求
# ============================================================

def fetch_post_ids(session: requests.Session, tags: str,
                   limit: Optional[int] = None, page: Optional[int] = None,
                   page_size: Optional[int] = None,
                   log: LogFunc = print, cancel: CancelEvent = None) -> List[int]:
    """获取匹配标签的所有帖子 ID（自动翻页）。

    page:      指定页码则只返回该页；不指定则遍历所有页。
    limit:     只取前 N 个帖子（与 page 同用时不建议）。
    page_size: 指定单页帖子数（仅与 page 搭配时生效，如 40/80/120/200/320）。
    """
    all_ids: List[int] = []
    current_page = page if page else 1
    consecutive_failures = 0
    MAX_PAGE_FAILURES = 5   # 同一页连续失败次数上限，超过则中止避免无限卡住
    while True:
        if _cancelled(cancel, log):
            break
        if page_size:
            request_limit = page_size
        else:
            request_limit = min(limit, POSTS_PER_REQUEST) if limit else POSTS_PER_REQUEST
        params = {
            "tags": tags,
            "limit": request_limit,
            "page": current_page,
            "filter_id": 0,          # 关闭内容过滤器，与网页端一致
        }
        try:
            resp = session.get(f"{session.api_base}/posts.json", params=params)
            resp.raise_for_status()
            data = resp.json()
            posts = data.get("posts", [])
            consecutive_failures = 0
            if not posts:
                break
            for post in posts:
                all_ids.append(post["id"])
            log(i18n.t("core_page_fetched", page=current_page,
                       n=len(posts), total=len(all_ids)))

            if page is not None:
                break                      # 指定了页码，只取一页
            if limit is not None or len(posts) < POSTS_PER_REQUEST:
                break                      # 最后一页
            current_page += 1
            time.sleep(REQUEST_DELAY)
        except requests.exceptions.JSONDecodeError:
            log(i18n.t("core_bad_json", head=resp.content[:200]))
            break
        except requests.RequestException as e:
            consecutive_failures += 1
            if consecutive_failures >= MAX_PAGE_FAILURES:
                log(i18n.t("core_fetch_fail", page=current_page, err=e))
                log(i18n.t("core_too_many_fails"))
                break
            log(i18n.t("core_fetch_fail_retry", page=current_page, err=e))
            time.sleep(5)
            continue
    return all_ids


def fetch_posts_batch(session: requests.Session, post_ids: List[int]) -> List[dict]:
    """批量获取帖子详细信息（一次最多 POSTS_PER_REQUEST 个）。"""
    if not post_ids:
        return []
    ids_str = ",".join(str(pid) for pid in post_ids)
    params = {
        "tags": f"id:{ids_str}",
        "limit": POSTS_PER_REQUEST,
    }
    resp = session.get(f"{session.api_base}/posts.json", params=params)
    resp.raise_for_status()
    data = resp.json()
    return data.get("posts", [])


def get_download_url(post: dict) -> Tuple[Optional[str], Optional[str]]:
    """提取可下载 URL 和扩展名。优先 file.url，其次 sample.url。"""
    file_data = post.get("file") or {}
    url = file_data.get("url")
    ext = file_data.get("ext")
    if url:
        return url, ext

    sample_data = post.get("sample") or {}
    url = sample_data.get("url")
    if url:
        ext = sample_data.get("ext") or ext or "jpg"
        return url, ext
    return None, None


def build_downloadable(session: requests.Session, post_ids: List[int],
                       log: LogFunc = print, cancel: CancelEvent = None) -> Tuple[List[Tuple[int, str, str]], List[int]]:
    """批量获取作品详情，构建可下载列表。

    返回 (downloadable, failed_ids)：
        downloadable: [(post_id, url, ext), ...]
        failed_ids:   无任何可用 URL 的作品 ID
    """
    downloadable: List[Tuple[int, str, str]] = []
    failed_ids: List[int] = []
    total = len(post_ids)
    for i in range(0, total, POSTS_PER_REQUEST):
        if _cancelled(cancel, log):
            break
        batch_ids = post_ids[i:i + POSTS_PER_REQUEST]
        log(i18n.t("core_batch_fetching", a=i + 1,
                   b=min(i + POSTS_PER_REQUEST, total), total=total))
        try:
            posts = fetch_posts_batch(session, batch_ids)
        except requests.RequestException:
            log(i18n.t("core_batch_fail"))
            time.sleep(5)
            try:
                posts = fetch_posts_batch(session, batch_ids)
            except requests.RequestException as e2:
                log(i18n.t("core_batch_fail2", err=e2))
                continue

        for post in posts:
            pid = post.get("id")
            url, ext = get_download_url(post)
            if url:
                downloadable.append((pid, url, ext or "jpg"))
            else:
                failed_ids.append(pid)
        time.sleep(REQUEST_DELAY)

    log(i18n.t("core_downloadable_count", n=len(downloadable))
        + (i18n.t("core_no_url_suffix", n=len(failed_ids)) if failed_ids else ""))
    return downloadable, failed_ids


# ============================================================
# 功能一：标签下载（原 e6_scraper.py / e6_taged_page_scraper.py）
# ============================================================

def download_by_tags(session: requests.Session, tags: str,
                     output_dir: Optional[str] = None,
                     limit: Optional[int] = None, page: Optional[int] = None,
                     page_size: Optional[int] = None, workers: int = 4,
                     log: LogFunc = print, cancel: CancelEvent = None) -> bool:
    """下载匹配标签的所有图片，按 1.jpg, 2.png ... 顺序编号。

    workers=1 时为顺序下载（等价原 e6_scraper.py）；
    workers>1 时为并发下载（等价原 e6_taged_page_scraper.py）。
    page_size 仅在指定 page 时生效：自定义每页帖子数（如 40/80/120/200/320）。
    """
    tags = (tags or "").strip()
    if not tags:
        log(i18n.t("core_tags_empty"))
        return False
    log(i18n.t("core_tags_label", tags=tags)
        + (i18n.t("core_page_only", page=page) if page else "")
        + (i18n.t("core_limit_only", n=limit) if limit else ""))

    all_ids = fetch_post_ids(session, tags, limit=limit, page=page,
                             page_size=(page_size if page else None),
                             log=log, cancel=cancel)
    if not all_ids:
        log(i18n.t("core_no_matches"))
        return False
    log(i18n.t("core_found_posts", n=len(all_ids)))

    out = Path(output_dir) if output_dir else Path(sanitize_filename(tags.replace(" ", "_")))
    out.mkdir(parents=True, exist_ok=True)

    downloadable, failed_ids = build_downloadable(session, all_ids, log=log, cancel=cancel)
    if not downloadable:
        log(i18n.t("core_no_images"))
        return False

    existing_max = find_existing_max(out)
    start_index = existing_max + 1
    if existing_max > 0:
        log(i18n.t("core_resume_from", n=existing_max, m=start_index))

    downloaded = skipped = 0
    download_failed: List[int] = []

    if workers and workers > 1:
        # ---------- 并发下载 ----------
        tasks = []
        for idx, (pid, url, ext) in enumerate(downloadable):
            if _cancelled(cancel, log):
                break
            if idx < existing_max:
                continue
            target_index = start_index + (idx - existing_max)
            filepath = out / f"{target_index}.{ext}"
            if filepath.exists():
                log(i18n.t("core_task_exists", i=target_index,
                           total=len(downloadable), pid=pid, name=filepath.name))
                skipped += 1
                continue
            tasks.append((pid, url, filepath, target_index))
        log(i18n.t("core_task_pending", n=len(tasks)))

        def dl_task(pid: int, url: str, filepath: Path, target_index: int):
            if _cancelled(cancel, log):
                return "cancelled", pid, target_index
            try:
                with session.get(url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(filepath, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                os.utime(filepath, None)
                return "ok", pid, target_index
            except Exception as e:
                log(i18n.t("core_dl_fail", pid=pid, err=e))
                if filepath.exists():
                    try:
                        filepath.unlink()
                    except OSError:
                        pass
                return "fail", pid, target_index

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(dl_task, p, u, fp, i): (p, u, fp, i)
                       for p, u, fp, i in tasks}
            for future in as_completed(futures):
                status, pid, target_index = future.result()
                if status == "ok":
                    downloaded += 1
                    log(i18n.t("core_dl_done", i=target_index,
                               total=len(downloadable), pid=pid))
                elif status == "fail":
                    download_failed.append(pid)
    else:
        # ---------- 顺序下载 ----------
        for idx, (pid, url, ext) in enumerate(downloadable):
            if _cancelled(cancel, log):
                break
            if idx < existing_max:
                continue
            target_index = start_index + (idx - existing_max)
            filename = f"{target_index}.{ext}"
            filepath = out / filename
            if filepath.exists():
                log(i18n.t("core_task_exists", i=target_index,
                           total=len(downloadable), pid=pid, name=filename))
                skipped += 1
                continue
            log(i18n.t("core_dl_start", i=target_index, total=len(downloadable),
                       pid=pid, name=filename))
            try:
                with session.get(url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(filepath, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                os.utime(filepath, None)
                downloaded += 1
            except requests.RequestException as e:
                log(i18n.t("core_dl_fail_seq", err=e))
                download_failed.append(pid)
                if filepath.exists():
                    try:
                        filepath.unlink()
                    except OSError:
                        pass
            time.sleep(REQUEST_DELAY)

    log("\n" + i18n.t("core_done_header"))
    log(i18n.t("core_tags_summary", tags=tags))
    log(i18n.t("core_total_posts", n=len(all_ids)))
    log(i18n.t("core_success", n=downloaded))
    log(i18n.t("core_skipped", n=skipped))
    if download_failed:
        log(i18n.t("core_failed_ids", n=len(download_failed),
                   ids=", ".join(map(str, download_failed))))
    if failed_ids:
        log(i18n.t("core_no_url_ids", n=len(failed_ids),
                   ids=", ".join(map(str, failed_ids))))
    log(i18n.t("core_saved_to", path=out.resolve()))
    return True


# ============================================================
# 功能二：艺术家分组下载（原 e6_artist.py）
# ============================================================

def download_posts_to_dir(session: requests.Session, post_ids: List[int],
                          out_dir: Path, log: LogFunc = print,
                          cancel: CancelEvent = None) -> None:
    """把一批帖子下载到指定目录（并发 4 线程），文件名为帖子 ID。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    details: List[dict] = []
    for i in range(0, len(post_ids), POSTS_PER_REQUEST):
        if _cancelled(cancel, log):
            return
        batch = post_ids[i:i + POSTS_PER_REQUEST]
        try:
            details.extend(fetch_posts_batch(session, batch))
        except Exception as e:
            log(i18n.t("core_batch_info_fail", err=e))
        time.sleep(REQUEST_DELAY)

    if not details:
        log(i18n.t("core_no_post_info"))
        return

    def dl_one(post: dict):
        pid = post.get("id")
        file_url = (post.get("file") or {}).get("url")
        ext = (post.get("file") or {}).get("ext", "jpg")
        if not file_url:
            sample = post.get("sample") or {}
            file_url = sample.get("url")
            ext = sample.get("ext") or ext or "jpg"
        if not file_url:
            return False, pid
        filepath = out_dir / f"{pid}.{ext}"
        if filepath.exists():
            return True, pid
        try:
            with session.get(file_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            os.utime(filepath, None)
            return True, pid
        except Exception as e:
            log(i18n.t("core_post_dl_fail", pid=pid, err=e))
            if filepath.exists():
                try:
                    filepath.unlink()
                except OSError:
                    pass
            return False, pid

    success = fail = 0
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(dl_one, p) for p in details]
        for future in as_completed(futures):
            ok, _ = future.result()
            if ok:
                success += 1
            else:
                fail += 1
    log(i18n.t("core_posts_dir_done", ok=success, fail=fail))


def download_artist(session: requests.Session, artist_tag: str,
                    output_root: Optional[str] = None, skip_others: bool = False,
                    log: LogFunc = print, cancel: CancelEvent = None) -> bool:
    """下载指定艺术家的所有作品，按所属 Pool 分组保存。

    输出结构：
        艺术家标签/
            Pool名称1/...      （每个 Pool 单独文件夹，完整下载池内全部作品）
            Pool名称2/...
            others/...        （不属于任何 Pool 的作品；skip_others=True 时跳过）
    """
    artist_tag = (artist_tag or "").strip()
    if not artist_tag:
        log(i18n.t("core_artist_empty"))
        return False
    log(i18n.t("core_artist_label", tag=artist_tag))

    root_dir = Path(output_root) if output_root else Path(sanitize_filename(artist_tag))
    root_dir.mkdir(parents=True, exist_ok=True)

    log(i18n.t("core_fetching_artist"))
    all_ids = fetch_post_ids(session, artist_tag, log=log, cancel=cancel)
    if not all_ids:
        log(i18n.t("core_artist_no_posts"))
        return False
    log(i18n.t("core_found_posts", n=len(all_ids)))

    log(i18n.t("core_fetching_details"))
    posts_with_pool_info: List[dict] = []
    for i in range(0, len(all_ids), POSTS_PER_REQUEST):
        if _cancelled(cancel, log):
            break
        batch_ids = all_ids[i:i + POSTS_PER_REQUEST]
        try:
            posts_with_pool_info.extend(fetch_posts_batch(session, batch_ids))
        except Exception as e:
            log(i18n.t("core_info_fail", err=e))
        time.sleep(REQUEST_DELAY)

    pool_ids: set = set()
    posts_without_pool: List[int] = []
    for post in posts_with_pool_info:
        pools = post.get("pools") or []
        if pools:
            pool_ids.update(pools)
        else:
            posts_without_pool.append(post["id"])
    log(i18n.t("core_pool_info_summary", pools=len(pool_ids),
               posts=len(posts_without_pool)))

    # 下载每个 Pool 的全部作品
    for pool_id in pool_ids:
        if _cancelled(cancel, log):
            break
        log("\n" + i18n.t("core_processing_pool", pid=pool_id))
        try:
            resp = session.get(f"{session.api_base}/pools/{pool_id}.json")
            resp.raise_for_status()
            data = resp.json()
            pool_info = data.get("pool", data)
            pool_name = sanitize_filename(pool_info.get("name", f"pool_{pool_id}"))
            pool_post_ids = pool_info.get("post_ids", [])
            log(i18n.t("core_pool_name_count", name=pool_name, n=len(pool_post_ids)))
            download_posts_to_dir(session, pool_post_ids, root_dir / pool_name,
                                  log=log, cancel=cancel)
        except Exception as e:
            log(i18n.t("core_pool_fetch_fail", pid=pool_id, err=e))

    # 下载不属于任何池的帖子
    if posts_without_pool and not skip_others:
        log("\n" + i18n.t("core_downloading_others", n=len(posts_without_pool)))
        download_posts_to_dir(session, posts_without_pool, root_dir / "others",
                              log=log, cancel=cancel)
    elif skip_others:
        log("\n" + i18n.t("core_skipped_others", n=len(posts_without_pool)))

    log("\n" + i18n.t("core_all_done", path=root_dir.resolve()))
    return True


# ============================================================
# 功能三：Pool 下载（原 pool_scraper.py / e621.py）
# ============================================================

def download_pool(session: requests.Session, pool_url: str,
                  output_dir: Optional[str] = None, reverse: bool = False,
                  workers: int = 4,
                  log: LogFunc = print, cancel: CancelEvent = None) -> bool:
    """下载指定 Pool 中的所有图片，支持断点续传。

    reverse=False 时顺序编号（等价原 pool_scraper.py）；
    reverse=True  时反转编号，最后一张 -> 1.jpg（等价原 e621.py）。
    workers>1 时并发下载图片（API 请求仍保持串行与间隔）。
    """
    pool_url = (pool_url or "").strip()
    try:
        pool_id = extract_pool_id(pool_url)
    except ValueError as e:
        log(i18n.t("core_err", err=e))
        return False
    log(i18n.t("core_pool_id", pid=pool_id))

    log(i18n.t("core_fetching_pool"))
    try:
        resp = session.get(f"{session.api_base}/pools/{pool_id}.json")
        resp.raise_for_status()
        data = resp.json()
        pool_info = data.get("pool", data)
    except requests.RequestException as e:
        log(i18n.t("core_pool_fail", err=e))
        return False

    pool_name = pool_info.get("name", f"pool_{pool_id}")
    post_ids = pool_info.get("post_ids", [])
    if not post_ids:
        log(i18n.t("core_pool_empty"))
        return False
    log(i18n.t("core_pool_name", name=pool_name))
    log(i18n.t("core_post_count", n=len(post_ids)))

    out = Path(output_dir) if output_dir else Path(sanitize_filename(pool_name))
    out.mkdir(parents=True, exist_ok=True)

    log(i18n.t("core_fetching_details2"))
    downloadable, failed_ids = build_downloadable(session, post_ids, log=log, cancel=cancel)
    if not downloadable:
        log(i18n.t("core_no_downloadable"))
        return False

    existing_max = find_existing_max(out)
    start_index = existing_max + 1
    if existing_max > 0:
        log(i18n.t("core_resume_rev", n=existing_max, m=start_index,
                   rev=(i18n.t("core_rev_suffix") if reverse else "")))
    elif reverse:
        log(i18n.t("core_rev_start"))

    downloaded = skipped = 0
    download_failed: List[int] = []
    tasks: List[Tuple[int, int, str, Path]] = []   # (target_index, pid, url, filepath)

    if reverse:
        # ---------- 反转编号：最后一张 -> 1.jpg ----------
        processed_count = 0
        for pid, url, ext in reversed(downloadable):
            if _cancelled(cancel, log):
                break
            if processed_count < existing_max:      # 续传跳过已完成作品
                processed_count += 1
                continue
            target_index = start_index + (processed_count - existing_max)
            filepath = out / f"{target_index}.{ext}"
            if filepath.exists():
                log(i18n.t("core_post_exists", i=target_index,
                           total=len(downloadable), pid=pid, name=filepath.name))
                skipped += 1
                processed_count += 1
                continue
            tasks.append((target_index, pid, url, filepath))
            processed_count += 1
    else:
        # ---------- 顺序编号：1.jpg, 2.png ... ----------
        for idx, (pid, url, ext) in enumerate(downloadable):
            if _cancelled(cancel, log):
                break
            if idx < existing_max:                  # 续传跳过已完成作品
                continue
            target_index = start_index + (idx - existing_max)
            filepath = out / f"{target_index}.{ext}"
            if filepath.exists():
                log(i18n.t("core_post_exists", i=target_index,
                           total=len(downloadable), pid=pid, name=filepath.name))
                skipped += 1
                continue
            tasks.append((target_index, pid, url, filepath))

    log(i18n.t("core_task_pending", n=len(tasks)))

    def dl_task(target_index: int, pid: int, url: str, filepath: Path):
        if _cancelled(cancel, log):
            return "cancelled", pid, target_index
        try:
            with session.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            os.utime(filepath, None)
            return "ok", pid, target_index
        except Exception as e:
            log(i18n.t("core_dl_fail", pid=pid, err=e))
            if filepath.exists():
                try:
                    filepath.unlink()
                except OSError:
                    pass
            return "fail", pid, target_index

    if workers and workers > 1 and tasks:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(dl_task, i, p, u, fp): (p, u, fp, i)
                       for i, p, u, fp in tasks}
            for future in as_completed(futures):
                status, pid, target_index = future.result()
                if status == "ok":
                    downloaded += 1
                    log(i18n.t("core_dl_done", i=target_index,
                               total=len(downloadable), pid=pid))
                elif status == "fail":
                    download_failed.append(pid)
    else:
        # 单线程（保留逐条日志）
        for target_index, pid, url, filepath in tasks:
            if _cancelled(cancel, log):
                break
            log(i18n.t("core_post_dl", i=target_index, total=len(downloadable),
                       pid=pid, name=filepath.name))
            status, pid2, _ = dl_task(target_index, pid, url, filepath)
            if status == "ok":
                downloaded += 1
            elif status == "fail":
                download_failed.append(pid2)

    log("\n" + i18n.t("core_done_header"))
    log(i18n.t("core_pool_summary", name=pool_name, pid=pool_id))
    log(i18n.t("core_total_works", n=len(post_ids)))
    log(i18n.t("core_downloadable", n=len(downloadable)))
    log(i18n.t("core_success", n=downloaded))
    log(i18n.t("core_skipped", n=skipped))
    if download_failed:
        log(i18n.t("core_failed_ids", n=len(download_failed),
                   ids=", ".join(map(str, download_failed))))
    if failed_ids:
        log(i18n.t("core_no_url_ids", n=len(failed_ids),
                   ids=", ".join(map(str, failed_ids))))
    log(i18n.t("core_saved_to", path=out.resolve()))
    return True
