import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from config import *
from core.video_engine import run_goddess_app

class ModernButton(tk.Button):
    def __init__(self, master, **kw):
        self.bg_norm = kw.pop("bg", C_BTN_SEC)
        self.bg_hover = kw.pop("activebackground", C_BTN_SEC_H)
        self.fg_norm = kw.pop("fg", C_TEXT_MAIN)
        self.is_selected = False
        self.selected_bg = C_ACCENT
        self.selected_fg = "#000000" 
        super().__init__(master, relief="flat", bd=0, bg=self.bg_norm, fg=self.fg_norm, cursor="hand2", **kw)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        if not self.is_selected: self.config(bg=self.bg_hover)

    def on_leave(self, e):
        if not self.is_selected: self.config(bg=self.bg_norm)
            
    def set_selected(self, state):
        self.is_selected = state
        if state: self.config(bg=self.selected_bg, fg=self.selected_fg)
        else: self.config(bg=self.bg_norm, fg=self.fg_norm)

class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LATINOW - Statua animata")
        self.geometry("1050x720")
        self.configure(bg=C_BG_MAIN)
        self.resizable(False, False)
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(screen_w - 1050) // 2}+{(screen_h - 720) // 2}")
        self.deities = self._scan_deities()
        self.selected_deity = tk.StringVar()
        self._build_ui()
        if self.deities:
            self._select_deity(list(self.deities.keys())[0])

    def _scan_deities(self):
        base_path = os.path.join("assets", "statue")
        d_dict = {}
        if not os.path.exists(base_path): os.makedirs(base_path, exist_ok=True)
        for genere in ["maschio", "femmina"]:
            genere_path = os.path.join(base_path, genere)
            if not os.path.exists(genere_path): 
                os.makedirs(genere_path, exist_ok=True)
                continue
            for item in os.listdir(genere_path):
                p = os.path.join(genere_path, item)
                if os.path.isdir(p):
                    voce = "im_nicola" if genere == "maschio" else "if_sara"
                    d_dict[item] = {
                        "talk": os.path.join(p, "video", "talk.mp4"),
                        "idle": os.path.join(p, "video", "idle.mp4"),
                        "audio": os.path.join(p, "audio", "traccia.mp3"),
                        "frasi": os.path.join(p, "frasi", "default.txt"),
                        "voce": voce 
                    }
        return d_dict

    def _build_ui(self):
        header = tk.Frame(self, bg=C_BG_MAIN, pady=25)
        header.pack(side="top", fill="x")
        tk.Label(header, text="LATINOW", font=F_HEADER, bg=C_BG_MAIN, fg=C_ACCENT).pack()
        tk.Label(header, text="Anima la statua che preferisci", font=F_BODY, bg=C_BG_MAIN, fg=C_TEXT_SUB).pack()
        bottom_bar = tk.Frame(self, bg=C_SIDEBAR, height=90)
        bottom_bar.pack(side="bottom", fill="x")
        bottom_bar.pack_propagate(False)
        ModernButton(
            bottom_bar, text="▶ AVVIA PROIEZIONE", font=F_BTN_L, 
            bg=C_SUCCESS, fg="#000000", activebackground="#00c853", 
            width=26, pady=12, command=self._start_app
        ).pack(side="right", padx=40, pady=15)
        main_container = tk.Frame(self, bg=C_BG_MAIN)
        main_container.pack(side="top", fill="both", expand=True, padx=40, pady=(10, 20))
        left_col = tk.Frame(main_container, bg=C_PANEL, padx=25, pady=25)
        left_col.pack(side="left", fill="y", expand=False)
        tk.Label(left_col, text="SCEGLI LA TUA STATUA:", font=F_TITLE, bg=C_PANEL, fg=C_TEXT_MAIN).pack(anchor="w", padx=8, pady=(0, 20))
        grid_frame = tk.Frame(left_col, bg=C_PANEL)
        grid_frame.pack()
        self.deity_buttons = {}
        row, col = 0, 0
        for name in self.deities.keys():
            btn = ModernButton(grid_frame, text=name.upper(), font=F_BTN, width=15, height=3, command=lambda n=name: self._select_deity(n))
            btn.grid(row=row, column=col, padx=8, pady=8)
            self.deity_buttons[name] = btn
            col += 1
            if col > 1: col = 0; row += 1
        right_col = tk.Frame(main_container, bg=C_BG_MAIN)
        right_col.pack(side="right", fill="both", expand=True, padx=(35, 0))
        guide_frame = tk.Frame(right_col, bg=C_SIDEBAR, padx=20, pady=15)
        guide_frame.pack(fill="x", pady=(0, 20))
        tk.Label(guide_frame, text="📌 TASTI DI CONTROLLO PROIEZIONE", font=F_TITLE, bg=C_SIDEBAR, fg=C_ACCENT).pack(anchor="w")
        tk.Label(guide_frame, text="(Da usare sulla tastiera SOLO mentre la statua è in proiezione)", font=F_BODY, bg=C_SIDEBAR, fg=C_TEXT_SUB).pack(anchor="w", pady=(2, 12))
        cmd_inner = tk.Frame(guide_frame, bg=C_SIDEBAR)
        cmd_inner.pack(fill="x", pady=(0, 5))
        commands = [
            ("Q", "Chiudi proiezione", 0, 0), ("N", "Vai alla prossima frase", 0, 1),
            ("R", "Ripeti la frase", 1, 0), ("SPAZIO", "Ruota video", 1, 1)
        ]
        for key, desc, r, c in commands:
            f = tk.Frame(cmd_inner, bg=C_SIDEBAR)
            f.grid(row=r, column=c, sticky="w", padx=(0, 40), pady=4)
            tk.Label(f, text=f"[{key}]", font=("Consolas", 12, "bold"), bg=C_SIDEBAR, fg=C_ACCENT).pack(side="left")
            tk.Label(f, text=desc, font=F_BODY, bg=C_SIDEBAR, fg=C_TEXT_MAIN).pack(side="left", padx=(8, 0))
        text_header = tk.Frame(right_col, bg=C_BG_MAIN)
        text_header.pack(fill="x", pady=(0, 10))
        self.lbl_frasi = tk.Label(text_header, text="FRASI CHE LA STATUA RECITERÀ", font=F_TITLE, bg=C_BG_MAIN, fg=C_TEXT_MAIN)
        self.lbl_frasi.pack(side="left")
        ModernButton(
            text_header, text="🗑 Svuota frasi", font=F_BTN, bg=C_ERROR, activebackground="#d50000", 
            padx=10, pady=4, command=self._clear_text
        ).pack(side="right", padx=(10, 0))
        ModernButton(
            text_header, text="📁 Importa frasi", font=F_BTN, bg=C_BTN_PRIM, activebackground=C_BTN_HOVER, 
            padx=10, pady=4, command=self._load_txt_file
        ).pack(side="right")
        text_container = tk.Frame(right_col, bg=C_ACCENT, bd=1) 
        text_container.pack(fill="both", expand=True)
        self.text_area = scrolledtext.ScrolledText(
            text_container, wrap="word", font=F_BODY, bg=C_PANEL, fg=C_TEXT_MAIN, 
            bd=0, padx=20, pady=20, insertbackground=C_ACCENT, highlightthickness=0
        )
        self.text_area.pack(fill="both", expand=True, padx=1, pady=1)

    def _select_deity(self, name):
        self.selected_deity.set(name)
        self.lbl_frasi.config(text=f"FRASI CHE {name.upper()} RECITERÀ")
        for b_name, btn in self.deity_buttons.items(): btn.set_selected(b_name == name)
        paths = self.deities.get(name)
        if paths and os.path.exists(paths["frasi"]):
            with open(paths["frasi"], 'r', encoding='utf-8') as f:
                content = f.read()
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, content)

    def _clear_text(self):
        self.text_area.delete("1.0", tk.END)

    def _load_txt_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if filepath:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, content)

    def _start_app(self):
        text_content = self.text_area.get("1.0", tk.END).strip()
        lines = [l.strip() for l in text_content.split('\n') if l.strip()]
        if not lines:
            messagebox.showwarning("Area Vuota", "Inserisci le frasi testuali che la statua reciterà.")
            return
        paths = self.deities[self.selected_deity.get()]
        self.withdraw()
        try: 
            run_goddess_app(paths["talk"], paths["idle"], paths["audio"], lines, paths["voce"])
        except Exception as e: 
            pass
        self.deiconify()