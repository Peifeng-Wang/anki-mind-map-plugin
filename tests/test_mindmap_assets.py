import json
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open

# Mock Anki/Qt before importing the module under test
_mock_aqt = MagicMock()
_mock_qt = MagicMock()
_mock_webview = MagicMock()
_mock_utils = MagicMock()

sys.modules['aqt'] = _mock_aqt
sys.modules['aqt.qt'] = _mock_qt
sys.modules['aqt.webview'] = _mock_webview
sys.modules['aqt.utils'] = _mock_utils

from mindmap_editor import assets


class TestAssetCaches(unittest.TestCase):
    def test_asset_cache_is_dict(self):
        self.assertIsInstance(assets._asset_cache, dict)

    def test_bg_image_cache_is_dict(self):
        self.assertIsInstance(assets._bg_image_cache, dict)


class TestReadAsset(unittest.TestCase):
    def setUp(self):
        assets._asset_cache.clear()

    @patch('builtins.open', mock_open(read_data='hello world'))
    @patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    def test_read_asset_caches(self, mock_join):
        result = assets.read_asset('test.js')
        self.assertEqual(result, 'hello world')
        self.assertIn('test.js', assets._asset_cache)

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_read_asset_missing(self, mock_open):
        result = assets.read_asset('missing.js')
        self.assertEqual(result, '')


class TestReadAssets(unittest.TestCase):
    @patch.object(assets, 'read_asset', side_effect=lambda f: f'content_of_{f}')
    def test_read_assets_joins(self, mock_read):
        result = assets.read_assets(['a.js', 'b.js'])
        self.assertEqual(result, 'content_of_a.js\ncontent_of_b.js')


class TestReadCssEntry(unittest.TestCase):
    def setUp(self):
        assets._asset_cache.clear()

    @patch.object(assets, 'read_asset', side_effect=lambda f: f'/* {f} */')
    def test_plain_css(self, mock_read):
        result = assets.read_css_entry('style.css')
        self.assertIn('style.css', result)

    @patch.object(assets, 'read_asset', side_effect=lambda f: f'/* {f} */')
    def test_import_expansion(self, mock_read):
        css = '@import url("./foo.css");\nbody {}'
        with patch.object(assets, 'read_asset', side_effect=lambda f: css if f == 'main.css' else f'/* {f} */'):
            result = assets.read_css_entry('main.css')
            self.assertIn('foo.css', result)
            self.assertIn('body {}', result)


class TestGetBackgroundStyle(unittest.TestCase):
    def setUp(self):
        assets._bg_image_cache.clear()

    @patch('os.path.exists', return_value=False)
    def test_no_file(self, mock_exists):
        result = assets.get_background_style('/addon', {'background_image': 'bg.jpg'})
        self.assertEqual(result, '')

    @patch('os.path.exists', return_value=True)
    @patch('os.path.getmtime', return_value=12345)
    @patch('builtins.open', mock_open(read_data=b'\x89PNG'))
    @patch('base64.b64encode', return_value=b'BASE64')
    def test_with_overlay(self, mock_b64, mock_mtime, mock_exists):
        result = assets.get_background_style('/addon', {'background_image': 'bg.png', 'background_overlay': 'rgba(0,0,0,0.5)'})
        self.assertIn('linear-gradient', result)

    @patch('os.path.exists', return_value=True)
    @patch('os.path.getmtime', return_value=12345)
    @patch('builtins.open', mock_open(read_data=b'\xff\xd8\xff\xe0'))
    @patch('base64.b64encode', return_value=b'BASE64')
    def test_jpeg(self, mock_b64, mock_mtime, mock_exists):
        result = assets.get_background_style('/addon', {'background_image': 'bg.jpg'})
        self.assertIn('image/jpeg', result)


class TestBuildEditorHtml(unittest.TestCase):
    @patch.object(assets, 'read_assets', return_value='')
    @patch.object(assets, 'read_css_entry', return_value='')
    @patch.object(assets, 'get_background_style', return_value='')
    def test_build_html(self, mock_bg, mock_css, mock_assets):
        dialog = MagicMock()
        html = assets.build_editor_html(dialog, {'hotkeys': {}}, '{"data":{}}', 'focus1')
        self.assertIn('initialData', html)
        self.assertIn('focus1', html)


if __name__ == '__main__':
    unittest.main()
