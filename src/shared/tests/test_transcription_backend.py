import unittest

from video_toolkit.transcription.backend import (
    build_backend_command,
    choose_backend,
    resolve_whisperx_decoding_options,
)


def resolver_with(*names):
    available = set(names)
    return lambda name: f"C:/fake/{name}.exe" if name in available else None


class TranscriptionWorkflowTests(unittest.TestCase):
    def test_backend_auto_prefers_whisperx(self):
        backend, warning = choose_backend("auto", resolver=resolver_with("whisperx", "whisper"))
        self.assertEqual(backend, "whisperx")
        self.assertEqual(warning, "")

    def test_backend_auto_falls_back_to_whisper_with_warning(self):
        backend, warning = choose_backend("auto", resolver=resolver_with("whisper"))
        self.assertEqual(backend, "whisper")
        self.assertIn("WhisperX no esta disponible", warning)

    def test_backend_auto_fails_without_any_backend(self):
        with self.assertRaises(RuntimeError):
            choose_backend("auto", resolver=resolver_with())

    def test_build_whisper_command_includes_transcribe_task(self):
        command = build_backend_command(
            backend="whisper",
            audio="audio.wav",
            output_dir="out",
            language="Spanish",
            whisper_model="turbo",
        )
        self.assertIn("--task", command)
        self.assertIn("transcribe", command)
        self.assertIn("--language", command)
        self.assertIn("Spanish", command)

    def test_build_whisperx_maximum_quality_command(self):
        command = build_backend_command(
            backend="whisperx",
            audio="audio.wav",
            output_dir="out",
            language="es",
            whisperx_quality="maximum",
            whisperx_initial_prompt="Clase virtual de auditoria.",
            whisperx_hotwords="DOFA, PESTEL",
        )
        self.assertEqual(command[command.index("--beam_size") + 1], "10")
        self.assertEqual(command[command.index("--patience") + 1], "2.0")
        self.assertEqual(command[command.index("--temperature") + 1], "0")
        self.assertEqual(command[command.index("--language") + 1], "es")
        self.assertIn("Clase virtual de auditoria.", command)
        self.assertIn("DOFA, PESTEL", command)

    def test_whisperx_quality_options_allow_explicit_overrides(self):
        options = resolve_whisperx_decoding_options("maximum", beam_size=8, patience=1.5)
        self.assertEqual(options, {"beam_size": 8, "patience": 1.5})


if __name__ == "__main__":
    unittest.main()
