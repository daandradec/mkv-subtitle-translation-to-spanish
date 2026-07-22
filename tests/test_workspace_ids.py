import unittest

from video_toolkit.workspace_ids import output_folder_name


class OutputFolderNameTests(unittest.TestCase):
    def test_output_name_is_the_full_filename_stem_without_hash(self):
        self.assertEqual(output_folder_name("inputs/NIPPON SANGOKU.mkv"), "NIPPON SANGOKU")

    def test_trailing_windows_dots_and_spaces_are_removed(self):
        self.assertEqual(output_folder_name("inputs/video. .mkv"), "video")

    def test_legacy_archive_name_is_reserved(self):
        with self.assertRaisesRegex(ValueError, "Reserved output folder"):
            output_folder_name("inputs/_legacy.mkv")


if __name__ == "__main__":
    unittest.main()
