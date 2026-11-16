#!/usr/bin/env python3
"""Встраивает dictionary.json в app.html и собирает Wortblase.html (один файл, работает офлайн)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
d = json.loads((HERE.parent / "dictionary.json").read_text(encoding="utf-8"))
topics, seen, words = [], set(), []
for e in d["entries"]:
    key = (e["section"], e["unit"])
    if key not in seen:
        seen.add(key)
        topics.append([e["section"], e["unit"], e["topic_ru"], e["topic_en"]])
    pres = list(e["present"].values()) if e.get("present") else None
    words.append([e["id"], e["section"], e["unit"], e["type"], e["german"], e["ru"], e["en"],
                  e.get("plural"), e.get("forms") or [], pres, e.get("prefix")])
data = json.dumps({"topics": topics, "words": words}, ensure_ascii=False, separators=(",", ":"))
data = data.replace("</", "<\\/")
html = (HERE / "app.html").read_text(encoding="utf-8").replace("__DATA__", data, 1)
(HERE / "Wortblase.html").write_text(html, encoding="utf-8")
print(f"Wortblase.html: {len(html)//1024} KB, {len(words)} words")
