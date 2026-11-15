#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线功能测试：用模拟 API 验证核心逻辑（无需联网）。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core


class FakeResp:
    def __init__(self, data):
        self._d = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._d

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def iter_content(self, chunk_size=8192):
        yield b"fakedata"

    @property
    def content(self):
        return b"{}"


class FakeSession:
    def __init__(self):
        self.api_base = "https://e621.net"
        self.posts = [
            {"id": 1001, "file": {"url": "https://cdn/1001.png", "ext": "png"}, "pools": [7]},
            {"id": 1002, "file": {"url": "https://cdn/1002.jpg", "ext": "jpg"}, "pools": [7]},
            {"id": 1003, "sample": {"url": "https://cdn/1003.jpg", "ext": "jpg"}},
        ]
        self.pool = {"pool": {"id": 7, "name": "test_pool", "post_ids": [1001, 1002, 1003]}}

    def get(self, url, params=None, stream=False, timeout=None):
        if url.endswith("/posts.json"):
            tags = (params or {}).get("tags", "")
            if tags.startswith("id:"):
                ids = [int(x) for x in tags[3:].split(",")]
                return FakeResp({"posts": [p for p in self.posts if p["id"] in ids]})
            return FakeResp({"posts": self.posts})
        if "pools/" in url:
            return FakeResp(self.pool)
        return FakeResp({})


class FakeBigIdSession(FakeSession):
    """帖子 id 故意用 6 位 + 7 位混合（贴近真实 e621），验证 id 补零与续传隔离。"""

    def __init__(self):
        super().__init__()
        self.posts = [
            {"id": 600001, "file": {"url": "https://cdn/a.png", "ext": "png"}, "pools": [7]},
            {"id": 7001002, "file": {"url": "https://cdn/b.jpg", "ext": "jpg"}, "pools": [7]},
        ]
        self.pool = {"pool": {"id": 7, "name": "test_pool",
                              "post_ids": [600001, 7001002]}}


class FakeShuffledPoolSession(FakeSession):
    """pool 的 post_ids 和 API 返回顺序不同，验证顺序命名按 post_ids 排。"""

    def __init__(self):
        super().__init__()
        # posts 列表是 1001(png) / 1002(jpg) / 1003(jpg)，pool 里故意写成 1002,1001,1003
        self.pool = {"pool": {"id": 7, "name": "shuffled",
                              "post_ids": [1002, 1001, 1003]}}


def names(d):
    return sorted(f.name for f in Path(d).iterdir() if f.is_file())


class FakeMultiPoolSession(FakeSession):
    """两个**同名** Pool（id 11 / 12）+ 一个 others，用于验证名单排序与目录消歧。"""

    def __init__(self):
        super().__init__()
        self.posts = [
            {"id": 2001, "file": {"url": "https://cdn/2001.png", "ext": "png"}, "pools": [11]},
            {"id": 2002, "file": {"url": "https://cdn/2002.png", "ext": "png"}, "pools": [12]},
            {"id": 2003, "file": {"url": "https://cdn/2003.png", "ext": "png"}, "pools": [11]},
            {"id": 2004, "file": {"url": "https://cdn/2004.png", "ext": "png"}},
        ]
        self.pools = {
            11: {"pool": {"id": 11, "name": "Same", "post_ids": [2001, 2003]}},
            12: {"pool": {"id": 12, "name": "Same", "post_ids": [2002]}},
        }

    def get(self, url, params=None, stream=False, timeout=None):
        if "pools/" in url:
            pid = int(url.rstrip("/").split("/")[-1].replace(".json", ""))
            return FakeResp(self.pools[pid])
        return super().get(url, params=params, stream=stream, timeout=timeout)


