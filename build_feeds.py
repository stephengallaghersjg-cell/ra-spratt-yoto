#!/usr/bin/env python3
"""Build ten Yoto-compatible feeds, excluding previously heard Nanny Piggins."""
import copy
import datetime as dt
import math
import os
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import format_datetime

SOURCE = "https://feeds.buzzsprout.com/852289.rss"
OUT = "feeds"
VOLUMES = 10
MAX_YOTO_ITEMS = 25
BASE = "https://raw.githubusercontent.com/stephengallaghersjg-cell/ra-spratt-yoto/main/feeds"

req = urllib.request.Request(SOURCE, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=30) as r:
    root = ET.fromstring(r.read())

channel = root.find("channel")
original = list(reversed(channel.findall("item")))  # oldest first
items = [item for item in original if "nanny piggins" not in (item.findtext("title") or "").casefold()]
removed = len(original) - len(items)
if len(items) > VOLUMES * MAX_YOTO_ITEMS:
    raise RuntimeError(f"{len(items)} episodes exceed {VOLUMES} Yoto feeds x {MAX_YOTO_ITEMS} episodes; refusing to silently omit any")

# Distribute the episodes over the TEN existing RSS URLs, without exceeding Yoto's 25-item cap.
base_size, extra = divmod(len(items), VOLUMES)
sizes = [base_size] * (VOLUMES - extra) + [base_size + 1] * extra
os.makedirs(OUT, exist_ok=True)
for fn in os.listdir(OUT):
    if fn.endswith(".xml"):
        os.remove(os.path.join(OUT, fn))

cursor = 0
for vol, size in enumerate(sizes, 1):
    chunk = items[cursor:cursor + size]
    a, b = cursor + 1, cursor + len(chunk)
    cursor += size
    newroot = copy.deepcopy(root)
    ch = newroot.find("channel")
    for it in ch.findall("item"):
        ch.remove(it)
    ch.find("title").text = f"R.A. Spratt Vol. {vol:02d} — Other Stories {a:03d}–{b:03d}"
    if ch.find("description") is not None:
        ch.find("description").text = "Non-Nanny Piggins stories in original chronological order, with reverse artificial dates for Yoto playback."
    # Yoto sorts podcasts newest first; reverse artificial dates make the OLDEST story appear first.
    anchor = dt.datetime(2026, 2, 9, 12, tzinfo=dt.timezone.utc)
    for index, item in enumerate(chunk):
        it = copy.deepcopy(item)
        pub = it.find("pubDate")
        if pub is None:
            pub = ET.SubElement(it, "pubDate")
        pub.text = format_datetime(anchor - dt.timedelta(days=index), usegmt=True)
        ch.append(it)
    ET.ElementTree(newroot).write(
        os.path.join(OUT, f"ra-spratt-vol-{vol:02d}.xml"),
        encoding="utf-8", xml_declaration=True
    )

with open("FEEDS.md", "w", encoding="utf-8") as f:
    f.write("# R.A. Spratt Yoto feeds — non-Nanny Piggins stories\\n\\n")
    f.write(f"{len(original)} source episodes; {removed} Nanny Piggins titles excluded; {len(items)} remaining across {VOLUMES} existing feeds.\\n\\n")
    for vol, size in enumerate(sizes, 1):
        start = sum(sizes[:vol-1]) + 1
        end = start + size - 1
        f.write(f"- **Vol. {vol:02d} — Episodes {start:03d}–{end:03d} ({size})** — {BASE}/ra-spratt-vol-{vol:02d}.xml\\n")
print(f"Generated {VOLUMES} feeds: {len(items)} remaining episodes, {removed} excluded")
