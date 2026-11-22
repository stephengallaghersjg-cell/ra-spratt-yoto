#!/usr/bin/env python3
"""Build independent Yoto feeds of Silly Stories for Kids episodes featuring Pim Pim."""
import copy
import datetime as dt
import html
import math
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import format_datetime, parsedate_to_datetime

SOURCE = "https://feeds.megaphone.fm/EUAET6896760602"
OUT = "pim-pim"
PER = 25
BASE = "https://raw.githubusercontent.com/stephengallaghersjg-cell/ra-spratt-yoto/main/pim-pim"
NS = {"content": "http://purl.org/rss/1.0/modules/content/"}

request = urllib.request.Request(SOURCE, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(request, timeout=60) as response:
    root = ET.fromstring(response.read())
channel = root.find("channel")
if channel is None:
    raise RuntimeError("Missing RSS channel")
items = channel.findall("item")
if len(items) < 100:
    raise RuntimeError(f"Unexpectedly short source feed ({len(items)} episodes)")

def text_for(item):
    fields = [item.findtext("title") or "", item.findtext("description") or "",
              item.findtext("content:encoded", default="", namespaces=NS)]
    return html.unescape(re.sub(r"<[^>]+>", " ", " ".join(fields)))

# Exclude generic promo links and boilerplate by matching story text only.
# Pim Pim appears under several spellings including Pim-Pim and Pimpim.
PATTERN = re.compile(r"\\bpim[\\s-]*pim\\b", re.I)
matches = [item for item in items if PATTERN.search(text_for(item))]
matches.sort(key=lambda item: parsedate_to_datetime(item.findtext("pubDate")).timestamp())
if not matches:
    raise RuntimeError("No Pim Pim episodes matched")

os.makedirs(OUT, exist_ok=True)
for filename in os.listdir(OUT):
    if filename.endswith(".xml"):
        os.remove(os.path.join(OUT, filename))
anchor = dt.datetime(2026, 2, 9, 12, tzinfo=dt.timezone.utc)
for start in range(0, len(matches), PER):
    chunk = matches[start:start+PER]
    vol = start // PER + 1
    newroot = copy.deepcopy(root)
    ch = newroot.find("channel")
    for item in ch.findall("item"):
        ch.remove(item)
    ch.find("title").text = f"Silly Stories — Pim Pim Vol. {vol:02d}"
    description = ch.find("description")
    if description is not None:
        description.text = "Pim Pim stories, oldest first, selected from episode titles and descriptions."
    for index, item in enumerate(chunk):
        it = copy.deepcopy(item)
        pub = it.find("pubDate")
        if pub is None:
            pub = ET.SubElement(it, "pubDate")
        pub.text = format_datetime(anchor - dt.timedelta(days=index), usegmt=True)
        ch.append(it)
    ET.ElementTree(newroot).write(
        os.path.join(OUT, f"pim-pim-vol-{vol:02d}.xml"),
        encoding="utf-8", xml_declaration=True)

with open("PIM_PIM_FEEDS.md", "w", encoding="utf-8") as f:
    f.write("# Pim Pim Yoto podcast feeds\\n\\n")
    f.write(f"Source episodes checked: {len(items)}. Episodes mentioning Pim Pim in title/description: {len(matches)}. Volumes: {math.ceil(len(matches)/PER)}.\\n\\n")
    for start in range(0, len(matches), PER):
        vol = start // PER + 1
        chunk = matches[start:start+PER]
        f.write(f"## Volume {vol:02d} ({len(chunk)} episodes)\\n\\n")
        f.write(f"{BASE}/pim-pim-vol-{vol:02d}.xml\\n\\n")
        for item in chunk:
            f.write(f"- {item.findtext('title') or '(Untitled)'}\\n")
        f.write("\\n")
print(f"Checked {len(items)} source episodes; found {len(matches)} Pim Pim matches in {math.ceil(len(matches)/PER)} volumes")
