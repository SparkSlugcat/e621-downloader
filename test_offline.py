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


def names(d):
    return sorted(f.name for f in Path(d).iterdir() if f.is_file())


def main():
    s = FakeSession()
    logs = []

    out = Path(tempfile.mkdtemp())
    core.download_by_tags(s, "rating:s", output_dir=str(out), limit=3, workers=1, log=logs.append)
    print("[tags 1st run ]", names(out))
    assert names(out) == ["1.png", "2.jpg", "3.jpg"], names(out)

    core.download_by_tags(s, "rating:s", output_dir=str(out), limit=3, workers=1, log=logs.append)
    print("[tags resume  ]", names(out))
    assert names(out) == ["1.png", "2.jpg", "3.jpg"], names(out)

    out2 = Path(tempfile.mkdtemp())
    core.download_pool(s, "https://e621.net/pools/12345", output_dir=str(out2), reverse=False, log=logs.append)
    print("[pool forward ]", names(out2))
    assert names(out2) == ["1.png", "2.jpg", "3.jpg"], names(out2)

    out3 = Path(tempfile.mkdtemp())
    core.download_pool(s, "https://e621.net/pools/12345", output_dir=str(out3), reverse=True, log=logs.append)
    print("[pool reverse ]", names(out3))
    assert names(out3) == ["1.jpg", "2.jpg", "3.png"], names(out3)

    out4 = Path(tempfile.mkdtemp())
    core.download_artist(s, "test_artist", output_root=str(out4), log=logs.append)
    files = sorted(str(Path(p).relative_to(out4)).replace("\\", "/")
                   for p in Path(out4).rglob("*") if p.is_file())
    print("[artist       ]", files)
    assert "test_pool/1001.png" in files and "test_pool/1002.jpg" in files
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
    assert names(out6) == ["1.png", "2.jpg", "3.jpg"], names(out6)

    # Pool 并发下载（workers=4）编号仍正确
    out7 = Path(tempfile.mkdtemp())
    core.download_pool(s, "https://e621.net/pools/12345", output_dir=str(out7),
                       reverse=False, workers=4, log=logs.append)
    print("[pool threaded]", names(out7))
    assert names(out7) == ["1.png", "2.jpg", "3.jpg"], names(out7)

    out8 = Path(tempfile.mkdtemp())
    core.download_pool(s, "https://e621.net/pools/12345", output_dir=str(out8),
                       reverse=True, workers=4, log=logs.append)
    print("[pool rev thrd]", names(out8))
    assert names(out8) == ["1.jpg", "2.jpg", "3.png"], names(out8)

    # Pool 顺序模式断点续传：已有 2 个文件时只补剩余，不重复下载
    out9 = Path(tempfile.mkdtemp())
    core.download_pool(s, "https://e621.net/pools/12345", output_dir=str(out9),
                       reverse=False, workers=4, log=logs.append)
    (out9 / "1.png").write_bytes(b"x")
    (out9 / "2.jpg").write_bytes(b"x")
    n_before = len(names(out9))
    core.download_pool(s, "https://e621.net/pools/12345", output_dir=str(out9),
                       reverse=False, workers=4, log=logs.append)
    print("[pool resume  ]", names(out9))
    assert names(out9) == ["1.png", "2.jpg", "3.jpg"], names(out9)
    assert len(names(out9)) == n_before, "断点续传不应新增重复文件"

    print("\nALL OFFLINE TESTS PASSED")


if __name__ == "__main__":
    main()
