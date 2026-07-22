"""Deterministic output-folder naming shared by the video workflows."""

from pathlib import Path


RESERVED_OUTPUT_NAMES = {"_legacy"}


def output_folder_name(input_video):
    """Return the source filename without its extension for use under outputs/."""
    stem = Path(input_video).stem.rstrip(". ")
    if not stem or stem in {".", ".."}:
        raise ValueError(f"Could not derive a safe output folder name from: {input_video}")
    if stem.casefold() in RESERVED_OUTPUT_NAMES:
        raise ValueError(f"Reserved output folder name derived from input: {stem}")
    return stem
