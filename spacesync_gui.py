"""Tkinter-Oberfläche für SpaceSync; wird nur im GUI-Modus importiert."""
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from pathlib import Path
import webbrowser

from spacesync import (SETTINGS_PATH, LANGUAGES_PATH, Translator, translator, tr,
                       load_settings, save_settings, create_archive, extract_archive,
                       manual_sections, export_manual_pdf)


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
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label=tr('about_title'), command=self.show_about)
        help_menu.add_command(label=tr('manual_title'), command=self.show_manual)
        menu.add_cascade(label=tr('help_menu'), menu=help_menu)
        self.configure(menu=menu)
        self.menu_bar, self.settings_menu, self.language_menu = menu, settings, languages
        self.help_menu = help_menu

    def show_about(self):
        dialog = tk.Toplevel(self)
        dialog.title(tr('about_title'))
        dialog.transient(self)
        dialog.resizable(False, False)
        content = ttk.Frame(dialog, padding=24)
        content.pack(fill='both', expand=True)
        ttk.Label(content, text='SpaceSync', font=('TkDefaultFont', 18, 'bold')).pack(pady=(0, 16))
        ttk.Label(content, text=tr('author_label')).pack()
        ttk.Label(content, text='Python User Group\npySpaceBremen', justify='center').pack(pady=(4, 8))
        for label, url in [
            (None, 'https://pyspacebremen.de'),
            (tr('software_website'), 'https://github.com/pyspacebremen/spacesync'),
        ]:
            if label:
                ttk.Label(content, text=label).pack(pady=(16, 4))
            ttk.Button(content, text=url, command=lambda address=url: webbrowser.open(address)).pack(fill='x')
        close = ttk.Button(content, text=tr('close'), command=dialog.destroy)
        close.pack(pady=(20, 0))
        dialog.bind('<Escape>', lambda event: dialog.destroy())
        dialog.grab_set()
        close.focus_set()

    def show_manual(self):
        # Keep dialog and exported document in the same selected language.
        translate = Translator(LANGUAGES_PATH)
        translate.select(translator.code)
        dialog = tk.Toplevel(self)
        dialog.title(translate('manual_title'))
        dialog.transient(self)
        dialog.geometry('760x650')
        dialog.minsize(480, 350)
        content = ttk.Frame(dialog, padding=16)
        content.pack(fill='both', expand=True)
        text = scrolledtext.ScrolledText(content, wrap='word', padx=12, pady=12)
        text.pack(fill='both', expand=True)
        text.tag_configure('heading', font=('TkDefaultFont', 12, 'bold'), spacing1=12, spacing3=6)
        for heading, body in manual_sections(translate):
            text.insert('end', heading + '\n', 'heading')
            text.insert('end', body + '\n\n')
        text.configure(state='disabled')
        buttons = ttk.Frame(content)
        buttons.pack(fill='x', pady=(12, 0))

        def export():
            path = filedialog.asksaveasfilename(
                parent=dialog, title=translate('export_pdf'), defaultextension='.pdf',
                initialfile=f'spacesync-manual-{translate.code}.pdf',
                filetypes=[('PDF', '*.pdf')])
            if not path:
                return
            try:
                export_manual_pdf(path, translate)
            except ImportError:
                messagebox.showerror(translate('export_pdf'), translate('pdf_dependency'), parent=dialog)
            except Exception as error:
                messagebox.showerror(translate('export_pdf'), translate('error', error=error), parent=dialog)
            else:
                messagebox.showinfo(translate('export_pdf'), translate('pdf_saved', path=path), parent=dialog)

        ttk.Button(buttons, text=translate('export_pdf'), command=export).pack(side='left')
        ttk.Button(buttons, text=translate('close'), command=dialog.destroy).pack(side='right')
        dialog.bind('<Escape>', lambda event: dialog.destroy())
        dialog.grab_set()
        text.focus_set()

    def refresh_language(self):
        translator.select(self.language.get())
        self.title(tr('title'))
        for key, variables in self.text_variables.items():
            for variable in variables:
                variable.set(tr(key))
        self.menu_bar.entryconfigure(0, label=tr('settings_menu'))
        self.settings_menu.entryconfigure(0, label=tr('language_menu'))
        self.language_menu.entryconfigure(0, label=tr('system_language'))
        self.menu_bar.entryconfigure(1, label=tr('help_menu'))
        self.help_menu.entryconfigure(0, label=tr('about_title'))
        self.help_menu.entryconfigure(1, label=tr('manual_title'))

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

