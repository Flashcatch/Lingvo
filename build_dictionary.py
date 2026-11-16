#!/usr/bin/env python3
"""Собирает словарь из vocab_source.txt.

Создаёт:
  dictionary.json — машиночитаемый словарь (основа для будущего тренажёра)
  СЛОВАРЬ.md      — словарь для чтения, по разделам и темам

Запуск:  python3 build_dictionary.py
"""
import json
import re
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "vocab_source.txt"

PERSONS = ["ich", "du", "er/sie/es", "wir", "ihr", "sie/Sie"]
ARTICLE = {"m": "der", "f": "die", "n": "das", "pl": "die"}
TYPE_RU = {
    "m": "сущ. м. р.", "f": "сущ. ж. р.", "n": "сущ. ср. р.", "pl": "сущ. мн. ч.",
    "v": "глагол", "vs": "глагол (отделяемый)", "vpast": "глагол (прош. вр.)",
    "adj": "прилагательное", "adv": "наречие", "pron": "местоимение",
    "prep": "предлог", "conj": "союз", "num": "числительное", "art": "артикль",
    "q": "вопрос. слово", "phr": "фраза", "name": "имя собств.", "part": "частица",
}

# Полностью неправильные глаголы в настоящем времени
FULL = {
    "sein":    ["bin", "bist", "ist", "sind", "seid", "sind"],
    "haben":   ["habe", "hast", "hat", "haben", "habt", "haben"],
    "werden":  ["werde", "wirst", "wird", "werden", "werdet", "werden"],
    "wissen":  ["weiß", "weißt", "weiß", "wissen", "wisst", "wissen"],
    "tun":     ["tue", "tust", "tut", "tun", "tut", "tun"],
    "können":  ["kann", "kannst", "kann", "können", "könnt", "können"],
    "müssen":  ["muss", "musst", "muss", "müssen", "müsst", "müssen"],
    "wollen":  ["will", "willst", "will", "wollen", "wollt", "wollen"],
    "sollen":  ["soll", "sollst", "soll", "sollen", "sollt", "sollen"],
    "dürfen":  ["darf", "darfst", "darf", "dürfen", "dürft", "dürfen"],
    "mögen":   ["mag", "magst", "mag", "mögen", "mögt", "mögen"],
    "möchten": ["möchte", "möchtest", "möchte", "möchten", "möchtet", "möchten"],
}
# Смена корневой гласной: (du, er/sie/es)
STEM_CHANGE = {
    "essen": ("isst", "isst"), "nehmen": ("nimmst", "nimmt"),
    "sehen": ("siehst", "sieht"), "lesen": ("liest", "liest"),
    "sprechen": ("sprichst", "spricht"), "fahren": ("fährst", "fährt"),
    "schlafen": ("schläfst", "schläft"), "laufen": ("läufst", "läuft"),
    "tragen": ("trägst", "trägt"), "waschen": ("wäschst", "wäscht"),
    "geben": ("gibst", "gibt"), "helfen": ("hilfst", "hilft"),
    "treffen": ("triffst", "trifft"), "fangen": ("fängst", "fängt"),
    "laden": ("lädst", "lädt"), "gefallen": ("gefällst", "gefällt"),
}
IMPERSONAL = {"regnen", "schneien"}          # только «es regnet»
REFLEXIVE = ["mich", "dich", "sich", "uns", "euch", "sich"]
INDECLINABLE_ADJ = {"rosa", "lila", "orange", "super", "fit", "klar", "möglich"}


def present(inf):
    """Спряжение в настоящем времени (Präsens): список из 6 форм."""
    if inf in FULL:
        return list(FULL[inf])
    if inf.endswith(("ern", "eln")):              # wandern → wander-
        stem = inf[:-1]
        forms = [stem + "e", stem + "st", stem + "t", inf, stem + "t", inf]
        if inf.endswith("eln"):                   # sammeln → ich sammle
            forms[0] = inf[:-3] + "le"
        return forms
    stem = inf[:-2] if inf.endswith("en") else inf[:-1]
    if re.search(r"(t|d|[^aeiouälmnrh][mn])$", stem):   # arbeit-, find-, öffn-, regn-
        du, er, ihr = stem + "est", stem + "et", stem + "et"
    elif re.search(r"(s|ß|z|x)$", stem):          # heiß-, tanz-
        du, er, ihr = stem + "t", stem + "t", stem + "t"
    else:
        du, er, ihr = stem + "st", stem + "t", stem + "t"
    wir = inf
    if inf in STEM_CHANGE:
        du, er = STEM_CHANGE[inf]
    return [stem + "e", du, er, wir, ihr, wir]


def conjugate(german, typ):
    reflexive = german.startswith("sich ")
    core = german[5:] if reflexive else german
    prefix = ""
    if typ == "vs":
        prefix, base = core.split("|")
    else:
        base = core
    forms = present(base)
    out = []
    for i, f in enumerate(forms):
        parts = [f]
        if reflexive:
            parts.append(REFLEXIVE[i])
        if prefix:
            parts.append(prefix)
        out.append(" ".join(parts))
    if base in IMPERSONAL:
        return {"es": out[2]}
    return dict(zip(PERSONS, out))


