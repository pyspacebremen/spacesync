import tempfile
import unittest
from pathlib import Path
import zipfile
import json
from string import Formatter
from unittest.mock import patch

from spacesync import (create_archive, extract_archive, load_settings, save_settings,
                       Translator, LANGUAGES_PATH)


class LanguageTests(unittest.TestCase):
    def test_system_language_and_fallback(self):
        with patch('spacesync.system_language', return_value='de_DE.UTF-8'):
            translator = Translator(LANGUAGES_PATH)
            self.assertEqual(translator('settings_menu'), 'Einstellungen')
        translator.select('en-US')
        self.assertEqual(translator('settings_menu'), 'Settings')
        translator.select('unknown')
        self.assertEqual(translator.code, 'en')

    def test_additional_language_and_missing_translation(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = json.loads(LANGUAGES_PATH.read_text(encoding='utf-8'))
            data['fr'] = {'name': 'Français', 'messages': {'settings_menu': 'Paramètres'}}
            path = Path(temporary) / 'languages.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            translator = Translator(path)
            translator.select('fr_FR')
            self.assertEqual(translator('settings_menu'), 'Paramètres')
            self.assertEqual(translator('saved', archive='test.zip'), 'Archive saved: test.zip')

    def test_translation_keys_and_placeholders_match(self):
        data = json.loads(LANGUAGES_PATH.read_text(encoding='utf-8'))
        english = data['en']['messages']
        fields = lambda text: {name for _, name, _, _ in Formatter().parse(text) if name}
        for language in data.values():
            self.assertEqual(set(language['messages']), set(english))
            for key, message in language['messages'].items():
                self.assertEqual(fields(message), fields(english[key]), key)


class SettingsTests(unittest.TestCase):
    def test_settings_roundtrip(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'settings.json'
            self.assertEqual(load_settings(path), {})
            settings = {'archive': '/tmp/Grüße.zip', 'directory': '/tmp/Ziel', 'clear': True}
            save_settings(path, settings)
            self.assertEqual(load_settings(path), settings)
            settings['clear'] = False
            save_settings(path, settings)
            self.assertEqual(load_settings(path), settings)

    def test_invalid_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'settings.json'
            for content in ('{', '[]', '{"clear": "false"}', '{"archive": 42}'):
                with self.subTest(content=content):
                    path.write_text(content, encoding='utf-8')
                    with self.assertRaises(ValueError):
                        load_settings(path)


class ArchiveTests(unittest.TestCase):
    def test_roundtrip_and_clear(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / 'source', root / 'target'
            (source / 'empty').mkdir(parents=True)
            (source / 'hello.txt').write_text('Grüße', encoding='utf-8')
            archive = root / 'backup.zip'
            create_archive(archive, source, lambda _: None)
            target.mkdir()
            (target / 'extra.txt').write_text('extra')
            extract_archive(archive, target, False, lambda _: None)
            self.assertEqual((target / 'hello.txt').read_text(encoding='utf-8'), 'Grüße')
            self.assertTrue((target / 'empty').is_dir())
            self.assertTrue((target / 'extra.txt').exists())
            extract_archive(archive, target, True, lambda _: None)
            self.assertFalse((target / 'extra.txt').exists())

    def test_unsafe_archive_does_not_clear_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'target'
            target.mkdir()
            (target / 'keep.txt').write_text('keep')
            archive = root / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr('../outside.txt', 'bad')
            with self.assertRaises(ValueError):
                extract_archive(archive, target, True, lambda _: None)
            self.assertTrue((target / 'keep.txt').exists())
            self.assertFalse((root / 'outside.txt').exists())

    def test_source_symlink_preserves_existing_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            source.mkdir()
            (source / 'link').symlink_to(root / 'elsewhere')
            archive = root / 'existing.zip'
            archive.write_bytes(b'previous content')
            with self.assertRaises(ValueError):
                create_archive(archive, source, lambda _: None)
            self.assertEqual(archive.read_bytes(), b'previous content')


if __name__ == '__main__':
    unittest.main()
