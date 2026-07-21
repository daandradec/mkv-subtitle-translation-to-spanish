#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def find_translation_maps(translations_dir, source_language):
    language_dir = Path(translations_dir) / source_language
    if not language_dir.exists():
        return []

    translations_all = language_dir / "translations_all.json"
    if translations_all.exists():
        return [translations_all]

    return sorted(
        path
        for path in language_dir.glob("translations_*.json")
        if path.is_file() and path.name != "translations_all.json"
    )


def main():
    parser = argparse.ArgumentParser(description="Resolve workspace translation maps for a source language.")
    parser.add_argument("--translations-dir", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    paths = [str(path) for path in find_translation_maps(args.translations_dir, args.language)]
    if args.json:
        print(json.dumps(paths, ensure_ascii=False, indent=2))
    else:
        for path in paths:
            print(path)


if __name__ == "__main__":
    main()
