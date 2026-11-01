"""Regression checks for screenshot comparison and review output."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, PngImagePlugin

from scene_atlas import analyze_session_screenshots


class SceneAtlasTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.session = self.root / 'session'
        self.session.mkdir()

    def capture(self, number, image, **save_options):
        directory = self.session / f'capture_{number:06d}'
        directory.mkdir()
        (directory / 'capture.json').write_text(json.dumps({
            'capture': number, 'time': {'process_elapsed_us': number * 1_000_000}
        }), encoding='utf-8')
        path = directory / 'screenshot.png'
        image.save(path, **save_options)
        return path

    def analyze(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return analyze_session_screenshots(self.session, **kwargs)

    def test_png_compression_and_metadata_do_not_create_cut(self):
        image = Image.new('RGB', (80, 60), 'navy')
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text('comment', 'Same image with different encoding')
        first = self.capture(0, image, compress_level=0)
        second = self.capture(1, image, compress_level=9, pnginfo=metadata)
        self.assertNotEqual(first.read_bytes(), second.read_bytes())
        atlas = self.analyze()
        self.assertEqual(atlas['entries'][1]['delta_from_prev_pct'], 0)
        self.assertEqual(atlas['entries'][0]['decoded_rgb_sha256'],
                         atlas['entries'][1]['decoded_rgb_sha256'])
        self.assertEqual(atlas['candidate_transitions'], [])

    def test_palette_changes_are_visible_even_with_same_indices(self):
        image = Image.new('P', (80, 60), 0)
        image.putpalette([0, 0, 0] * 256)
        self.capture(0, image)
        image.putpalette([255, 255, 255] * 256)
        self.capture(1, image)
        atlas = self.analyze()
        self.assertEqual(atlas['entries'][1]['delta_from_prev_pct'], 100)
        self.assertEqual(len(atlas['candidate_transitions']), 1)
        transition = atlas['candidate_transitions'][0]
        self.assertEqual((transition['start_sec'], transition['end_sec']), (0, 1))
        self.assertEqual(transition['review_status'], 'unreviewed')

    def test_resolution_change_is_explicit_even_with_same_color(self):
        self.capture(0, Image.new('RGB', (80, 60), 'black'))
        self.capture(1, Image.new('RGB', (160, 120), 'black'))
        atlas = self.analyze()
        self.assertEqual(atlas['entries'][1]['delta_from_prev_pct'], 0)
        self.assertTrue(atlas['entries'][1]['dimensions_changed'])
        self.assertEqual(atlas['candidate_transitions'][0]['reason'], 'dimensions_changed')

    def test_corrupt_image_breaks_comparison_and_reports_gap(self):
        self.capture(0, Image.new('RGB', (80, 60), 'black'))
        broken = self.capture(1, Image.new('RGB', (80, 60), 'black'))
        broken.write_bytes(b'not a PNG')
        self.capture(2, Image.new('RGB', (80, 60), 'white'))
        atlas = self.analyze()
        self.assertEqual(atlas['total_screenshots'], 2)
        self.assertIsNone(atlas['entries'][1]['delta_from_prev_pct'])
        self.assertTrue(any('Cannot decode' in warning for warning in atlas['warnings']))
        self.assertEqual(atlas['candidate_transitions'], [])

    def test_unknown_time_is_not_zero_and_outputs_preserve_inputs(self):
        self.capture(0, Image.new('RGB', (80, 60), 'black'))
        (self.session / 'capture_000000' / 'capture.json').write_text('{"capture": 0}')
        before = {path: path.read_bytes() for path in self.session.rglob('*') if path.is_file()}
        manifest = self.root / 'atlas.json'
        sheet = self.root / 'sheet.jpg'
        atlas = self.analyze(output_manifest=manifest, contact_sheet=sheet)
        self.assertIsNone(atlas['entries'][0]['elapsed_sec'])
        self.assertTrue(atlas['warnings'])
        self.assertEqual(json.loads(manifest.read_text())['review_status'], 'unreviewed')
        with Image.open(sheet) as image:
            self.assertGreater(image.width, 0)
            self.assertGreater(image.height, 0)
        after = {path: path.read_bytes() for path in self.session.rglob('*') if path.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
