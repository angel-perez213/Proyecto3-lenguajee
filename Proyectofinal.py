import tkinter as tk
from tkinter import ttk, messagebox
import re

# --- Configuración ---
PROJECT_TITLE = "Proyecto Final — Simulador de Máquina de Turing"
PROJECT_SUBTITLE = "Visualización paso a paso + Laboratorio de Expresiones Regulares"
BLANK = "_"

# --- Núcleo de Máquina de Turing ---
class TuringMachine:
    def __init__(self, transitions, start_state, accept_states, reject_states=None, tape=None):
        self.transitions = transitions
        self.start_state = start_state
        self.accept_states = set(accept_states)
        self.reject_states = set(reject_states or [])
        self.reset(list(tape) if tape is not None else [])

    def reset(self, tape_list):
        self.tape = list(tape_list) if tape_list else [BLANK]
        self.head = 0
        self.state = self.start_state
        self.halted = False
        self.result = None

    def load_input(self, w: str):
        self.reset(list(w if w else ""))

    def _read(self):
        if self.head < 0:
            self.tape.insert(0, BLANK); self.head = 0
        if self.head >= len(self.tape):
            self.tape.append(BLANK)
        return self.tape[self.head]

    def step(self):
        if self.halted:
            return 'halt'
        if self.state in self.accept_states:
            self.halted = True; self.result = True;  return 'accept'
        if self.state in self.reject_states:
            self.halted = True; self.result = False; return 'reject'

        sym = self._read()
        key = (self.state, sym)
        if key not in self.transitions:
            self.halted = True; self.result = False; return 'reject'

        write, move, next_state = self.transitions[key]
        self.tape[self.head] = write
        if move == "L": self.head -= 1
        elif move == "R": self.head += 1
        self.state = next_state
        return 'running'

# --- Máquinas de ejemplo ---
def tm_ends_with_abb():
    q0, q1, q2, q3, qacc, qrej = "q0","q1","q2","q3","qacc","qrej"
    tr = {}
    for ch in ("a","b"): tr[(q0,ch)] = (ch,"R",q0)
    tr[(q0,BLANK)] = (BLANK,"L",q1)
    tr[(q1,'b')] = ('b',"L",q2);  tr[(q1,'a')] = ('a',"S",qrej); tr[(q1,BLANK)] = (BLANK,"S",qrej)
    tr[(q2,'b')] = ('b',"L",q3);  tr[(q2,'a')] = ('a',"S",qrej); tr[(q2,BLANK)] = (BLANK,"S",qrej)
    tr[(q3,'a')] = ('a',"S",qacc); tr[(q3,'b')] = ('b',"S",qrej); tr[(q3,BLANK)] = (BLANK,"S",qrej)
    return TuringMachine(tr, q0, {qacc}, {qrej})

def tm_even_ones_binary():
    qE,qO,qacc,qrej = "qE","qO","qacc","qrej"
    tr = {
        (qE,'0'):('0',"R",qE),(qE,'1'):('1',"R",qO),(qE,BLANK):(BLANK,"S",qacc),
        (qO,'0'):('0',"R",qO),(qO,'1'):('1',"R",qE),(qO,BLANK):(BLANK,"S",qrej)
    }
    return TuringMachine(tr, qE, {qacc}, {qrej})

def tm_an_bn():
    q0,q1,q2,qcheck,qacc,qrej = "q0","q1","q2","qcheck","qacc","qrej"
    tr = {}
    tr[(q0,'X')] = ('X',"R",q0); tr[(q0,'Y')] = ('Y',"R",q0)
    tr[(q0,'a')] = ('X',"R",q1); tr[(q0,'b')] = ('b',"S",qrej)
    tr[(q0,BLANK)] = (BLANK,"L",qcheck)
    tr[(q1,'a')] = ('a',"R",q1); tr[(q1,'X')] = ('X',"R",q1); tr[(q1,'Y')] = ('Y',"R",q1)
    tr[(q1,'b')] = ('Y',"L",q2); tr[(q1,BLANK)] = (BLANK,"S",qrej)
    for ch in ('a','b','X','Y'): tr[(q2,ch)] = (ch,"L",q2)
    tr[(q2,BLANK)] = (BLANK,"R",q0)
    tr[(qcheck,'Y')] = ('Y',"L",qcheck); tr[(qcheck,'X')] = ('X',"L",qcheck)
    tr[(qcheck,'a')] = ('a',"S",qrej);   tr[(qcheck,'b')] = ('b',"S",qrej)
    tr[(qcheck,BLANK)] = (BLANK,"S",qacc)
    return TuringMachine(tr, q0, {qacc}, {qrej})

TM_LIBRARY = {
    "Termina en 'abb'  (Σ={a,b})": tm_ends_with_abb,
    "Paridad de '1'    (Σ={0,1})": tm_even_ones_binary,
    "a^n b^n (n≥1)     (Σ={a,b})": tm_an_bn,
}

# --- GUI ---
CELL_W, CELL_H, VISIBLE_CELLS = 36, 44, 20

