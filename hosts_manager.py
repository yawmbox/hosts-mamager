import customtkinter as ctk
from tkinter import messagebox
import json
import os
import locale
import subprocess
import re
import shutil

class HostsParser:
    def __init__(self, filepath="/etc/hosts"):
        self.filepath = filepath
        self.lines = []
        self.entries = [] 
        self.load()
        
    def load(self):
        if not os.path.exists(self.filepath):
            # Fallback for Windows or if file doesn't exist
            if os.name == 'nt':
                self.filepath = r"C:\Windows\System32\drivers\etc\hosts"
            if not os.path.exists(self.filepath):
                self.lines = []
                self.entries = []
                return

        with open(self.filepath, 'r') as f:
            self.lines = f.readlines()
            
        self.entries = []
        # Regex to match a hosts line: optional `#`, IP, Hostname(s), optional `# comment`
        pattern = re.compile(r'^\s*(?P<comment_start>#)?\s*(?P<ip>\d{1,3}(?:\.\d{1,3}){3}|[a-fA-F0-9:]+)\s+(?P<hostnames>[^\s#]+(?:\s+[^\s#]+)*)\s*(?:#\s*(?P<trailing_comment>.*))?$')
        
        for i, line in enumerate(self.lines):
            match = pattern.match(line)
            if match:
                self.entries.append({
                    'index': i,
                    'active': not bool(match.group('comment_start')),
                    'ip': match.group('ip'),
                    'hostname': match.group('hostnames'),
                    'comment': match.group('trailing_comment') or ''
                })

    def get_all_entries(self):
        return self.entries

    def update_entry(self, entry_list_index, active, ip, hostname, comment):
        entry = self.entries[entry_list_index]
        entry['active'] = active
        entry['ip'] = ip
        entry['hostname'] = hostname
        entry['comment'] = comment
        # We replace the line in the original lines array
        self.lines[entry['index']] = self._format_line(entry)

    def add_entry(self, active, ip, hostname, comment):
        # make sure previous last line has newline if self.lines is not empty
        if self.lines and self.lines[-1] is not None and not self.lines[-1].endswith('\n'):
            self.lines[-1] += '\n'
            
        entry = {
            'index': len(self.lines),
            'active': active,
            'ip': ip,
            'hostname': hostname,
            'comment': comment
        }
        self.entries.append(entry)
        self.lines.append(self._format_line(entry) + '\n')

    def delete_entry(self, entry_list_index):
        entry = self.entries.pop(entry_list_index)
        self.lines[entry['index']] = None 

    def _format_line(self, entry):
        prefix = "" if entry['active'] else "# "
        suffix = f"\t# {entry['comment']}" if entry['comment'] else ""
        return f"{prefix}{entry['ip']}\t{entry['hostname']}{suffix}"

    def get_file_content(self):
        out = []
        for line in self.lines:
            if line is not None:
                if not line.endswith('\n'):
                    line += '\n'
                out.append(line)
        return "".join(out)


class HostsManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Hosts Manager")
        self.geometry("900x600")
        self.minsize(800, 500)
        
        # Determine language
        self.locales = {}
        self.load_locales()
        self.current_lang = self.detect_language()
        
        # App State
        self.hosts_parser = HostsParser()
        self.unsaved_changes = False
        
        # UI Setup
        self.setup_ui()
        self.populate_list()
        self.update_texts()
        self._center_main_window()

    def _center_main_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")

    def load_locales(self):
        try:
            with open(os.path.join(os.path.dirname(__file__), 'locales.json'), 'r', encoding='utf-8') as f:
                self.locales = json.load(f)
        except Exception as e:
            print(f"Error loading locales: {e}")
            self.locales = {
                "EN": { "app_title": "Hosts Manager", "btn_add": "Add", "btn_edit": "Edit", "btn_delete": "Delete", 
                        "btn_toggle": "Toggle", "btn_save": "Save Changes", "btn_help": "Help", "language": "Language:" }
            }

    def detect_language(self):
        try:
            sys_lang = locale.getdefaultlocale()[0]
            if sys_lang:
                lang_code = sys_lang[:2].upper()
                if lang_code in self.locales:
                    return lang_code
        except:
            pass
        return "EN"

    def t(self, key):
        return self.locales.get(self.current_lang, self.locales.get("EN")).get(key, key)

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # TOP BAR
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.lbl_title = ctk.CTkLabel(self.top_frame, text="Hosts Manager", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_title.pack(side="left", padx=10)
        
        self.lang_var = ctk.StringVar(value=self.current_lang)
        
        self.btn_exit = ctk.CTkButton(self.top_frame, text="Exit", command=self.quit, width=80, fg_color="#ef4444", hover_color="#b91c1c")
        self.btn_exit.pack(side="right", padx=10)

        self.combo_lang = ctk.CTkComboBox(self.top_frame, values=list(self.locales.keys()), variable=self.lang_var, command=self.change_language, width=80)
        self.combo_lang.pack(side="right", padx=5)

        self.btn_help = ctk.CTkButton(self.top_frame, text="Help", command=self.show_help, width=80, fg_color="#4b5563", hover_color="#374151")
        self.btn_help.pack(side="right", padx=15)

        # MAIN LIST AREA
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        self.list_frame.grid_columnconfigure(0, weight=1) # Status
        self.list_frame.grid_columnconfigure(1, weight=3) # IP
        self.list_frame.grid_columnconfigure(2, weight=4) # Hostname
        self.list_frame.grid_columnconfigure(3, weight=5) # Comment
        
        # Headers inside scrollable frame (not ideal but works, better to put outside or just inside)
        self.header_frame = ctk.CTkFrame(self, corner_radius=0)
        self.header_frame.grid(row=1, column=0, sticky="new", padx=15, pady=(2,0)) # Overlaying top
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=3)
        self.header_frame.grid_columnconfigure(2, weight=4)
        self.header_frame.grid_columnconfigure(3, weight=5)
        
        self.lbl_h_status = ctk.CTkLabel(self.header_frame, text="Status", font=ctk.CTkFont(weight="bold"))
        self.lbl_h_status.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.lbl_h_ip = ctk.CTkLabel(self.header_frame, text="IP", font=ctk.CTkFont(weight="bold"))
        self.lbl_h_ip.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.lbl_h_host = ctk.CTkLabel(self.header_frame, text="Hostname", font=ctk.CTkFont(weight="bold"))
        self.lbl_h_host.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.lbl_h_comment = ctk.CTkLabel(self.header_frame, text="Comment", font=ctk.CTkFont(weight="bold"))
        self.lbl_h_comment.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # BOTTOM BAR (Buttons)
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        self.btn_add = ctk.CTkButton(self.bottom_frame, text="Add", command=self.add_host)
        self.btn_add.pack(side="left", padx=5, pady=10)
        
        self.btn_edit = ctk.CTkButton(self.bottom_frame, text="Edit", command=self.edit_host)
        self.btn_edit.pack(side="left", padx=5, pady=10)
        
        self.btn_delete = ctk.CTkButton(self.bottom_frame, text="Delete", command=self.delete_host, fg_color="#ef4444", hover_color="#b91c1c")
        self.btn_delete.pack(side="left", padx=5, pady=10)
        
        self.btn_toggle = ctk.CTkButton(self.bottom_frame, text="Toggle", command=self.toggle_host, fg_color="#f59e0b", hover_color="#d97706")
        self.btn_toggle.pack(side="left", padx=5, pady=10)
        
        self.btn_save = ctk.CTkButton(self.bottom_frame, text="Save Changes", command=self.save_hosts, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(weight="bold"))
        self.btn_save.pack(side="right", padx=10, pady=10)

        # STATE
        self.row_frames = []
        self.selected_index = -1

    def update_texts(self):
        self.title(self.t("app_title"))
        self.lbl_title.configure(text=self.t("app_title"))
        self.btn_help.configure(text=self.t("btn_help"))
        self.btn_exit.configure(text=self.t("btn_exit"))
        self.lbl_h_status.configure(text=self.t("col_status"))
        self.lbl_h_ip.configure(text=self.t("col_ip"))
        self.lbl_h_host.configure(text=self.t("col_host"))
        self.lbl_h_comment.configure(text=self.t("col_comment"))
        self.btn_add.configure(text=self.t("btn_add"))
        self.btn_edit.configure(text=self.t("btn_edit"))
        self.btn_delete.configure(text=self.t("btn_delete"))
        self.btn_toggle.configure(text=self.t("btn_toggle"))
        
        save_text = self.t("btn_save")
        if self.unsaved_changes:
            save_text = f"*{save_text}*"
        self.btn_save.configure(text=save_text)
        
        self.populate_list()

    def change_language(self, lang):
        self.current_lang = lang
        self.update_texts()

    def select_row(self, index, event=None):
        self.selected_index = index
        for i, frame in enumerate(self.row_frames):
            if i == index:
                frame.configure(fg_color=("#d1d5db", "#374151"))
            else:
                frame.configure(fg_color="transparent")

    def populate_list(self):
        # Clear existing
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.row_frames = []
        
        # Add spacing for the fixed header
        spacer = ctk.CTkFrame(self.list_frame, height=30, fg_color="transparent")
        spacer.grid(row=0, column=0, columnspan=4)
        
        entries = self.hosts_parser.get_all_entries()
        
        for i, entry in enumerate(entries):
            row_frame = ctk.CTkFrame(self.list_frame, fg_color="transparent", corner_radius=0)
            row_frame.grid(row=i+1, column=0, columnspan=4, sticky="ew", pady=1)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=3)
            row_frame.grid_columnconfigure(2, weight=4)
            row_frame.grid_columnconfigure(3, weight=5)
            
            # Make the entire row clickable
            row_frame.bind("<Button-1>", lambda e, idx=i: self.select_row(idx, e))
            row_frame.bind("<Double-1>", lambda e, idx=i: self.on_double_click(idx, e))
            
            status_text = "🟢" if entry['active'] else "⚫"
            color = ("#000000", "#dce4ee") if entry['active'] else "gray"

            lbl_s = ctk.CTkLabel(row_frame, text=status_text)
            lbl_s.grid(row=0, column=0, padx=5, pady=5, sticky="w")
            lbl_s.bind("<Button-1>", lambda e, idx=i: self.select_row(idx, e))
            lbl_s.bind("<Double-1>", lambda e, idx=i: self.on_double_click(idx, e))
            
            lbl_i = ctk.CTkLabel(row_frame, text=entry['ip'], text_color=color)
            lbl_i.grid(row=0, column=1, padx=5, pady=5, sticky="w")
            lbl_i.bind("<Button-1>", lambda e, idx=i: self.select_row(idx, e))
            lbl_i.bind("<Double-1>", lambda e, idx=i: self.on_double_click(idx, e))
            
            lbl_h = ctk.CTkLabel(row_frame, text=entry['hostname'], text_color=color)
            lbl_h.grid(row=0, column=2, padx=5, pady=5, sticky="w")
            lbl_h.bind("<Button-1>", lambda e, idx=i: self.select_row(idx, e))
            lbl_h.bind("<Double-1>", lambda e, idx=i: self.on_double_click(idx, e))
            
            lbl_c = ctk.CTkLabel(row_frame, text=entry['comment'], text_color=color)
            lbl_c.grid(row=0, column=3, padx=5, pady=5, sticky="w")
            lbl_c.bind("<Button-1>", lambda e, idx=i: self.select_row(idx, e))
            lbl_c.bind("<Double-1>", lambda e, idx=i: self.on_double_click(idx, e))
            
            self.row_frames.append(row_frame)
            
        if self.selected_index >= 0 and self.selected_index < len(self.row_frames):
            self.select_row(self.selected_index)

    def on_double_click(self, index, event=None):
        self.select_row(index)
        self.edit_host()

    def mark_unsaved(self):
        self.unsaved_changes = True
        self.btn_save.configure(text=f"*{self.t('btn_save')}*")

    def toggle_host(self):
        if self.selected_index < 0:
            messagebox.showwarning("Warning", self.t("err_select_item"))
            return
            
        entry = self.hosts_parser.get_all_entries()[self.selected_index]
        self.hosts_parser.update_entry(self.selected_index, not entry['active'], entry['ip'], entry['hostname'], entry['comment'])
        self.mark_unsaved()
        self.populate_list()

    def delete_host(self):
        if self.selected_index < 0:
            messagebox.showwarning("Warning", self.t("err_select_item"))
            return
            
        if messagebox.askyesno("Confirm", self.t("msg_confirm_delete")):
            self.hosts_parser.delete_entry(self.selected_index)
            self.selected_index = -1
            self.mark_unsaved()
            self.populate_list()

    def edit_host(self):
        if self.selected_index < 0:
            messagebox.showwarning("Warning", self.t("err_select_item"))
            return
        entry = self.hosts_parser.get_all_entries()[self.selected_index]
        self.open_editor_modal(self.t("title_edit"), entry)

    def add_host(self):
        self.open_editor_modal(self.t("title_add"))

    def open_editor_modal(self, title, entry=None):
        modal = ctk.CTkToplevel(self)
        modal.title(title)
        modal.geometry("400x350")
        
        ctk.CTkLabel(modal, text=self.t("lbl_ip")).pack(pady=(20,0), padx=20, anchor="w")
        ent_ip = ctk.CTkEntry(modal, width=360)
        ent_ip.pack(pady=(0,10), padx=20)
        
        ctk.CTkLabel(modal, text=self.t("lbl_host")).pack(pady=0, padx=20, anchor="w")
        ent_host = ctk.CTkEntry(modal, width=360)
        ent_host.pack(pady=(0,10), padx=20)
        
        ctk.CTkLabel(modal, text=self.t("lbl_comment")).pack(pady=0, padx=20, anchor="w")
        ent_comment = ctk.CTkEntry(modal, width=360)
        ent_comment.pack(pady=(0,20), padx=20)
        
        is_active = ctk.BooleanVar(value=True)
        chk_active = ctk.CTkCheckBox(modal, text="Active", variable=is_active)
        chk_active.pack(pady=10, padx=20, anchor="w")
        
        if entry:
            ent_ip.insert(0, entry['ip'])
            ent_host.insert(0, entry['hostname'])
            if entry['comment']:
                ent_comment.insert(0, entry['comment'])
            is_active.set(entry['active'])
        else:
            ent_ip.insert(0, "127.0.0.1")

        def save_modal():
            ip = ent_ip.get().strip()
            host = ent_host.get().strip()
            comment = ent_comment.get().strip()
            
            if not ip:
                messagebox.showerror("Error", self.t("err_invalid_ip"))
                return
            if not host:
                messagebox.showerror("Error", self.t("err_invalid_host"))
                return
                
            if entry:
                self.hosts_parser.update_entry(self.selected_index, is_active.get(), ip, host, comment)
            else:
                self.hosts_parser.add_entry(is_active.get(), ip, host, comment)
                
            self.mark_unsaved()
            self.populate_list()
            modal.destroy()

        btn_frame = ctk.CTkFrame(modal, fg_color="transparent")
        btn_frame.pack(pady=10, fill="x")
        
        ctk.CTkButton(btn_frame, text=self.t("btn_cancel"), command=modal.destroy, fg_color="gray").pack(side="left", padx=20)
        ctk.CTkButton(btn_frame, text=self.t("btn_confirm"), command=save_modal).pack(side="right", padx=20)

        # Center modal
        modal.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (modal.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (modal.winfo_height() // 2)
        modal.geometry(f"+{x}+{y}")
        modal.transient(self)
        modal.grab_set()

    def save_hosts(self):
        new_content = self.hosts_parser.get_file_content()
        target_file = self.hosts_parser.filepath
        
        # Save mechanism
        try:
            # First, check if we have write permission natively
            if os.access(target_file, os.W_OK):
                # We do! (Maybe running as admin/root, or Windows)
                self._backup_host_if_needed(target_file)
                with open(target_file, 'w') as f:
                    f.write(new_content)
                self._on_save_success()
            else:
                # We need elevated privileges
                if os.name == 'nt':
                    messagebox.showerror(self.t("msg_error"), "Please run the application as Administrator to save changes.")
                    return
                else:
                    # Write to temp file
                    temp_path = "/tmp/hosts_manager_temp"
                    with open(temp_path, 'w') as f:
                        f.write(new_content)
                    self._prompt_for_sudo(temp_path, target_file)
                        
        except Exception as e:
            messagebox.showerror(self.t("msg_error"), str(e))

    def _prompt_for_sudo(self, temp_path, target_file):
        modal = ctk.CTkToplevel(self)
        modal.title(self.t("app_title"))
        modal.geometry("320x160")
        
        lbl = ctk.CTkLabel(modal, text="Password Amministratore (sudo):")
        lbl.pack(pady=(20, 10))
        
        ent = ctk.CTkEntry(modal, width=220, show="*")
        ent.pack(pady=0)
        ent.focus_set()
        
        def on_confirm(event=None):
            pwd = ent.get()
            modal.destroy()
            self._execute_sudo(pwd, temp_path, target_file)
            
        ent.bind("<Return>", on_confirm)
        
        btn = ctk.CTkButton(modal, text=self.t("btn_confirm"), command=on_confirm)
        btn.pack(pady=20)
        
        modal.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (modal.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (modal.winfo_height() // 2)
        modal.geometry(f"+{x}+{y}")
        modal.transient(self)
        modal.grab_set()

    def _execute_sudo(self, pwd, temp_path, target_file):
        try:
            self._backup_host_if_needed(target_file, with_sudo=True, pwd=pwd)
            cmd = ['sudo', '-S', 'sh', '-c', f'cat {temp_path} > {target_file}']
            res = subprocess.run(cmd, input=(pwd + '\n').encode(), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            if res.returncode == 0:
                self._on_save_success()
            else:
                err = res.stderr.decode().strip()
                messagebox.showerror("Sudo Error", err if err else "Authentication failed. Incorrect password?")
        except Exception as e:
            messagebox.showerror(self.t("msg_error"), str(e))

    def _backup_host_if_needed(self, target_file, with_sudo=False, pwd=None):
        backup_file = target_file + ".bak"
        if not os.path.exists(backup_file):
            if with_sudo and pwd:
                subprocess.run(['sudo', '-S', 'cp', target_file, backup_file], input=(pwd + '\n').encode(), stderr=subprocess.PIPE)
            else:
                shutil.copy2(target_file, backup_file)

    def _on_save_success(self):
        self.unsaved_changes = False
        self.btn_save.configure(text=self.t("btn_save"))
        messagebox.showinfo("Success", self.t("msg_saved"))

    def show_help(self):
        modal = ctk.CTkToplevel(self)
        modal.title(self.t("title_help"))
        modal.geometry("500x400")
        
        txt = ctk.CTkTextbox(modal, wrap="word", font=ctk.CTkFont(size=14))
        txt.pack(fill="both", expand=True, padx=20, pady=20)
        txt.insert("1.0", self.t("help_text"))
        txt.configure(state="disabled")
        
        ctk.CTkButton(modal, text=self.t("btn_cancel"), command=modal.destroy).pack(pady=(0,20))

        # Center modal
        modal.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (modal.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (modal.winfo_height() // 2)
        modal.geometry(f"+{x}+{y}")
        modal.transient(self)

if __name__ == "__main__":
    app = HostsManagerApp()
    app.mainloop()
