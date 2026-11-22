#!/usr/bin/env python3
"""Rebuild previously hidden Nanny Piggins episodes plus complete multipart stories."""
import copy
import datetime as dt
import html
import math
import os
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import format_datetime, parsedate_to_datetime

REPO = "stephengallaghersjg-cell/ra-spratt-yoto"
ARCHIVE_COMMIT = "1384852b3fdf7df7f7a670330964d4d4d41c3973"
BASE = f"https://raw.githubusercontent.com/{REPO}/main/nanny-piggins-hidden"
ARCHIVE_BASE = f"https://raw.githubusercontent.com/{REPO}/{ARCHIVE_COMMIT}/feeds"
OUT = "nanny-piggins-hidden"
PER_VOLUME = 25

# Extra complete stories: identify companions from the ORIGINAL 400-episode archive.
# Pairs that are already both hidden are retained automatically.
STORY_GROUPS = [
    ["Nanny Piggins and the Campaign Strategy - Part 1", "Nanny Piggins and the Campaign Strategy - Part 2"],
    ["Nanny Piggins and the Grandmaster", "Nanny Piggins and the Grandmaster - Part 2"],
    ["Nanny Piggins and the Daring Rescue - Part 1", "Nanny Piggins and the Daring Rescue - Part 2"],
    ["'Boris and the Big Snore' with Nanny Piggins - Part 1", "'Boris and the Big Snore' with Nanny Piggins - Part 2"],
    ["Nanny Piggins and the Egg Challenge", "Nanny Piggins and the Eggs - Part 2"],
    ["'Joseph and his Rainbow Coat' as told by Nanny Piggins - Part 1 - Holiday Rerun",
     "'Joseph and his Rainbow Coat' as told by Nanny Piggins - Part 2 - Holiday Rerun"],
]

all_items = []
hidden = []
source_root = None
for vol in range(1, 11):
    url = f"{ARCHIVE_BASE}/ra-spratt-vol-{vol:02d}.xml"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        root = ET.fromstring(response.read())
    if source_root is None:
        source_root = root
    items = root.find("channel").findall("item")
    if len(items) != 40:
        raise RuntimeError(f"Archived volume {vol} has {len(items)} entries, expected 40")
    all_items.extend(items)
    hidden.extend(item for item in items[25:] if "nanny piggins" in (item.findtext("title") or "").casefold())

if len(all_items) != 400 or len(hidden) != 83:
    raise RuntimeError(f"Unexpected archive counts: {len(all_items)} total / {len(hidden)} hidden Nanny Piggins")

by_title = {}
for item in all_items:
    by_title.setdefault(html.unescape(item.findtext("title") or "").strip(), []).append(item)
def guid(item):
    return (item.findtext("guid") or "").strip()
selected = {guid(item): item for item in hidden}
added_companions = []
for group in STORY_GROUPS:
    for title in group:
        matches = by_title.get(title, [])
        if len(matches) != 1:
            raise RuntimeError(f"Cannot uniquely find companion story episode {title!r}: {len(matches)}")
        item = matches[0]
        if guid(item) not in selected:
            selected[guid(item)] = item
            added_companions.append(title)

# Keep original chronological order, with ties stable in archive order.
chosen = list(selected.values())
chosen.sort(key=lambda item: parsedate_to_datetime(item.findtext("pubDate")).timestamp())
if len({guid(item) for item in chosen}) != len(chosen):
    raise RuntimeError("Duplicate GUIDs")
if len(chosen) > 4 * PER_VOLUME:
    raise RuntimeError("More than four volumes required; review grouping before publishing")

# Keep each two-part story in a single volume when feasible.
groups = []
used = set()
for group in STORY_GROUPS:
    ids = {guid(by_title[title][0]) for title in group}
    if ids & used:
        raise RuntimeError("Overlapping story groups")
    used |= ids
    groups.append(ids)
blocks = []
for item in chosen:
    identifier = guid(item)
    if identifier in used:
        if not any(identifier in block_ids for block_ids, _ in blocks):
            block_ids = next(g for g in groups if identifier in g)
            block_items = [x for x in chosen if guid(x) in block_ids]
            blocks.append((block_ids, block_items))
    else:
        blocks.append(({identifier}, [item]))
# Sort story blocks by their first publication date, preserving parts inside each block.
blocks.sort(key=lambda block: min(parsedate_to_datetime(x.findtext("pubDate")).timestamp() for x in block[1]))
volumes = []
current = []
for _, block_items in blocks:
    if len(current) + len(block_items) > PER_VOLUME:
        volumes.append(current)
        current = []
    current.extend(block_items)
if current:
    volumes.append(current)

os.makedirs(OUT, exist_ok=True)
for filename in os.listdir(OUT):
    if filename.endswith(".xml"):
        os.remove(os.path.join(OUT, filename))

anchor = dt.datetime(2026, 2, 9, 12, tzinfo=dt.timezone.utc)
for number, items in enumerate(volumes, 1):
    root = copy.deepcopy(source_root)
    channel = root.find("channel")
    for item in channel.findall("item"):
        channel.remove(item)
    channel.find("title").text = f"Nanny Piggins — Previously Hidden Vol. {number:02d}"
    description = channel.find("description")
    if description is not None:
        description.text = "Previously hidden Nanny Piggins episodes, plus necessary multipart story companions; oldest first."
    for index, item in enumerate(items):
        episode = copy.deepcopy(item)
        pub = episode.find("pubDate")
        if pub is None:
            pub = ET.SubElement(episode, "pubDate")
        pub.text = format_datetime(anchor - dt.timedelta(days=index), usegmt=True)
        channel.append(episode)
    ET.ElementTree(root).write(f"{OUT}/nanny-piggins-hidden-vol-{number:02d}.xml", encoding="utf-8", xml_declaration=True)

with open("NANNY_PIGGINS_HIDDEN_FEEDS.md", "w", encoding="utf-8") as f:
    f.write("# Nanny Piggins — previously hidden episodes\n\n")
    f.write(f"Archived catalogue: 400 episodes; 83 Nanny Piggins entries hidden by the 25-of-40 limit.\n")
    f.write(f"Added {len(added_companions)} story companions, for {len(chosen)} total episodes in {len(volumes)} volumes.\n\n")
    for number, items in enumerate(volumes, 1):
        f.write(f"## Volume {number:02d} ({len(items)} episodes)\n\n")
        f.write(f"{BASE}/nanny-piggins-hidden-vol-{number:02d}.xml\n\n")
        for item in items:
            f.write(f"- {html.unescape(item.findtext('title') or '')}\n")
        f.write("\n")
    f.write("## Extra companion episodes (previously visible)\n\n")
    for title in added_companions:
        f.write(f"- {title}\n")
print(f"Created {len(volumes)} volumes with {len(chosen)} episodes: 83 hidden plus {len(added_companions)} companions")