def adj_forms(base):
    if base in INDECLINABLE_ADJ:
        return [base]
    stem = base
    if base.endswith("e"):                                  # müde → müd- + e
        stem = base[:-1]
    elif base.endswith("el") and base not in {"hell"}:        # dunkel → dunkl-
        stem = base[:-2] + "l"
    elif base.endswith("er") and base in {"teuer", "sauber"}:
        stem = base[:-2] + "r" if base == "teuer" else base
    if base == "best":
        return ["beste", "besten", "bester", "bestes", "bestem"]
    return list(dict.fromkeys([base] + [stem + e for e in ("e", "en", "er", "es", "em")]))


def parse():
    entries, section, unit, topic_ru, topic_en = [], None, None, None, None
    seen = set()
    for line in SRC.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or (line.startswith("#") and not line.startswith("##")):
            continue
        if line.startswith("##"):
            section, unit, topic_ru, topic_en = [x.strip() for x in line[2:].split("|")]
            continue
        typ, german, extra, en, ru = [x.strip() for x in line.split("|", 4)] if line.count("|") >= 4 else (None,) * 5
        if typ == "vs":   # «an|kommen» содержит лишний «|» — собираем обратно
            cols = [x.strip() for x in line.split("|")]
            typ, german, extra, en, ru = cols[0], cols[1] + "|" + cols[2], cols[3], cols[4], cols[5]
        key = (typ, german.replace("|", ""))
        if key in seen:
            continue
        seen.add(key)
        e = OrderedDict(
            id=len(entries) + 1, section=int(section), unit=int(unit),
            topic_ru=topic_ru, topic_en=topic_en, type=typ,
            german=german.replace("|", ""), en=en, ru=ru,
        )
        if typ in ARTICLE:
            e["article"] = ARTICLE[typ]
            e["plural"] = None if extra in ("-", "") else extra
            e["forms"] = [german] + ([extra] if extra not in ("-", "", german) else [])
        elif typ in ("v", "vs"):
            if typ == "vs":
                e["prefix"] = german.split("|")[0].replace("sich ", "")
            e["reflexive"] = german.startswith("sich ")
            e["present"] = conjugate(german, typ)
            e["forms"] = sorted(set(e["present"].values()))
        elif typ == "vpast":
            e["forms"] = [german] + [x.strip() for x in extra.split(",") if x.strip()]
        elif typ == "adj":
            more = [x.strip() for x in extra.split(",") if x.strip()]
            e["forms"] = [german] + more if more else adj_forms(german)
        else:
            e["forms"] = [german] + [x.strip() for x in extra.split(",") if x.strip()]
        entries.append(e)
    return entries


def tokens(entries):
    toks = set()
    for e in entries:
        for f in e["forms"] + ([e["german"]] if e["type"] in ("v", "vs") else []):
            for t in re.split(r"[\s/]+", f):
                if t:
                    toks.add(t.lower())
    return toks


def write_md(entries, n_tokens):
    lines = [
        "# Немецкий словарь: Duolingo, разделы 1–2 (курс для англоговорящих)",
        "",
        f"**Лемм (словарных статей): {len(entries)}** · "
        f"**уникальных словоформ: {n_tokens}** (Duolingo считает формы: *bin*, *bist*, *ist* — три «слова»).",
        "",
        "> Словарь восстановлен по тематике разделов 1–2 курса Duolingo German (from English),",
        "> а не выгружен из личного аккаунта. Сверьте его со своим списком «Слова» в приложении:",
        "> лишнее удалите, недостающее допишите в `vocab_source.txt` и пересоберите (`python3 build_dictionary.py`).",
        "",
    ]
    cur = None
    for e in entries:
        if (e["section"], e["unit"]) != cur:
            if cur and cur[0] != e["section"]:
                pass
            if cur is None or cur[0] != e["section"]:
                lines += ["", f"## Раздел {e['section']}", ""]
            cur = (e["section"], e["unit"])
            lines += ["", f"### {e['unit']}. {e['topic_ru']} · *{e['topic_en']}*", "",
                      "| Немецкий | Формы | Русский | English |", "|---|---|---|---|"]
        de = e["german"]
        if "article" in e:
            de = f"{e['article']} {de}" if e["type"] != "pl" else f"die {de} *(мн.)*"
            extra = f"мн.: {e['plural']}" if e["plural"] and e["type"] != "pl" else ("только ед. ч." if e["type"] != "pl" else "")
        elif e["type"] in ("v", "vs"):
            p = e["present"]
            extra = ", ".join(p.values()) if len(p) > 1 else p.get("es", "")
        elif e["type"] == "adj":
            extra = ""
        else:
            extra = ", ".join(e["forms"][1:])
        lines.append(f"| **{de}** | {extra} | {e['ru']} | {e['en']} |")
    (HERE / "СЛОВАРЬ.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    entries = parse()
    toks = tokens(entries)
    by_type = {}
    for e in entries:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    data = OrderedDict(
        title="Duolingo German (from English) — Sections 1–2",
        note="Reconstructed from the course's Section 1–2 topics, not exported from a personal account.",
        lemma_count=len(entries),
        word_form_count=len(toks),
        counts_by_type=by_type,
        entries=entries,
        all_word_forms=sorted(toks),
    )
    (HERE / "dictionary.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    write_md(entries, len(toks))
    print(f"lemmas: {len(entries)}  word forms: {len(toks)}")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {TYPE_RU.get(t, t):24} {n}")


if __name__ == "__main__":
    main()
