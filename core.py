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
    raise ValueError(f"无法从 URL 中提取 Pool ID: {pool_url}")


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
        log("已收到停止请求，任务中止。")
        return True
    return False


# ============================================================
# API 请求
# ============================================================

def fetch_post_ids(session: requests.Session, tags: str,
                   limit: Optional[int] = None, page: Optional[int] = None,
                   log: LogFunc = print, cancel: CancelEvent = None) -> List[int]:
    """获取匹配标签的所有帖子 ID（自动翻页）。

    page:  指定页码则只返回该页；不指定则遍历所有页。
    limit: 只取前 N 个帖子（与 page 同用时不建议）。
    """
    all_ids: List[int] = []
    current_page = page if page else 1
    consecutive_failures = 0
    MAX_PAGE_FAILURES = 5   # 同一页连续失败次数上限，超过则中止避免无限卡住
    while True:
        if _cancelled(cancel, log):
            break
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
            log(f"  第 {current_page} 页，获取到 {len(posts)} 个帖子（累计 {len(all_ids)}）")

            if page is not None:
                break                      # 指定了页码，只取一页
            if limit is not None or len(posts) < POSTS_PER_REQUEST:
                break                      # 最后一页
            current_page += 1
            time.sleep(REQUEST_DELAY)
        except requests.exceptions.JSONDecodeError:
            log(f"    响应不是 JSON，前200字节: {resp.content[:200]}")
            break
        except requests.RequestException as e:
            consecutive_failures += 1
            if consecutive_failures >= MAX_PAGE_FAILURES:
                log(f"获取帖子列表失败（第 {current_page} 页）: {e}")
                log("连续失败次数过多，已中止。请检查网络/代理设置后重试。")
                break
            log(f"获取帖子列表失败（第 {current_page} 页）: {e}，等待 5 秒后重试...")
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
        log(f"  获取批次 ({i + 1}-{min(i + POSTS_PER_REQUEST, total)}/{total})")
        try:
            posts = fetch_posts_batch(session, batch_ids)
        except requests.RequestException:
            log("  批次请求失败，等待 5 秒后重试...")
            time.sleep(5)
            try:
                posts = fetch_posts_batch(session, batch_ids)
            except requests.RequestException as e2:
                log(f"  重试仍失败: {e2}，跳过该批次")
                continue

        for post in posts:
            pid = post.get("id")
            url, ext = get_download_url(post)
            if url:
                downloadable.append((pid, url, ext or "jpg"))
            else:
                failed_ids.append(pid)
        time.sleep(REQUEST_DELAY)

    log(f"  可下载作品: {len(downloadable)}"
        + (f"，无可用 URL: {len(failed_ids)}" if failed_ids else ""))
    return downloadable, failed_ids


# ============================================================
# 功能一：标签下载（原 e6_scraper.py / e6_taged_page_scraper.py）
# ============================================================

