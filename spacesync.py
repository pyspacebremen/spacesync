"""ZIP-Archive und Verzeichnisse mit einer Tkinter-Oberfläche abgleichen."""
from pathlib import Path
import json
import argparse
import locale
import os
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from xml.sax.saxutils import escape


SETTINGS_PATH = Path(__file__).resolve().with_name('spacesync.json')
LANGUAGES_PATH = Path(__file__).resolve().with_name('languages.json')


def system_language():
    for name in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        if os.environ.get(name):
            return os.environ[name]
    if sys.platform == 'darwin':
        try:
            result = subprocess.run(['defaults', 'export', 'NSGlobalDomain', '-'],
                                    capture_output=True, check=True, timeout=2)
            languages = plistlib.loads(result.stdout).get('AppleLanguages', [])
            if languages:
                return languages[0]
        except (OSError, subprocess.SubprocessError, plistlib.InvalidFileException):
            pass
    elif sys.platform == 'win32':
        import ctypes
        return locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), 'en')
    return locale.getlocale()[0] or 'en'


class Translator:
    def __init__(self, path):
        self.languages = json.loads(Path(path).read_text(encoding='utf-8'))
        if 'en' not in self.languages:
            raise ValueError('languages.json requires an English (en) fallback.')
        for code, data in self.languages.items():
            if (not isinstance(data.get('name'), str)
                    or not isinstance(data.get('messages'), dict)
                    or not all(isinstance(value, str) for value in data['messages'].values())):
                raise ValueError(f'Invalid language definition: {code}')
        self.select('')

    def select(self, language):
        code = (language or system_language()).split('.')[0].split('@')[0]
        code = code.replace('-', '_').lower()
        self.code = next((key for key in (code, code.split('_')[0])
                          if key in self.languages), 'en')

    def __call__(self, message_key, **values):
        message = self.languages[self.code]['messages'].get(
            message_key, self.languages['en']['messages'].get(message_key, message_key))
        return message.format(**values)


translator = Translator(LANGUAGES_PATH)
tr = translator


MANUAL_SECTIONS = ('paths', 'archive', 'extract', 'clear', 'settings', 'messages', 'pdf', 'cli')


def manual_sections(translate):
    return [(translate(f'manual_{key}_heading'), translate(f'manual_{key}_body'))
            for key in MANUAL_SECTIONS]


def export_manual_pdf(path, translate):
    # Optional dependency: the application and manual also work without ReportLab.
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

    fonts = Path(reportlab.__file__).parent / 'fonts'
    for name, filename in [('Manual', 'Vera.ttf'), ('ManualBold', 'VeraBd.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
    styles = getSampleStyleSheet()
    for name in ('Title', 'Heading2', 'BodyText'):
        styles[name].fontName = 'ManualBold' if name != 'BodyText' else 'Manual'
    styles['BodyText'].fontSize = 10
    styles['BodyText'].leading = 15
    styles['Heading2'].textColor = colors.HexColor('#234963')
    story = [Paragraph(escape('SpaceSync - ' + translate('manual_title')), styles['Title']), Spacer(1, 12)]
    for index, (heading, body) in enumerate(manual_sections(translate)):
        if MANUAL_SECTIONS[index] == 'cli':
            story.append(PageBreak())
        story.extend([Paragraph(escape(heading), styles['Heading2']),
                      Paragraph(escape(body).replace('\n', '<br/>'), styles['BodyText']), Spacer(1, 8)])

    def footer(canvas, document):
        canvas.setFont('Manual', 8)
        canvas.drawString(42, 25, 'SpaceSync | pySpaceBremen')
        canvas.drawRightString(A4[0] - 42, 25, str(document.page))

    path = Path(path)
    handle, temporary = tempfile.mkstemp(dir=path.parent, suffix='.pdf')
    os.close(handle)
    try:
        SimpleDocTemplate(temporary, pagesize=A4, rightMargin=42, leftMargin=42,
                          topMargin=40, bottomMargin=44,
                          title='SpaceSync - ' + translate('manual_title'),
                          author='Python User Group pySpaceBremen').build(
                              story, onFirstPage=footer, onLaterPages=footer)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def load_settings(path):
    try:
        settings = json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}
    if not isinstance(settings, dict):
        raise ValueError(tr('settings_object'))
    for key, expected in [('archive', str), ('directory', str), ('clear', bool), ('language', str)]:
        if key in settings and not isinstance(settings[key], expected):
            raise ValueError(tr('invalid_setting', key=key))
    return settings


def save_settings(path, settings):
    path = Path(path)
    handle, temporary = tempfile.mkstemp(dir=path.parent, suffix='.json')
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as output:
            json.dump(settings, output, ensure_ascii=False, indent=2)
            output.write('\n')
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def create_archive(archive, directory, log):
    archive, directory = Path(archive).resolve(), Path(directory).resolve()
    if not directory.is_dir():
        raise ValueError(tr('source_missing'))
    if archive.is_relative_to(directory):
        raise ValueError(tr('archive_outside_source'))
    archive.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=archive.parent, suffix='.zip')
    os.close(handle)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as output:
            for root, directories, files in os.walk(directory):
                for name in sorted(directories + files):
                    path = Path(root) / name
                    if path.is_symlink():
                        raise ValueError(tr('symlink', path=path))
                    output.write(path, path.relative_to(directory).as_posix())
                    log(tr('archived', path=path.relative_to(directory)))
        os.replace(temporary, archive)
    finally:
        Path(temporary).unlink(missing_ok=True)
    log(tr('saved', archive=archive))