class TMSimulatorGUI:
    def __init__(self, root):
        self.root = root
        root.title(PROJECT_TITLE)
        self._build_menu()

        self.notebook = ttk.Notebook(root)
        self.frame_tm = ttk.Frame(self.notebook)
        self.frame_regex = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_tm, text="Máquina de Turing")
        self.notebook.add(self.frame_regex, text="Regex Lab")
        self.notebook.pack(fill="both", expand=True)

        self._build_tm_tab()
        self._build_regex_tab()
        self.running = False

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label="Reiniciar", command=self._reset_all)
        m_file.add_separator()
        m_file.add_command(label="Salir", command=self.root.quit)
        menubar.add_cascade(label="Archivo", menu=m_file)
        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label="Acerca de", command=lambda: messagebox.showinfo("Acerca de", f"{PROJECT_TITLE}\n\n{PROJECT_SUBTITLE}"))
        menubar.add_cascade(label="Ayuda", menu=m_help)
        self.root.config(menu=menubar)

    def _reset_all(self):
        try: self.on_reset()
        except: pass

    # --- Pestaña TM ---
    def _build_tm_tab(self):
        top = ttk.Frame(self.frame_tm); top.pack(fill="x", padx=10, pady=8)
        ttk.Label(top, text="Máquina:").pack(side="left")
        self.cmb_machine = ttk.Combobox(top, values=list(TM_LIBRARY.keys()), state="readonly", width=30)
        self.cmb_machine.current(0); self.cmb_machine.pack(side="left", padx=6)
        ttk.Label(top, text="Entrada:").pack(side="left", padx=(16,2))
        self.ent_input = ttk.Entry(top, width=32); self.ent_input.pack(side="left")
        ttk.Button(top, text="Load", command=self.on_load).pack(side="left", padx=6)

        info = ttk.Frame(self.frame_tm); info.pack(fill="x", padx=10)
        self.lbl_state = ttk.Label(info, text="Estado: -"); self.lbl_state.pack(side="left")
        self.lbl_result = ttk.Label(info, text="Resultado: -"); self.lbl_result.pack(side="left", padx=20)

        self.canvas = tk.Canvas(self.frame_tm, width=CELL_W*VISIBLE_CELLS+2, height=CELL_H+60, bg="#111")
        self.canvas.pack(padx=10, pady=8)

        controls = ttk.Frame(self.frame_tm); controls.pack(fill="x", padx=10, pady=(4,10))
        ttk.Button(controls, text="Step", command=self.on_step).pack(side="left")
        self.btn_run = ttk.Button(controls, text="Run", command=self.on_run_pause); self.btn_run.pack(side="left", padx=6)
        ttk.Button(controls, text="Reset", command=self.on_reset).pack(side="left")
        ttk.Label(controls, text="Velocidad (ms):").pack(side="left", padx=(16,4))
        self.speed = tk.IntVar(value=120)
        ttk.Scale(controls, from_=20, to=800, orient="horizontal", variable=self.speed).pack(side="left", fill="x", expand=True)

        self.tm = None
        self.window_left_index = 0
        self.on_load()

    def draw_tape(self):
        self.canvas.delete("all")
        y0, x0 = 18, 10
        left = self.window_left_index
        right = left + VISIBLE_CELLS
        _ = self.tm._read()
        if self.tm.head < left + 3:
            self.window_left_index = max(0, self.tm.head - 3); left = self.window_left_index; right = left + VISIBLE_CELLS
        elif self.tm.head >= right - 3:
            self.window_left_index = max(0, self.tm.head - (VISIBLE_CELLS - 3)); left = self.window_left_index; right = left + VISIBLE_CELLS

        for i, idx in enumerate(range(left, right)):
            x = x0 + i*CELL_W
            self.canvas.create_rectangle(x, y0, x+CELL_W, y0+CELL_H, outline="#888", width=1)
            ch = self.tm.tape[idx] if 0 <= idx < len(self.tm.tape) else BLANK
            self.canvas.create_text(x+CELL_W/2, y0+CELL_H/2, text=ch, fill="#eee", font=("Consolas", 18, "bold"))
            if idx == self.tm.head:
                hx = x + CELL_W/2
                self.canvas.create_polygon(hx-10, y0-10, hx+10, y0-10, hx, y0-2, fill="#46f", outline="#46f")

        self.lbl_state.config(text=f"Estado: {self.tm.state}")
        if self.tm.halted:
            if self.tm.result is True:  self.lbl_result.config(text="Resultado: ACCEPT", foreground="#08b000")
            elif self.tm.result is False: self.lbl_result.config(text="Resultado: REJECT",  foreground="#d61a1a")
            else:                         self.lbl_result.config(text="Resultado: HALT",    foreground="#999")
        else:
            self.lbl_result.config(text="Resultado: (en ejecución)", foreground="#ccc")

    def on_load(self):
        maker = TM_LIBRARY[self.cmb_machine.get()]
        self.tm = maker()
        self.tm.load_input(self.ent_input.get().strip())
        self.window_left_index = 0
        self.running = False
        self.btn_run.config(text="Run")
        self.draw_tape()

    def on_step(self):
        if not self.tm: return
        status = self.tm.step()
        self.draw_tape()
        if status in ("accept","reject"):
            self.running = False; self.btn_run.config(text="Run")

    def on_run_pause(self):
        if not self.tm: return
        self.running = not self.running
        self.btn_run.config(text="Pause" if self.running else "Run")
        if self.running: self._auto_loop()

    def _auto_loop(self):
        if not self.running: return
        status = self.tm.step()
        self.draw_tape()
        if status in ("accept","reject"):
            self.running = False; self.btn_run.config(text="Run"); return
        self.root.after(max(10, int(self.speed.get())), self._auto_loop)

    def on_reset(self):
        if not self.tm: return
        self.tm.reset(list(self.ent_input.get().strip()))
        self.window_left_index = 0
        self.running = False
        self.btn_run.config(text="Run")
        self.draw_tape()

    # --- Pestaña Regex ---
    def _build_regex_tab(self):
        wrapper = ttk.Frame(self.frame_regex); wrapper.pack(fill="both", expand=True, padx=10, pady=10)
        patterns = [
            r"(a|b)*abb", r"0*1*", r"(ab)*", r"1(01)*0",
            r"(a|b)*a(a|b)*", r"a+", r"(01|10)+", r"(a|b){3,5}",
            r"0(0|1)*0", r"(?!.*11)1*0*",
        ]
        self.regex_patterns = patterns

        top = ttk.Frame(wrapper); top.pack(fill="x")
        ttk.Label(top, text="Expresión regular:").pack(side="left")
        self.cmb_regex = ttk.Combobox(top, values=patterns, state="readonly", width=38)
        self.cmb_regex.current(0); self.cmb_regex.pack(side="left", padx=6)
        ttk.Label(top, text="Cadena:").pack(side="left", padx=(12,4))
        self.ent_regex_in = ttk.Entry(top, width=32); self.ent_regex_in.pack(side="left")
        ttk.Button(top, text="Test", command=self.on_regex_test).pack(side="left", padx=6)

        self.lbl_regex_res = ttk.Label(wrapper, text="Resultado: -")
        self.lbl_regex_res.pack(anchor="w", pady=(10,0))

        helpbox = tk.Text(wrapper, height=9, wrap="word")
        helpbox.pack(fill="both", expand=True, pady=(8,0))
        helpbox.insert("1.0",
            "Instrucciones:\n"
            "1) Elige una regex.\n"
            "2) Escribe la cadena y presiona 'Test'.\n"
            "3) La coincidencia es completa (full match).\n")
        helpbox.config(state="disabled")

    def on_regex_test(self):
        try:
            pat = self.cmb_regex.get()
            s = self.ent_regex_in.get()
            self.lbl_regex_res.config(
                text="Resultado: MATCH ✅" if re.fullmatch(pat, s) else "Resultado: NO MATCH ❌",
                foreground="#08b000" if re.fullmatch(pat, s) else "#d61a1a"
            )
        except re.error as e:
            self.lbl_regex_res.config(text=f"Regex inválida: {e}", foreground="#d61a1a")

