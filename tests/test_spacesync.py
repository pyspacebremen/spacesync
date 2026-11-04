import tempfile
import unittest
from pathlib import Path
import zipfile
import json
import importlib.util
import subprocess
import sys
from string import Formatter
from unittest.mock import patch

from spacesync import (create_archive, extract_archive, load_settings, save_settings,
                       Translator, LANGUAGES_PATH, manual_sections, export_manual_pdf)


class ManualTests(unittest.TestCase):
    def test_manual_uses_selected_language(self):
        translator = Translator(LANGUAGES_PATH)
        for code, heading in [('de', '1. Pfade auswählen'),
                              ('en', '1. Choose paths'), ('nl', '1. Paden kiezen')]:
            translator.select(code)
            sections = manual_sections(translator)
            self.assertEqual(len(sections), 8)
            self.assertEqual(sections[0][0], heading)
            self.assertTrue(all(body for _, body in sections))

    @unittest.skipUnless(importlib.util.find_spec('reportlab'), 'ReportLab not installed')
    def test_pdf_export_and_failed_export_preserves_file(self):
        translator = Translator(LANGUAGES_PATH)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'manual.pdf'
            for code in ('de', 'en', 'nl'):
                translator.select(code)
                export_manual_pdf(path, translator)
                self.assertTrue(path.read_bytes().startswith(b'%PDF-'))
                self.assertGreater(path.stat().st_size, 10000)
            previous = path.read_bytes()
            with patch('reportlab.platypus.SimpleDocTemplate.build', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    export_manual_pdf(path, translator)
            self.assertEqual(path.read_bytes(), previous)
            self.assertEqual(list(Path(temporary).iterdir()), [path])


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


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'hello.txt').write_text('Grüße', encoding='utf-8')
        self.archive = self.root / 'backup.zip'
        self.config = self.root / 'settings.json'
        save_settings(self.config, {'archive': str(self.archive), 'directory': str(self.source),
                                   'clear': True, 'language': 'en'})

    def run_cli(self, *args):
        # Verify real subprocess execution even on systems without Tkinter.
        script = Path(__file__).resolve().parents[1] / 'spacesync.py'
        bootstrap = """
import builtins, runpy, sys
original = builtins.__import__
def no_tk(name, *args, **kwargs):
    if name == 'tkinter' or name.startswith('tkinter.'):
        raise ImportError('Tkinter unavailable in headless test')
    return original(name, *args, **kwargs)
builtins.__import__ = no_tk
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""
        return subprocess.run([sys.executable, '-c', bootstrap, str(script),
                               '--config', str(self.config), *args],
                              capture_output=True, text=True, timeout=15)

    def test_action_only_uses_saved_paths_and_does_not_save_overrides(self):
        previous = self.config.read_bytes()
        result = self.run_cli('archive')
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(self.archive) as archive:
            self.assertEqual(archive.read('hello.txt').decode(), 'Grüße')
        target = self.root / 'target'
        target.mkdir()
        (target / 'extra').write_text('keep')
        result = self.run_cli('extract', '--directory', str(target), '--no-clear')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((target / 'extra').exists())
        self.assertTrue((target / 'hello.txt').exists())
        self.assertEqual(self.config.read_bytes(), previous)

    def test_saved_clear_and_explicit_save(self):
        self.assertEqual(self.run_cli('create').returncode, 0)
        target = self.root / 'target'
        target.mkdir()
        (target / 'extra').write_text('remove')
        result = self.run_cli('unpack', '--directory', str(target), '--headless',
                              '--language', 'nl', '--save-settings')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((target / 'extra').exists())
        self.assertIn('Uitpakken voltooid', result.stdout)
        settings = load_settings(self.config)
        self.assertEqual(settings['directory'], str(target))
        self.assertEqual(settings['language'], 'nl')
        self.assertTrue(settings['clear'])

    def test_missing_config_and_explicit_paths(self):
        self.config.unlink()
        result = self.run_cli('archive')
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.archive.exists())
        result = self.run_cli('archive', '-a', str(self.archive), '-d', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.config.exists())

    def test_invalid_config_and_invocation(self):
        self.config.write_text('{broken')
        result = self.run_cli('archive')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(self.run_cli('--headless').returncode, 2)
        self.assertEqual(self.run_cli('extract', '--clear', '--no-clear').returncode, 2)
        self.assertEqual(self.run_cli('archive', '--pdf', 'bad.pdf').returncode, 2)
        self.assertEqual(self.run_cli('--help').returncode, 0)

    def test_manual_language(self):
        result = self.run_cli('manual', '--language', 'de')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('8. Kommandozeile ohne Fenster', result.stdout)


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