def extract_archive(archive, directory, clear, log):
    archive, directory = Path(archive).resolve(), Path(directory).resolve()
    if directory == Path(directory.anchor) or directory == Path.home().resolve():
        raise ValueError(tr('unsafe_destination'))
    if archive.is_relative_to(directory):
        raise ValueError(tr('archive_outside_target'))
    # Erst vollständig prüfen und temporär entpacken, bevor das Ziel verändert wird.
    with zipfile.ZipFile(archive) as source, tempfile.TemporaryDirectory() as staging:
        for entry in source.infolist():
            name = entry.filename
            parts = name.replace('\\', '/').split('/')
            if (name.startswith(('/', '\\')) or '..' in parts
                    or any(':' in part for part in parts)
                    or stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError(tr('unsafe_entry', name=name))
        source.extractall(staging)
        if directory.exists() and not directory.is_dir():
            raise ValueError(tr('not_directory'))
        if directory.exists() and not clear:
            # Kein Schreiben durch bestehende symbolische Links im Ziel.
            for root, dirs, files in os.walk(directory):
                for name in dirs + files:
                    if (Path(root) / name).is_symlink():
                        raise ValueError(tr('target_symlink', path=Path(root) / name))
        directory.mkdir(parents=True, exist_ok=True)
        if clear:
            for child in directory.iterdir():
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                log(tr('deleted', name=child.name))
        shutil.copytree(staging, directory, dirs_exist_ok=True)
        for entry in source.infolist():
            log(tr('extracted', name=entry.filename))
    log(tr('complete', directory=directory))


def build_parser():
    parser = argparse.ArgumentParser(description=tr('cli_description'))
    parser.add_argument('action', nargs='?',
                        choices=['archive', 'create', 'extract', 'unpack', 'manual'],
                        help=tr('cli_action'))
    parser.add_argument('-a', '--archive', help=tr('cli_archive'))
    parser.add_argument('-d', '--directory', help=tr('cli_directory'))
    clear = parser.add_mutually_exclusive_group()
    clear.add_argument('--clear', dest='clear', action='store_true', default=None,
                       help=tr('cli_clear'))
    clear.add_argument('--no-clear', dest='clear', action='store_false', help=tr('cli_no_clear'))
    parser.add_argument('--language', choices=['system', *translator.languages], help=tr('cli_language'))
    parser.add_argument('--config', type=Path, default=SETTINGS_PATH, help=tr('cli_config'))
    parser.add_argument('--save-settings', action='store_true', help=tr('cli_save_settings'))
    parser.add_argument('--headless', action='store_true', help=tr('cli_headless'))
    parser.add_argument('--pdf', type=Path, help=tr('cli_pdf'))
    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        from spacesync_gui import SpaceSync
        SpaceSync().mainloop()
        return 0
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.action:
        parser.error(tr('cli_missing_action'))
    if args.pdf is not None and args.action != 'manual':
        parser.error(tr('cli_pdf_manual_only'))
    try:
        # Load first, then override only explicitly supplied command-line options.
        if args.language is not None:
            translator.select('' if args.language == 'system' else args.language)
        settings = load_settings(args.config.expanduser())
        language = args.language if args.language is not None else settings.get('language', '')
        language = '' if language == 'system' else language
        translator.select(language)
        resolved = {
            'archive': args.archive if args.archive is not None else settings.get('archive', ''),
            'directory': args.directory if args.directory is not None else settings.get('directory', ''),
            'clear': args.clear if args.clear is not None else settings.get('clear', False),
            'language': language,
        }
        if args.action == 'manual':
            if args.pdf is not None:
                export_manual_pdf(args.pdf.expanduser(), translator)
                print(tr('pdf_saved', path=args.pdf))
            else:
                print('SpaceSync - ' + tr('manual_title'))
                for heading, body in manual_sections(translator):
                    print(f'\n{heading}\n{body}')
        else:
            if not resolved['archive'].strip() or not resolved['directory'].strip():
                raise ValueError(tr('enter_paths'))
            archive = Path(resolved['archive'].strip()).expanduser()
            directory = Path(resolved['directory'].strip()).expanduser()
            if args.action in ('archive', 'create'):
                create_archive(archive, directory, print)
            else:
                extract_archive(archive, directory, resolved['clear'], print)
        if args.save_settings:
            save_settings(args.config.expanduser(), resolved)
    except ImportError as error:
        print(tr('error', error=error), file=sys.stderr)
        return 1
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, shutil.Error) as error:
        print(tr('error', error=error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    # Share the core module with the lazily imported GUI.
    sys.modules.setdefault('spacesync', sys.modules[__name__])
    raise SystemExit(main())
