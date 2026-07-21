#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from video_generate_traslated_subtitles_from_existing_subtitles.normalize_spanish_subtitles import (
    find_suspicious_question_marks,
    normalize_spanish_text,
)


def sanitize_map(input_path, output_path):
    data = json.loads(input_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Translation map must be a JSON object: {input_path}")

    sanitized = {}
    changed = []
    suspicious = []
    for key, value in data.items():
        if value is None:
            sanitized[key] = value
            continue
        if not isinstance(value, str):
            sanitized[key] = value
            continue

        normalized = normalize_spanish_text(value)
        sanitized[key] = normalized
        if normalized != value:
            changed.append({"key": key, "before": value, "after": normalized})
        for finding in find_suspicious_question_marks(normalized):
            suspicious.append({"key": key, **finding})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(sanitized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "input": str(input_path),
        "output": str(output_path),
        "entries": len(data),
        "changed_entries": len(changed),
        "suspicious_question_replacements": suspicious,
        "suspicious_question_replacement_count": len(suspicious),
        "changed_samples": changed[:25],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Normalize generated Spanish translation JSON maps before applying them to subtitles."
    )
    parser.add_argument("--translations", nargs="+", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    report_path = Path(args.report)
    sanitized_paths = []
    map_reports = []

    for index, raw_path in enumerate(args.translations, start=1):
        input_path = Path(raw_path)
        output_name = input_path.name
        if len(args.translations) > 1:
            output_name = f"{index:02d}_{output_name}"
        output_path = output_dir / output_name
        map_report = sanitize_map(input_path, output_path)
        sanitized_paths.append(str(output_path))
        map_reports.append(map_report)

    suspicious_count = sum(item["suspicious_question_replacement_count"] for item in map_reports)
    report = {
        "translation_maps": sanitized_paths,
        "map_count": len(map_reports),
        "changed_entries": sum(item["changed_entries"] for item in map_reports),
        "suspicious_question_replacement_count": suspicious_count,
        "maps": map_reports,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps({"translation_maps": sanitized_paths, "report": str(report_path)}, ensure_ascii=False))
    else:
        print(f"translation maps: {len(sanitized_paths)}")
        print(f"changed entries: {report['changed_entries']}")
        print(f"report: {report_path}")

    if suspicious_count:
        raise SystemExit(
            "Translation map quality validation failed: suspicious '?' replacements remain. "
            f"See report: {report_path}"
        )


if __name__ == "__main__":
    main()
