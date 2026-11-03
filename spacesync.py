"""ZIP-Archive und Verzeichnisse mit einer Tkinter-Oberfläche abgleichen."""
from pathlib import Path
import json
import locale
import os
import plistlib
import queue
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import zipfile


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


class SpaceSync(tk.Tk):
    def __init__(self):
        super().__init__()
        self.text_variables = {}
        self.title(tr('title'))
        self.geometry('980x440')
        self.minsize(780, 350)
        self.events = queue.Queue()
        self.archive = tk.StringVar()
        self.directory = tk.StringVar()
        self.clear = tk.BooleanVar()
        self.settings_timer = None
        self.language = tk.StringVar(value='')
        try:
            settings = load_settings(SETTINGS_PATH)
            self.language.set(settings.get('language', ''))
            translator.select(self.language.get())
            self.archive.set(settings.get('archive', ''))
            self.directory.set(settings.get('directory', ''))
            self.clear.set(settings.get('clear', False))
        except (OSError, ValueError) as error:
            self.events.put(('log', tr('load_error', error=error)))
        for variable in (self.archive, self.directory, self.clear, self.language):
            variable.trace_add('write', self.schedule_settings_save)
        self.busy = False
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        controls = ttk.Frame(self, padding=18)
        controls.grid(row=0, column=0, sticky='nsew')
        controls.columnconfigure(0, weight=1)
        ttk.Label(controls, textvariable=self.text('archive_label')).grid(row=0, column=0, sticky='w')
        ttk.Entry(controls, textvariable=self.archive).grid(row=1, column=0, sticky='ew', pady=6)
        ttk.Button(controls, textvariable=self.text('browse'), command=self.choose_archive).grid(row=1, column=1, padx=(8, 0))
        actions = ttk.Frame(controls)
        actions.grid(row=2, column=0, columnspan=2, pady=18)
        self.up = ttk.Button(actions, textvariable=self.text('create'), command=lambda: self.start(True))
        self.up.pack(fill='x', pady=4)
        self.down = ttk.Button(actions, textvariable=self.text('extract'), command=lambda: self.start(False))
        self.down.pack(fill='x', pady=4)
        ttk.Label(controls, textvariable=self.text('directory_label')).grid(row=3, column=0, columnspan=2, sticky='w')
        ttk.Entry(controls, textvariable=self.directory).grid(row=4, column=0, sticky='ew', pady=6)
        ttk.Button(controls, textvariable=self.text('browse'), command=self.choose_directory).grid(row=4, column=1, padx=(8, 0))
        ttk.Checkbutton(controls, textvariable=self.text('clear_label'), variable=self.clear).grid(row=5, column=0, columnspan=2, sticky='w', pady=10)
        ttk.Label(controls, textvariable=self.text('keep_hint'), wraplength=390).grid(row=6, column=0, columnspan=2, sticky='w')
        panel = ttk.LabelFrame(self, padding=8)
        panel.configure(labelwidget=ttk.Label(panel, textvariable=self.text('log_label')))
        panel.grid(row=0, column=1, sticky='nsew', padx=(0, 18), pady=18)
        self.output = scrolledtext.ScrolledText(panel, state='disabled', width=45, wrap='word')
        self.output.pack(fill='both', expand=True)
        self.build_menu()
        self.refresh_language()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(100, self.poll)

    def text(self, key):
        variable = tk.StringVar(value=tr(key))
        self.text_variables.setdefault(key, []).append(variable)
        return variable

    def build_menu(self):
        menu = tk.Menu(self)
        settings = tk.Menu(menu, tearoff=False)
        languages = tk.Menu(settings, tearoff=False)
        languages.add_radiobutton(label=tr('system_language'), variable=self.language,
                                 value='', command=self.refresh_language)
        for code, data in translator.languages.items():
            languages.add_radiobutton(label=data['name'], variable=self.language,
                                     value=code, command=self.refresh_language)
        settings.add_cascade(label=tr('language_menu'), menu=languages)
        menu.add_cascade(label=tr('settings_menu'), menu=settings)
        self.configure(menu=menu)
        self.menu_bar, self.settings_menu, self.language_menu = menu, settings, languages

    def refresh_language(self):
        translator.select(self.language.get())
        self.title(tr('title'))
        for key, variables in self.text_variables.items():
            for variable in variables:
                variable.set(tr(key))
        self.menu_bar.entryconfigure(0, label=tr('settings_menu'))
        self.settings_menu.entryconfigure(0, label=tr('language_menu'))
        self.language_menu.entryconfigure(0, label=tr('system_language'))

    def schedule_settings_save(self, *_):
        if self.settings_timer is not None:
            self.after_cancel(self.settings_timer)
        self.settings_timer = self.after(500, self.persist_settings)

    def persist_settings(self):
        if self.settings_timer is not None:
            self.after_cancel(self.settings_timer)
            self.settings_timer = None
        try:
            save_settings(SETTINGS_PATH, {
                'archive': self.archive.get(),
                'directory': self.directory.get(),
                'clear': self.clear.get(),
                'language': self.language.get(),
            })
        except OSError as error:
            self.events.put(('log', tr('save_error', error=error)))
            return False
        return True

    def choose_archive(self):
        path = filedialog.asksaveasfilename(title=tr('choose_archive'), defaultextension='.zip', filetypes=[(tr('zip_files'), '*.zip')], confirmoverwrite=False)
        if path:
            self.archive.set(path)

    def choose_directory(self):
        path = filedialog.askdirectory(title=tr('choose_directory'), mustexist=False)
        if path:
            self.directory.set(path)

    def start(self, upwards):
        if self.busy:
            return
        if not self.archive.get().strip() or not self.directory.get().strip():
            messagebox.showerror(tr('missing_path'), tr('enter_paths'))
            return
        archive = Path(self.archive.get().strip()).expanduser()
        directory = Path(self.directory.get().strip()).expanduser()
        clear = self.clear.get()
        if upwards and archive.exists():
            if not messagebox.askyesno(tr('replace_title'), tr('replace_question', archive=archive)):
                return
        if not upwards and clear:
            if not messagebox.askyesno(tr('clear_title'), tr('clear_question', directory=directory), icon='warning'):
                return
        self.busy = True
        self.up.state(['disabled'])
        self.down.state(['disabled'])
        self.events.put(('log', tr('creating') if upwards else tr('extracting')))

        def work():
            try:
                log = lambda text: self.events.put(('log', text))
                if upwards:
                    create_archive(archive, directory, log)
                else:
                    extract_archive(archive, directory, clear, log)
            except Exception as error:
                self.events.put(('log', tr('error', error=error)))
            finally:
                self.events.put(('done', ''))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        for _ in range(200):
            try:
                kind, text = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'done':
                self.busy = False
                self.up.state(['!disabled'])
                self.down.state(['!disabled'])
            else:
                self.output.configure(state='normal')
                self.output.insert('end', text + '\n')
                self.output.see('end')
                self.output.configure(state='disabled')
        self.after(100, self.poll)

    def close(self):
        if self.busy:
            messagebox.showinfo(tr('busy_title'), tr('wait'))
        else:
            if not self.persist_settings():
                messagebox.showerror(tr('save_title'),
                                     tr('save_failed'))
                return
            self.destroy()


if __name__ == '__main__':
    SpaceSync().mainloop()
