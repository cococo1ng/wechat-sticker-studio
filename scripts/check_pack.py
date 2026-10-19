#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""表情包成品检查（零依赖，只用标准库）。

用法：
    python check_pack.py <成品目录>
    python check_pack.py <成品目录> --expect 24

只读文件，不改任何东西。逐张读 PNG 头判断尺寸 / 体积 / 透明度，
按文件名归类后对照微信表情开放平台的规格表输出 PASS / FAIL。

控制台若是 GBK，中文文件名可能显示为乱码——那是终端编码问题，
不影响判定。需要正常显示请先执行 `chcp 65001`。
"""

import argparse
import os
import struct
import sys

# 规格：(宽, 高, 体积上限KB, 是否必须有 alpha)
SPEC = {
    "MAIN":   (240, 240, 500, True),
    "THUMB":  (120, 120, 50,  True),
    "COVER":  (240, 240, 500, True),
    "ICON":   (50,  50,  30,  True),
    "BANNER": (750, 400, 500, False),
    "TIP":    (750, 560, None, False),
    "THANKS": (750, 750, None, False),
}

PNG_SIG = b"\x89PNG\r\n\x1a\n"
SKIP_WORDS = ("preview", "预览", "拼版", "sheet", "contact")


def read_png(path):
    """读 PNG 头 -> (宽, 高, 位深, 颜色类型, 有无 tRNS)。非 PNG 返回 None。"""
    with open(path, "rb") as f:
        head = f.read(33)
        if len(head) < 33 or head[:8] != PNG_SIG:
            return None
        w, h, depth, ctype = struct.unpack(">IIBB", head[16:26])
        has_trns = False
        total = os.path.getsize(path)
        pos = 8
        while pos < total and pos < 4 * 1024 * 1024:
            f.seek(pos)
            raw_len = f.read(4)
            if len(raw_len) < 4:
                break
            ln = struct.unpack(">I", raw_len)[0]
            raw_type = f.read(4)
            if raw_type == b"tRNS":
                has_trns = True
                break
            if raw_type in (b"IDAT", b"IEND"):
                break
            pos += 12 + ln
        return w, h, depth, ctype, has_trns


def kind_of(name, in_main_dir):
    low = name.lower()
    if any(s in low for s in SKIP_WORDS):
        return None
    if "赞赏引导" in name or "tip" in low:
        return "TIP"
    if "赞赏致谢" in name or "致谢" in name or "thanks" in low:
        return "THANKS"
    if "横幅" in name or "banner" in low:
        return "BANNER"
    if "封面" in name or "cover" in low:
        return "COVER"
    if "图标" in name or "icon" in low:
        return "ICON"
    if "缩略" in name or "thumb" in low:
        return "THUMB"
    if in_main_dir or name[:2].isdigit():
        return "MAIN"
    return None


def alpha_ok(ctype, has_trns):
    return ctype in (4, 6) or has_trns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="成品目录")
    ap.add_argument("--expect", type=int, default=None, help="期望主图张数，如 16 / 24")
    args = ap.parse_args()

    root = args.root
    if not os.path.isdir(root):
        print("NOT A DIRECTORY: %s" % root)
        return 2

    files = []
    for base, _dirs, names in os.walk(root):
        for n in names:
            if n.lower().endswith(".png"):
                files.append((os.path.join(base, n), base))

    if not files:
        print("NO PNG FOUND: %s" % root)
        return 2

    rows, fails, main_count, skipped = [], 0, 0, 0
    for path, base in sorted(files):
        name = os.path.basename(path)
        in_main = "主图" in base
        kind = kind_of(name, in_main)
        if kind is None:
            skipped += 1
            continue

        spec = SPEC[kind]
        if kind == "MAIN":
            main_count += 1

        info = read_png(path)
        kb = os.path.getsize(path) / 1024.0
        if info is None:
            rows.append((name, kind, "-", "%.1fKB" % kb, "-", "FAIL not-a-png"))
            fails += 1
            continue

        w, h, _depth, ctype, trns = info
        has_a = alpha_ok(ctype, trns)
        problems = []

        if (w, h) != (spec[0], spec[1]):
            problems.append("want %dx%d" % (spec[0], spec[1]))
        if spec[2] is not None and kb > spec[2]:
            problems.append("over %dKB" % spec[2])
        if spec[3] and not has_a:
            problems.append("no-alpha")
        stem = os.path.splitext(name)[0]
        if stem.isdigit() and len(stem) < 2:
            problems.append("name-not-zero-padded")

        status = "PASS" if not problems else "FAIL " + ", ".join(problems)
        if problems:
            fails += 1
        rows.append((name, kind, "%dx%d" % (w, h), "%.1fKB" % kb,
                     "yes" if has_a else "no", status))

    print("%-30s %-7s %-10s %-9s %-5s %s" % ("FILE", "TYPE", "SIZE", "WEIGHT", "ALPHA", "RESULT"))
    print("-" * 96)
    for r in rows:
        print("%-30s %-7s %-10s %-9s %-5s %s" % r)

    print("\nMAIN count: %d   (skipped %d preview files)" % (main_count, skipped))
    if args.expect is not None:
        if main_count == args.expect:
            print("PASS count == %d" % args.expect)
        else:
            print("FAIL count should be %d" % args.expect)
            fails += 1

    print("\nTOTAL %d file(s), FAIL %d" % (len(rows), fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
