#!/usr/bin/env python3
"""Convert a Remark42 backup (gzipped JSON-lines) into Hugo data for the
archived-comments partial.

Usage:
    python3 tools/remark2data.py comments/backup-remark42.metamodel.blog-YYYYMMDD.gz

Writes data/archived_comments.json keyed by post path (e.g. "/posts/foo/"),
each entry a list of comments in thread order with a "depth" field.
"""
import sys, json, gzip, re
from pathlib import Path
from urllib.parse import urlparse

def main(backup_path):
    comments = []
    opener = gzip.open if backup_path.endswith(".gz") else open
    with opener(backup_path, "rt", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line or i == 0:  # first line is site/users metadata
                continue
            c = json.loads(line)
            if c.get("deleted") or c.get("delete"):
                continue
            path = urlparse(c["locator"]["url"]).path
            # very old comments predate the /blog/ -> /posts/ rename
            if path.startswith("/blog/"):
                path = "/posts/" + path[len("/blog/"):]
            comments.append({
                "id": c["id"],
                "pid": c.get("pid", ""),
                "path": path,
                "name": c["user"]["name"],
                # strip fractional seconds so Hugo's time() can parse it
                "time": re.sub(r"\.\d+", "", c["time"]),
                "html": c["text"],
                "score": c.get("score", 0),
            })

    # thread order: children directly after their parent, siblings by time
    by_post = {}
    for c in comments:
        by_post.setdefault(c["path"], []).append(c)

    result = {}
    for path, clist in by_post.items():
        children = {}
        for c in sorted(clist, key=lambda c: c["time"]):
            children.setdefault(c["pid"], []).append(c)
        ordered = []
        def walk(pid, depth):
            for c in children.get(pid, []):
                ordered.append({
                    "name": c["name"], "time": c["time"],
                    "html": c["html"], "depth": depth, "score": c["score"],
                })
                walk(c["id"], depth + 1)
        walk("", 0)
        # orphans (their parent comment was deleted): treat as top-level threads
        all_ids = {c["id"] for c in clist}
        for pid in sorted(children):
            if pid and pid not in all_ids:
                walk(pid, 0)
        result[path] = ordered

    out = Path(__file__).resolve().parent.parent / "data" / "archived_comments.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    total = sum(len(v) for v in result.values())
    print(f"wrote {out} : {total} comments on {len(result)} posts")

if __name__ == "__main__":
    main(sys.argv[1])
