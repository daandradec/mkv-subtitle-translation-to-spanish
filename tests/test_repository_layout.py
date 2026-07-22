import configparser
import os
import tempfile
import tomllib
import unittest
from pathlib import Path

from video_toolkit.temp_paths import managed_temporary_directory


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RepositoryLayoutTests(unittest.TestCase):
    def test_working_directories_use_plural_names(self):
        self.assertTrue((PROJECT_ROOT / "inputs").is_dir())
        self.assertTrue((PROJECT_ROOT / "outputs").is_dir())
        self.assertFalse((PROJECT_ROOT / "input").exists())
        self.assertFalse((PROJECT_ROOT / "output").exists())

    def test_repository_management_scripts_are_centralized(self):
        expected = {
            "manage_video_toolkit.ps1",
            "manage_video_toolkit.sh",
        }
        scripts = PROJECT_ROOT / "scripts"
        self.assertEqual(expected, {path.name for path in scripts.iterdir() if path.is_file()})
        self.assertEqual(
            {"VideoToolkit.Infrastructure.psm1", "VideoToolkit.Infrastructure.sh"},
            {path.name for path in (scripts / "lib").iterdir() if path.is_file()},
        )
        bash_manager = (scripts / "manage_video_toolkit.sh").read_text(encoding="utf-8")
        self.assertIn("lib/VideoToolkit.Infrastructure.sh", bash_manager)
        self.assertFalse((PROJECT_ROOT / "src" / "shared" / "powershell").exists())
        self.assertFalse((PROJECT_ROOT / "src" / "shared" / "tests").exists())
        self.assertTrue((PROJECT_ROOT / "src" / "shared" / "video_toolkit").is_dir())
        self.assertFalse((PROJECT_ROOT / "src" / "shared" / "python").exists())

        for manager in (
            scripts / "manage_video_toolkit.ps1",
            scripts / "manage_video_toolkit.sh",
        ):
            source = manager.read_text(encoding="utf-8-sig")
            self.assertIn("clean-temporary-files", source)
            self.assertIn("clean-cache-files", source)
            self.assertNotIn(".tmp/dist", source.replace("\\", "/"))

    def test_setuptools_artifacts_are_redirected_to_dot_tmp(self):
        config = configparser.ConfigParser()
        config.read(PROJECT_ROOT / "setup.cfg", encoding="utf-8")
        self.assertEqual(config["build"]["build_base"], ".tmp/build")
        self.assertEqual(config["egg_info"]["egg_base"], ".tmp")

        with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
            project_config = tomllib.load(handle)
        package_dirs = project_config["tool"]["setuptools"]["package-dir"]
        self.assertEqual(package_dirs["video_toolkit"], "src/shared/video_toolkit")

    def test_workflow_launchers_use_the_consolidated_runtime(self):
        launchers = (
            PROJECT_ROOT
            / "src"
            / "video-generate-new-subtitles-from-audio"
            / "transcribe_video_audio.ps1",
            PROJECT_ROOT
            / "src"
            / "video-generate-traslated-subtitles-from-existing-subtitles"
            / "traducir_subs_mkv.ps1",
            PROJECT_ROOT
            / "src"
            / "video-generate-whisper-transcription"
            / "transcribe_video_text.ps1",
        )
        for launcher in launchers:
            with self.subTest(launcher=launcher.name):
                source = launcher.read_text(encoding="utf-8-sig")
                self.assertIn("VideoToolkit.Infrastructure.psm1", source)
                self.assertIn("manage_video_toolkit.ps1", source)
                self.assertIn('"setup-python-environment"', source)

    def test_repository_root_has_no_temporary_packaging_artifacts(self):
        for name in ("build", "video_toolkit_workflows.egg-info"):
            self.assertFalse((PROJECT_ROOT / name).exists(), name)

    def test_reusable_generated_paths_use_dot_cache(self):
        cache_root = Path(os.environ["VIDEO_TOOLKIT_CACHE_ROOT"]).resolve()
        self.assertEqual(cache_root, (PROJECT_ROOT / ".cache").resolve())
        self.assertEqual(Path(os.environ["PIP_CACHE_DIR"]).resolve(), cache_root / "pip")
        self.assertEqual(Path(os.environ["PYTHONPYCACHEPREFIX"]).resolve(), cache_root / "python")
        self.assertEqual(Path(os.environ["HF_HOME"]).resolve(), cache_root / "models" / "huggingface")
        self.assertEqual(Path(os.environ["TORCH_HOME"]).resolve(), cache_root / "models" / "torch")
        self.assertEqual(Path(os.environ["WHISPER_CACHE_DIR"]).resolve(), cache_root / "models" / "whisper")

        powershell_manager = (PROJECT_ROOT / "scripts" / "manage_video_toolkit.ps1").read_text(
            encoding="utf-8-sig"
        )
        bash_manager = (PROJECT_ROOT / "scripts" / "manage_video_toolkit.sh").read_text(encoding="utf-8")
        for source in (powershell_manager, bash_manager):
            normalized = source.replace("\\", "/")
            self.assertIn("packages/python", normalized)
            self.assertIn("install-state", normalized)

    def test_dist_is_not_used_for_python_packaging(self):
        managed_sources = (
            PROJECT_ROOT / "scripts" / "manage_video_toolkit.ps1",
            PROJECT_ROOT / "scripts" / "manage_video_toolkit.sh",
            PROJECT_ROOT / "scripts" / "lib" / "VideoToolkit.Infrastructure.psm1",
            PROJECT_ROOT / "scripts" / "lib" / "VideoToolkit.Infrastructure.sh",
        )
        for path in managed_sources:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8-sig").replace("\\", "/")
                self.assertNotIn(".tmp/dist", source)
                self.assertNotIn('Join-Path $temporaryRoot "dist"', source)

    def test_managed_temporary_directory_uses_configured_root(self):
        configured_root = Path(os.environ["VIDEO_TOOLKIT_TMP_ROOT"]).resolve()
        with managed_temporary_directory("layout-test-") as directory:
            temporary_path = Path(directory).resolve()
            self.assertTrue(temporary_path.is_relative_to(configured_root / "tests"))
            self.assertTrue(temporary_path.is_dir())

    def test_standard_tempfile_is_redirected_by_test_launcher(self):
        configured_tests = (Path(os.environ["VIDEO_TOOLKIT_TMP_ROOT"]) / "tests").resolve()
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(Path(directory).resolve().is_relative_to(configured_tests))


if __name__ == "__main__":
    unittest.main()
