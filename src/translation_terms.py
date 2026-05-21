#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


BASE_TERMS = {
    "大和": "Yamato",
    "金沢": "Kanazawa",
    "聖夷": "Seii",
    "福井": "Fukui",
    "龍門": "Ryuumon",
    "賀来": "Kaku",
    "菅生": "Sugao",
    "菅生強": "Sugao Tsuyoshi",
    "長嶺士遼": "Nagamine Shiryō",
    "長尾武兎惇": "Nagao Buton",
    "長尾": "Nagao",
    "武兎惇": "Buton",
    "平殿継": "Taira Tonotsugu",
    "総帥輪島": "Comandante supremo Wajima",
    "犀川": "río Sai",
    "畿内": "Kinai",
    "三角": "Misumi",
    "ツネちゃんさん": "Tsune-chan-san",
}


def mojibake_variants(text):
    variants = set()
    encoded = text.encode("utf-8")
    for encoding in ("cp1252", "latin-1"):
        variants.add(encoded.decode(encoding, errors="ignore"))
    variants.discard(text)
    variants.discard("")
    return variants


def build_default_terms():
    terms = {}
    for source, target in BASE_TERMS.items():
        terms[source] = target
        for variant in mojibake_variants(source):
            terms[variant] = target
    return terms


DEFAULT_TERMS = build_default_terms()


def load_term_maps(paths):
    terms = dict(DEFAULT_TERMS)
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8-sig"))
        for key, value in data.items():
            if key and value is not None:
                terms[str(key)] = str(value)
    return terms


def apply_terms(text, terms):
    result = text
    for source, target in sorted(terms.items(), key=lambda item: len(item[0]), reverse=True):
        result = result.replace(source, target)
    return result


def main():
    parser = argparse.ArgumentParser(description="Apply glossary/term-map replacements to text.")
    parser.add_argument("text")
    parser.add_argument("--term-map", nargs="*", default=[])
    args = parser.parse_args()
    print(apply_terms(args.text, load_term_maps(args.term_map)))


if __name__ == "__main__":
    main()
