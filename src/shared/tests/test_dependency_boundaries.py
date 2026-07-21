import ast
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[2]
SKILL_PACKAGES = {
    "mkv-subtitle-agentic-translation": "mkv_subtitle_agentic_translation",
    "video-subtitle-agentic-transcription": "video_subtitle_agentic_transcription",
    "video-text-agent-transcription": "video_text_agent_transcription",
}
LEGACY_FLAT_MODULES = {
    "ass_apply_translations",
    "ass_to_tv_safe_srt",
    "languages",
    "normalize_spanish_subtitles",
    "normalize_translation_maps",
    "subtitle_language",
    "subtitle_text_to_ass",
    "subtitle_workspace",
    "text_transcription_postprocess",
    "text_transcription_workspace",
    "transcription_backend",
    "transcription_postprocess",
    "transcription_workspace",
    "translation_maps",
    "translation_terms",
}


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def imports_package(module_name, package_name):
    return module_name == package_name or module_name.startswith(f"{package_name}.")


class DependencyBoundaryTests(unittest.TestCase):
    def test_shared_python_does_not_import_skill_packages(self):
        skill_packages = tuple(SKILL_PACKAGES.values())
        for path in (SRC_DIR / "shared" / "python").rglob("*.py"):
            for module_name in imported_modules(path):
                with self.subTest(path=path, module=module_name):
                    self.assertFalse(
                        any(imports_package(module_name, package) for package in skill_packages)
                    )

    def test_skill_packages_do_not_import_each_other(self):
        for skill_dir, owner_package in SKILL_PACKAGES.items():
            forbidden = tuple(
                package for package in SKILL_PACKAGES.values() if package != owner_package
            )
            for path in (SRC_DIR / skill_dir / "python").rglob("*.py"):
                for module_name in imported_modules(path):
                    with self.subTest(skill=skill_dir, path=path, module=module_name):
                        self.assertFalse(
                            any(imports_package(module_name, package) for package in forbidden)
                        )

    def test_canonical_packages_do_not_import_flat_compatibility_modules(self):
        roots = [SRC_DIR / "shared" / "python"]
        roots.extend(SRC_DIR / skill_dir / "python" for skill_dir in SKILL_PACKAGES)
        for root in roots:
            for path in root.rglob("*.py"):
                for module_name in imported_modules(path):
                    with self.subTest(path=path, module=module_name):
                        self.assertFalse(
                            any(
                                imports_package(module_name, legacy_module)
                                for legacy_module in LEGACY_FLAT_MODULES
                            )
                        )


if __name__ == "__main__":
    unittest.main()