# --- Splash ---
class Splash(tk.Toplevel):
    def __init__(self, master, timeout_ms=1200):
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(bg="#0f172a")
        w,h = 560,220
        sw,sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        tk.Label(self, text=PROJECT_TITLE, fg="#e5e7eb", bg="#0f172a", font=("Segoe UI",14,"bold")).pack(pady=(36,6))
        tk.Label(self, text=PROJECT_SUBTITLE, fg="#a5b4fc", bg="#0f172a", font=("Segoe UI",10)).pack()

        bar_bg = tk.Frame(self, bg="#1f2937", height=10); bar_bg.pack(fill="x", padx=48, pady=(24,0))
        self.bar = tk.Frame(bar_bg, bg="#60a5fa", height=10, width=1); self.bar.pack(side="left")
        self.progress = 0
        self.max_progress = 100
        self.step_ms = max(16, timeout_ms // self.max_progress)
        self.after(self.step_ms, self._tick)

    def _tick(self):
        if self.progress >= self.max_progress:
            self.destroy(); return
        self.progress += 2
        total_w = self.winfo_width() - 96
        self.bar.config(width=max(1, int(total_w * self.progress / self.max_progress)))
        self.after(self.step_ms, self._tick)

# --- Main (con fix de instancia única) ---
def main():
    root = tk.Tk()
    root.withdraw()
    splash = Splash(root, timeout_ms=1200)
    app_started = {"v": False}

    def on_splash_destroy(e):
        if e.widget is splash and not app_started["v"]:
            app_started["v"] = True
            root.deiconify()
            TMSimulatorGUI(root)

    splash.bind("<Destroy>", on_splash_destroy)
    root.mainloop()

if __name__ == "__main__":
    main()