def download_by_tags(session: requests.Session, tags: str,
                     output_dir: Optional[str] = None,
                     limit: Optional[int] = None, page: Optional[int] = None,
                     workers: int = 1,
                     log: LogFunc = print, cancel: CancelEvent = None) -> bool:
    """下载匹配标签的所有图片，按 1.jpg, 2.png ... 顺序编号。

    workers=1 时为顺序下载（等价原 e6_scraper.py）；
    workers>1 时为并发下载（等价原 e6_taged_page_scraper.py，默认 2 线程）。
    """
    tags = (tags or "").strip()
    if not tags:
        log("错误：标签不能为空。")
        return False
    log(f"搜索标签: {tags}" + (f"（仅第 {page} 页）" if page else "")
        + (f"（仅前 {limit} 个）" if limit else ""))

    all_ids = fetch_post_ids(session, tags, limit=limit, page=page, log=log, cancel=cancel)
    if not all_ids:
        log("没有找到匹配的帖子。")
        return False
    log(f"共找到 {len(all_ids)} 个帖子")

    out = Path(output_dir) if output_dir else Path(sanitize_filename(tags.replace(" ", "_")))
    out.mkdir(parents=True, exist_ok=True)

    downloadable, failed_ids = build_downloadable(session, all_ids, log=log, cancel=cancel)
    if not downloadable:
        log("没有可下载的图片。")
        return False

    existing_max = find_existing_max(out)
    start_index = existing_max + 1
    if existing_max > 0:
        log(f"检测到已有 {existing_max} 个文件，从序号 {start_index} 继续下载")

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
                log(f"[{target_index}/{len(downloadable)}] #{pid} -> {filepath.name} 已存在，跳过")
                skipped += 1
                continue
            tasks.append((pid, url, filepath, target_index))
        log(f"待下载任务数: {len(tasks)}")

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
                log(f"  下载 #{pid} 失败: {e}")
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
                    log(f"[{target_index}/{len(downloadable)}] 下载 #{pid} 完成")
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
                log(f"[{target_index}/{len(downloadable)}] #{pid} -> {filename} 已存在，跳过")
                skipped += 1
                continue
            log(f"[{target_index}/{len(downloadable)}] 下载 #{pid} -> {filename}")
            try:
                with session.get(url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(filepath, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                os.utime(filepath, None)
                downloaded += 1
            except requests.RequestException as e:
                log(f"  下载失败: {e}")
                download_failed.append(pid)
                if filepath.exists():
                    try:
                        filepath.unlink()
                    except OSError:
                        pass
            time.sleep(REQUEST_DELAY)

    log("\n===== 下载完成 =====")
    log(f"标签: {tags}")
    log(f"总计帖子: {len(all_ids)}")
    log(f"成功下载: {downloaded}")
    log(f"已存在跳过: {skipped}")
    if download_failed:
        log(f"下载失败: {len(download_failed)} (ID: {', '.join(map(str, download_failed))})")
    if failed_ids:
        log(f"无可用 URL: {len(failed_ids)} (ID: {', '.join(map(str, failed_ids))})")
    log(f"文件保存至: {out.resolve()}")
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
            log(f"  批量获取帖子信息失败: {e}")
        time.sleep(REQUEST_DELAY)

    if not details:
        log("  没有找到帖子信息")
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
            log(f"  下载帖子 #{pid} 失败: {e}")
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
    log(f"  下载完成：成功 {success}，失败/跳过 {fail}")


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
        log("错误：艺术家标签不能为空。")
        return False
    log(f"艺术家标签: {artist_tag}")

    root_dir = Path(output_root) if output_root else Path(sanitize_filename(artist_tag))
    root_dir.mkdir(parents=True, exist_ok=True)

    log("正在获取艺术家所有帖子 ID...")
    all_ids = fetch_post_ids(session, artist_tag, log=log, cancel=cancel)
    if not all_ids:
        log("没有找到任何帖子。")
        return False
    log(f"共找到 {len(all_ids)} 个帖子")

    log("正在获取帖子详细信息以提取 Pool 信息...")
    posts_with_pool_info: List[dict] = []
    for i in range(0, len(all_ids), POSTS_PER_REQUEST):
        if _cancelled(cancel, log):
            break
        batch_ids = all_ids[i:i + POSTS_PER_REQUEST]
        try:
            posts_with_pool_info.extend(fetch_posts_batch(session, batch_ids))
        except Exception as e:
            log(f"批量获取帖子信息失败: {e}")
        time.sleep(REQUEST_DELAY)

    pool_ids: set = set()
    posts_without_pool: List[int] = []
    for post in posts_with_pool_info:
        pools = post.get("pools") or []
        if pools:
            pool_ids.update(pools)
        else:
            posts_without_pool.append(post["id"])
    log(f"发现 {len(pool_ids)} 个相关 Pool，{len(posts_without_pool)} 个帖子不属于任何池")

    # 下载每个 Pool 的全部作品
    for pool_id in pool_ids:
        if _cancelled(cancel, log):
            break
        log(f"\n正在处理 Pool ID: {pool_id}")
        try:
            resp = session.get(f"{session.api_base}/pools/{pool_id}.json")
            resp.raise_for_status()
            data = resp.json()
            pool_info = data.get("pool", data)
            pool_name = sanitize_filename(pool_info.get("name", f"pool_{pool_id}"))
            pool_post_ids = pool_info.get("post_ids", [])
            log(f"  Pool 名称: {pool_name}, 作品数: {len(pool_post_ids)}")
            download_posts_to_dir(session, pool_post_ids, root_dir / pool_name,
                                  log=log, cancel=cancel)
        except Exception as e:
            log(f"  获取 Pool {pool_id} 失败: {e}")

    # 下载不属于任何池的帖子
    if posts_without_pool and not skip_others:
        log(f"\n下载 {len(posts_without_pool)} 个无 Pool 帖子到 others 文件夹")
        download_posts_to_dir(session, posts_without_pool, root_dir / "others",
                              log=log, cancel=cancel)
    elif skip_others:
        log(f"\n已跳过 {len(posts_without_pool)} 个无 Pool 帖子（已勾选跳过）")

    log("\n全部完成！文件保存在: " + str(root_dir.resolve()))
    return True


# ============================================================
# 功能三：Pool 下载（原 pool_scraper.py / e621.py）
# ============================================================

def download_pool(session: requests.Session, pool_url: str,
                  output_dir: Optional[str] = None, reverse: bool = False,
                  log: LogFunc = print, cancel: CancelEvent = None) -> bool:
    """下载指定 Pool 中的所有图片，支持断点续传。

    reverse=False 时顺序编号（等价原 pool_scraper.py）；
    reverse=True  时反转编号，最后一张 -> 1.jpg（等价原 e621.py）。
    """
    pool_url = (pool_url or "").strip()
    try:
        pool_id = extract_pool_id(pool_url)
    except ValueError as e:
        log(f"错误: {e}")
        return False
    log(f"解析到 Pool ID: {pool_id}")

    log("正在获取 Pool 信息...")
    try:
        resp = session.get(f"{session.api_base}/pools/{pool_id}.json")
        resp.raise_for_status()
        data = resp.json()
        pool_info = data.get("pool", data)
    except requests.RequestException as e:
        log(f"获取 Pool 信息失败: {e}")
        return False

    pool_name = pool_info.get("name", f"pool_{pool_id}")
    post_ids = pool_info.get("post_ids", [])
    if not post_ids:
        log("该 Pool 中没有作品。")
        return False
    log(f"Pool 名称: {pool_name}")
    log(f"作品数量: {len(post_ids)}")

    out = Path(output_dir) if output_dir else Path(sanitize_filename(pool_name))
    out.mkdir(parents=True, exist_ok=True)

    log("正在获取作品详细信息...")
    downloadable, failed_ids = build_downloadable(session, post_ids, log=log, cancel=cancel)
    if not downloadable:
        log("没有可下载的作品。")
        return False

    existing_max = find_existing_max(out)
    start_index = existing_max + 1
    if existing_max > 0:
        log(f"检测到已有 {existing_max} 个文件，从序号 {start_index} 开始续传"
            + ("（反转顺序）" if reverse else ""))
    elif reverse:
        log("开始下载，图片将按 Pool 反转顺序编号：最后一张 -> 1.jpg, 倒数第二张 -> 2.png ...")

    downloaded = skipped = 0
    download_failed: List[int] = []

    if reverse:
        # ---------- 反转编号（原 e621.py 逻辑） ----------
        processed_count = 0
        for pid, url, ext in reversed(downloadable):
            if _cancelled(cancel, log):
                break
            if processed_count < existing_max:      # 续传跳过已完成作品
                processed_count += 1
                continue
            target_index = start_index + (processed_count - existing_max)
            filename = f"{target_index}.{ext}"
            filepath = out / filename
            if filepath.exists():
                log(f"[{target_index}/{len(downloadable)}] 作品 #{pid} -> {filename} 已存在，跳过")
                skipped += 1
                processed_count += 1
                continue
            log(f"[{target_index}/{len(downloadable)}] 下载作品 #{pid} -> {filename}")
            try:
                with session.get(url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(filepath, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                os.utime(filepath, None)
                downloaded += 1
            except requests.RequestException as e:
                log(f"  下载失败: {e}")
                download_failed.append(pid)
                if filepath.exists():
                    try:
                        filepath.unlink()
                    except OSError:
                        pass
            processed_count += 1
            time.sleep(REQUEST_DELAY)
    else:
        # ---------- 顺序编号（原 pool_scraper.py 逻辑） ----------
        for idx, (pid, url, ext) in enumerate(downloadable):
            if _cancelled(cancel, log):
                break
            target_index = start_index + idx
            filename = f"{target_index}.{ext}"
            filepath = out / filename
            if filepath.exists():
                log(f"[{target_index}/{start_index + len(downloadable) - 1}] 作品 #{pid} -> {filename} 已存在，跳过")
                skipped += 1
                continue
            log(f"[{target_index}] 下载作品 #{pid} -> {filename}")
            try:
                with session.get(url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(filepath, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                os.utime(filepath, None)
                downloaded += 1
            except requests.RequestException as e:
                log(f"  下载失败: {e}")
                download_failed.append(pid)
                if filepath.exists():
                    try:
                        filepath.unlink()
                    except OSError:
                        pass
            time.sleep(REQUEST_DELAY)

    log("\n===== 下载完成 =====")
    log(f"Pool: {pool_name} (ID: {pool_id})")
    log(f"总计作品: {len(post_ids)}")
    log(f"可下载作品: {len(downloadable)}")
    log(f"成功下载: {downloaded}")
    log(f"已存在跳过: {skipped}")
    if download_failed:
        log(f"下载失败: {len(download_failed)} (ID: {', '.join(map(str, download_failed))})")
    if failed_ids:
        log(f"无可用 URL: {len(failed_ids)} (ID: {', '.join(map(str, failed_ids))})")
    log(f"文件保存至: {out.resolve()}")
    return True