def main():
    s = FakeSession()
    logs = []

    out = Path(tempfile.mkdtemp())
    core.download_by_tags(s, "rating:s", output_dir=str(out), limit=3, workers=1, log=logs.append)
    print("[tags 1st run ]", names(out))
    assert names(out) == ["001.png", "002.jpg", "003.jpg"], names(out)

    core.download_by_tags(s, "rating:s", output_dir=str(out), limit=3, workers=1, log=logs.append)
    print("[tags resume  ]", names(out))
    assert names(out) == ["001.png", "002.jpg", "003.jpg"], names(out)

    out2 = Path(tempfile.mkdtemp())
    core.download_pool(s, "https://e621.net/pools/12345", output_dir=str(out2), reverse=False, log=logs.append)
    print("[pool forward ]", names(out2))
    assert names(out2) == ["001.png", "002.jpg", "003.jpg"], names(out2)

    out3 = Path(tempfile.mkdtemp())
    core.download_pool(s, "https://e621.net/pools/12345", output_dir=str(out3), reverse=True, log=logs.append)
    print("[pool reverse ]", names(out3))
    assert names(out3) == ["001.jpg", "002.jpg", "003.png"], names(out3)

    out4 = Path(tempfile.mkdtemp())
    core.download_artist(s, "test_artist", output_root=str(out4), log=logs.append)
    files = sorted(str(Path(p).relative_to(out4)).replace("\\", "/")
                   for p in Path(out4).rglob("*") if p.is_file())
    print("[artist       ]", files)
    # pool 目录用顺序编号，others 用帖子 id
    assert "test_pool/001.png" in files and "test_pool/002.jpg" in files, files
    assert "test_pool/003.jpg" in files, files
    assert "others/1003.jpg" in files, files

    # 取消测试
    from threading import Event
    out5 = Path(tempfile.mkdtemp())
    cancel = Event()
    cancel.set()
    core.download_by_tags(s, "rating:s", output_dir=str(out5), limit=3, workers=1,
                          log=logs.append, cancel=cancel)
    print("[cancel       ]", names(out5))
    assert names(out5) == [], names(out5)

    # 分页数量参数（page + page_size）
    out6 = Path(tempfile.mkdtemp())
    core.download_by_tags(s, "rating:s", output_dir=str(out6), page=1, page_size=40,
                          workers=2, log=logs.append)
    print("[page_size    ]", names(out6))
    assert names(out6) == ["001.png", "002.jpg", "003.jpg"], names(out6)

    # Pool 并发下载（workers=4）编号仍正确
    out7 = Path(tempfile.mkdtemp())
    core.download_pool(s, "https://e621.net/pools/12345", output_dir=str(out7),
                       reverse=False, workers=4, log=logs.append)
    print("[pool threaded]", names(out7))
    assert names(out7) == ["001.png", "002.jpg", "003.jpg"], names(out7)

    out8 = Path(tempfile.mkdtemp())
    core.download_pool(s, "https://e621.net/pools/12345", output_dir=str(out8),
                       reverse=True, workers=4, log=logs.append)
    print("[pool rev thrd]", names(out8))
    assert names(out8) == ["001.jpg", "002.jpg", "003.png"], names(out8)

    # Pool 顺序模式断点续传：已有 2 个文件时只补剩余，不重复下载
    out9 = Path(tempfile.mkdtemp())
    core.download_pool(s, "https://e621.net/pools/12345", output_dir=str(out9),
                       reverse=False, workers=4, log=logs.append)
    (out9 / "001.png").write_bytes(b"x")
    (out9 / "002.jpg").write_bytes(b"x")
    n_before = len(names(out9))
    core.download_pool(s, "https://e621.net/pools/12345", output_dir=str(out9),
                       reverse=False, workers=4, log=logs.append)
    print("[pool resume  ]", names(out9))
    assert names(out9) == ["001.png", "002.jpg", "003.jpg"], names(out9)
    assert len(names(out9)) == n_before, "断点续传不应新增重复文件"

    # ---- 艺术家：扫描名单（有序 + 同名 Pool 消歧）----
    s2 = FakeMultiPoolSession()
    items = core.scan_artist(s2, "multi_artist", log=logs.append)
    dirs = [it["dir"] for it in items]
    print("[scan items   ]", [(it["kind"], it["name"], it["dir"], it["count"]) for it in items])
    assert dirs == ["Same_11", "Same_12", "others"], dirs
    assert len(set(dirs)) == len(dirs), "同名 Pool 的目录必须两两不同"

    # ---- 只下载勾选的项（第 1 个同名 Pool + others，跳过第 2 个）----
    out10 = Path(tempfile.mkdtemp())
    core.download_artist_items(s2, [items[0], items[2]], output_root=str(out10), log=logs.append)
    files = sorted(str(Path(p).relative_to(out10)).replace("\\", "/")
                   for p in Path(out10).rglob("*") if p.is_file())
    print("[selected     ]", files)
    assert "Same_11/001.png" in files and "Same_11/002.png" in files, files
    assert "others/2004.png" in files, files          # others 用帖子 id
    assert not any(f.startswith("Same_12") for f in files), files

    # ---- 全量下载（download_artist）与扫描走同一套目录规则 ----
    out11 = Path(tempfile.mkdtemp())
    core.download_artist(s2, "multi_artist", output_root=str(out11), log=logs.append)
    files11 = sorted(str(Path(p).relative_to(out11)).replace("\\", "/")
                     for p in Path(out11).rglob("*") if p.is_file())
    print("[artist full  ]", files11)
    assert {"Same_11/001.png", "Same_11/002.png", "Same_12/001.png",
            "others/2004.png"} <= set(files11), files11

    # ---- 命名方式：零填充宽度 / 按 id / 两者混在同一目录 ----
    print("[seq_width     ]", [(n, core.seq_width(n)) for n in (9, 99, 999, 1000, 99999)])
    assert core.seq_width(9) == 3
    assert core.seq_width(999) == 3
    assert core.seq_width(1000) == 4
    assert core.seq_width(99999) == 5

    # 目录里已有 3 位序号时，宽度取 max(按总数算, 已有宽度)，避免同目录宽度混杂
    out12 = Path(tempfile.mkdtemp())
    (out12 / "001.png").write_bytes(b"x")
    (out12 / "999.png").write_bytes(b"x")
    print("[width resume  ]", core.detect_seq_width(out12, 1000))
    assert core.detect_seq_width(out12, 1000) == 4

    # 按 id 命名：文件名就是帖子 id
    s3 = FakeBigIdSession()
    out13 = Path(tempfile.mkdtemp())
    core.download_pool(s3, "https://e621.net/pools/12345", output_dir=str(out13),
                       reverse=False, log=logs.append, naming="id")
    print("[pool by id    ]", names(out13))
    assert names(out13) == ["0600001.png", "7001002.jpg"], names(out13)

    # id 命名 + 反转：反转会被忽略（id 是固定的，反转只是换个序号起点）
    out14 = Path(tempfile.mkdtemp())
    core.download_pool(s3, "https://e621.net/pools/12345", output_dir=str(out14),
                       reverse=True, log=logs.append, naming="id")
    print("[id + reverse  ]", names(out14))
    assert names(out14) == ["0600001.png", "7001002.jpg"], names(out14)

    # 关键回归：同一目录先按 id 下过、再切顺序编号 -> id 文件不能当成序号
    out15 = Path(tempfile.mkdtemp())
    core.download_pool(s3, "https://e621.net/pools/12345", output_dir=str(out15),
                       reverse=False, log=logs.append, naming="id")
    core.download_pool(s3, "https://e621.net/pools/12345", output_dir=str(out15),
                       reverse=False, log=logs.append, naming="seq")
    got = names(out15)
    print("[id then seq   ]", got)
    assert got == ["001.png", "002.jpg", "0600001.png", "7001002.jpg"], got

    # 关键回归：顺序命名必须按 pool 的 post_ids 排，而不是 API 返回顺序
    # （API 实测是 id 降序返回的；这里 post_ids 故意写成 1002,1001,1003）
    s4 = FakeShuffledPoolSession()
    out16 = Path(tempfile.mkdtemp())
    core.download_pool(s4, "https://e621.net/pools/12345", output_dir=str(out16),
                       log=logs.append, naming="seq")
    got16 = names(out16)
    print("[pool order    ]", got16)
    # 1002 是 jpg -> 001.jpg；1001 是 png -> 002.png；1003 是 jpg -> 003.jpg
    assert got16 == ["001.jpg", "002.png", "003.jpg"], got16

    print("\nALL OFFLINE TESTS PASSED")


if __name__ == "__main__":
    main()
