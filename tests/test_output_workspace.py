import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


POWERSHELL = shutil.which("powershell")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "lib" / "VideoToolkit.Infrastructure.psm1"


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(POWERSHELL, "Windows PowerShell is required")
class OutputWorkspaceTests(unittest.TestCase):
    def invoke_workspace(self, root, output_dir, debug_dir, resume=False):
        command = [
            f"Import-Module {ps_quote(MODULE_PATH)} -Force",
            "$result = Initialize-VideoOutputWorkspace "
            f"-ProjectRoot {ps_quote(root)} "
            f"-OutputDir {ps_quote(output_dir)} "
            f"-DebugDir {ps_quote(debug_dir)} "
            f"-InputPath {ps_quote(Path(root) / 'inputs' / 'video.mp4')} "
            "-Workflow 'test-workflow'"
            + (" -Resume" if resume else ""),
            "$result | ConvertTo-Json -Compress",
        ]
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-Command", "; ".join(command)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_fresh_workspace_clears_existing_contents_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "outputs").mkdir()
            output_dir = root / "outputs" / "video"
            debug_dir = output_dir / "debug" / "test-workflow"
            stale = output_dir / "old" / "stale.txt"
            stale.parent.mkdir(parents=True)
            stale.write_text("old", encoding="utf-8")

            result = self.invoke_workspace(root, output_dir, debug_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(stale.exists())
            manifest = json.loads((debug_dir / "run_manifest.json").read_text(encoding="utf-8-sig"))
            self.assertEqual(manifest["mode"], "fresh")
            self.assertEqual(manifest["workflow"], "test-workflow")

    def test_resume_preserves_existing_debug_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "outputs").mkdir()
            output_dir = root / "outputs" / "video"
            debug_dir = output_dir / "debug" / "test-workflow"
            marker = debug_dir / "checkpoint.json"
            marker.parent.mkdir(parents=True)
            marker.write_text("{}", encoding="utf-8")

            result = self.invoke_workspace(root, output_dir, debug_dir, resume=True)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(marker.exists())
            manifest = json.loads((debug_dir / "run_manifest.json").read_text(encoding="utf-8-sig"))
            self.assertEqual(manifest["mode"], "resume")

    def test_nested_or_external_output_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "outputs").mkdir()
            output_dir = root / "outputs" / "video" / "nested"
            debug_dir = output_dir / "debug" / "test-workflow"

            result = self.invoke_workspace(root, output_dir, debug_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unsafe output workspace target", result.stderr)

    def test_legacy_archive_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "outputs").mkdir()
            output_dir = root / "outputs" / "_legacy"
            debug_dir = output_dir / "debug" / "test-workflow"

            result = self.invoke_workspace(root, output_dir, debug_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Reserved output workspace target", result.stderr)

    def test_file_at_output_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "outputs").mkdir()
            output_dir = root / "outputs" / "video"
            output_dir.write_text("not a directory", encoding="utf-8")
            debug_dir = output_dir / "debug" / "test-workflow"

            result = self.invoke_workspace(root, output_dir, debug_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Output workspace target is not a directory", result.stderr)


if __name__ == "__main__":
    unittest.main()
