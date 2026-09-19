#!/usr/bin/env python3
import copy, math, os, urllib.request
import xml.etree.ElementTree as ET

SOURCE = "https://feeds.buzzsprout.com/852289.rss"
OUT = "feeds"
PER = 10

req = urllib.request.Request(SOURCE, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=30) as r:
    data = r.read()

root = ET.fromstring(data)
channel = root.find("channel")
items = list(reversed(channel.findall("item")))  # oldest first
os.makedirs(OUT, exist_ok=True)
for fn in os.listdir(OUT):
    if fn.endswith(".xml"):
        os.remove(os.path.join(OUT, fn))

for start in range(0, len(items), PER):
    chunk = items[start:start+PER]
    a, b, vol = start+1, start+len(chunk), start//PER+1
    newroot = copy.deepcopy(root)
    ch = newroot.find("channel")
    for it in ch.findall("item"):
        ch.remove(it)
    if ch.find("title") is not None:
        ch.find("title").text = f"R.A. Spratt Vol. {vol:02d} — Episodes {a:03d}–{b:03d}"
    if ch.find("description") is not None:
        ch.find("description").text = f"Custom chronological volume {vol} of Bedtime Stories with R.A. Spratt. Episodes {a}–{b} from the official podcast feed."
    for it in reversed(chunk):
        ch.append(copy.deepcopy(it))
    ET.ElementTree(newroot).write(os.path.join(OUT, f"ra-spratt-vol-{vol:02d}.xml"), encoding="utf-8", xml_declaration=True)

base = "https://raw.githubusercontent.com/stephengallaghersjg-cell/ra-spratt-yoto/main/feeds"
with open("FEEDS.md", "w", encoding="utf-8") as f:
    f.write("# R.A. Spratt Yoto feeds\n\n")
    f.write(f"{len(items)} episodes found; {math.ceil(len(items)/PER)} chronological volumes.\n\n")
    for start in range(0, len(items), PER):
        a, b, vol = start+1, min(start+PER, len(items)), start//PER+1
        f.write(f"- **Vol. {vol:02d} — Episodes {a:03d}–{b:03d}** — {base}/ra-spratt-vol-{vol:02d}.xml\n")
print(f"Generated {math.ceil(len(items)/PER)} feeds from {len(items)} episodes")
