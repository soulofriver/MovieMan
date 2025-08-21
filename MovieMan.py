import os
import json
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox
from io import BytesIO

import requests
from PIL import Image, ImageTk

# If you're on openai>=1.0:
#   pip install --upgrade openai
#   from openai import OpenAI
# Otherwise, fall back gracefully if import fails.
try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

# =========================
# 1) Config & Utilities
# =========================
CONFIG_FILE = "config.json"

def load_api_keys():
    keys = {"OPENAI_API_KEY": None, "OMDB_API_KEY": None}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                file_keys = json.load(f)
                keys.update({k: v for k, v in file_keys.items() if v})
        except Exception as e:
            print(f"Error reading {CONFIG_FILE}: {e}")
    env_openai = os.getenv("OPENAI_API_KEY")
    env_omdb   = os.getenv("OMDB_API_KEY")
    keys["OPENAI_API_KEY"] = env_openai or keys["OPENAI_API_KEY"]
    keys["OMDB_API_KEY"]   = env_omdb   or keys["OMDB_API_KEY"]
    return keys["OPENAI_API_KEY"], keys["OMDB_API_KEY"]


# =========================
# 2) main app
# =========================
class MovieManApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # ---- window basics
        self.title("🎬 MovieMan")
        self.geometry("520x700")
        self.configure(bg="#f0f0f0")
        self.resizable(True, True)

        # ---- state
        self.openai_api_key, self.omdb_api_key = load_api_keys()
        self.client = OpenAI(api_key=self.openai_api_key) if (OpenAI and self.openai_api_key) else None
        self.current_movie = None
        self.current_recommendation = None
        self.dark_mode = False
        self.poster_cache = {}  # title -> PIL ImageTk
        self.lock = threading.Lock()

        # ---- UI
        self.build_menu()
        self.build_title()
        self.build_chat_area()
        self.build_input_area()
        self.build_misc_widgets()

        # shortcuts
        self.bind("<s>", lambda e: self.smash())
        self.bind("<p>", lambda e: self.pass_movie())
        self.bind("<Escape>", lambda e: self.reset_session())

    # -----------------------
    # UI Builders
    # -----------------------
    def build_menu(self):
        menu_bar = tk.Menu(self)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Configure API", command=self.configure_api)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        session_menu = tk.Menu(menu_bar, tearoff=0)
        session_menu.add_command(label="Restart Session", command=self.reset_session)
        menu_bar.add_cascade(label="Session", menu=session_menu)

        self.config(menu=menu_bar)

    def build_title(self):
        self.title_label = tk.Label(
            self, text="🎬 MovieMan",
            font=("Helvetica", 18, "bold"),
            bg=self["bg"], fg="#333"
        )
        self.title_label.pack(pady=(10, 0))

    def build_chat_area(self):
        self.chat_frame = tk.Frame(self, bg=self["bg"])
        self.chat_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.chat_log = tk.Text(
            self.chat_frame, bg="white", fg="black", wrap=tk.WORD,
            state=tk.DISABLED, font=("Helvetica", 12), bd=0, padx=10, pady=10
        )
        self.chat_log.tag_config("bold", font=("Helvetica", 12, "bold"))
        self.chat_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(self.chat_frame, command=self.chat_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_log.config(yscrollcommand=self.chat_log.yview)

    def build_input_area(self):
        self.entry_frame = tk.Frame(self, bg=self["bg"])
        self.entry_frame.pack(padx=10, pady=(0, 10), fill=tk.X)

        self.entry = tk.Entry(
            self.entry_frame, bg="white", fg="black",
            font=("Helvetica", 12), bd=1, relief=tk.FLAT
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", lambda e: self.start_session())

        self.send_button = tk.Button(
            self.entry_frame, text="START", command=self.start_session,
            bg="#4CAF50", fg="white", font=("Helvetica", 12, "bold"),
            bd=0, activebackground="#45A049", padx=10, pady=6
        )
        self.send_button.pack(side=tk.RIGHT, padx=(10, 0))

    def build_misc_widgets(self):
        self.dark_mode_button = tk.Button(
            self, text="🌙 Dark Mode", command=self.toggle_dark_mode,
            bg=self["bg"], fg="#000000", font=("Helvetica", 10)
        )
        self.dark_mode_button.pack(pady=(0, 5))

        self.session_label = tk.Label(
            self, text="", font=("Helvetica", 14, "bold"),
            bg=self["bg"], fg="#000000"
        )
        self.session_label.pack(pady=(5, 0))

        self.loading_label = tk.Label(
            self, text="", font=("Helvetica", 12),
            bg=self["bg"], fg="gray"
        )
        self.loading_label.pack()

        # poster and plot area container
        self.info_frame = tk.Frame(self, bg=self["bg"])
        self.info_frame.pack(padx=10, pady=(4, 10), fill=tk.X)

        self.poster_label = tk.Label(
            self.info_frame, text="Poster will appear here",
            bg=self["bg"], fg="#666",
            font=("Helvetica", 10), wraplength=220, justify="center"
        )
        self.poster_label.pack(side=tk.LEFT, padx=(0, 10))

        # buttons row
        self.btn_row = tk.Frame(self, bg=self["bg"])
        self.btn_row.pack(pady=(0, 10), fill=tk.X)

        self.like_button = tk.Button(
            self.btn_row, text="👍 Smash", command=self.smash,
            bg="#2196F3", fg="white", font=("Helvetica", 12)
        )
        self.dislike_button = tk.Button(
            self.btn_row, text="👎 Pass it", command=self.pass_movie,
            bg="#f44336", fg="white", font=("Helvetica", 12)
        )
        # hidden until we have a recommendation
        self.like_button.pack_forget()
        self.dislike_button.pack_forget()

        # restart button (visible once a session exists)
        self.restart_button = tk.Button(
            self, text="↺ Restart Session", command=self.reset_session,
            bg="#9E9E9E", fg="white", font=("Helvetica", 10)
        )
        self.restart_button.pack(pady=(0, 8))
        self.restart_button.pack_forget()

    # -----------------------
    # App Logic
    # -----------------------
    def configure_api(self):
        new_openai = simpledialog.askstring(
            "Configure OpenAI API Key",
            "Enter your OpenAI API Key:",
            show="*"
        )
        if new_openai:
            self.openai_api_key = new_openai
            os.environ["OPENAI_API_KEY"] = new_openai
            if OpenAI:
                self.client = OpenAI(api_key=new_openai)

        new_omdb = simpledialog.askstring(
            "Configure OMDB API Key",
            "Enter your OMDB API Key (optional):"
        )
        if new_omdb is not None:
            self.omdb_api_key = new_omdb
            os.environ["OMDB_API_KEY"] = new_omdb

        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({
                    "OPENAI_API_KEY": self.openai_api_key,
                    "OMDB_API_KEY": self.omdb_api_key
                }, f, indent=4)
            messagebox.showinfo("Success", "API keys saved to config.json")
        except Exception as e:
            messagebox.showwarning("Warning", f"Could not save config.json:\n{e}")

    def start_session(self):
        m = self.entry.get().strip()
        if not m:
            return
        self.entry.delete(0, tk.END)
        self.entry.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)

        self.current_movie = m
        self.session_label.config(text=f"Your movie: {m}")
        self.restart_button.pack(pady=(0, 8))  # show restart option
        self.show_recommendation()

    def show_recommendation(self):
        if not self.client:
            messagebox.showerror(
                "Missing API Key",
                "OpenAI API Key not set.\nUse File → Configure API to set it."
            )
            self._enable_input()
            return

        self._append_chat(f"Based on “{self.current_movie}”, MovieMan recommends:\n", tag="bold")
        self.loading_label.config(text="🎬 Thinking…")
        self.update_idletasks()

        # run heavy work in background
        t = threading.Thread(target=self._fetch_and_display_recommendation, daemon=True)
        t.start()

    def _fetch_and_display_recommendation(self):
        try:
            rec = self._ask_openai(f"Recommend one movie title (only the title) similar to “{self.current_movie}”.")
        except Exception as e:
            self.after(0, lambda: self._on_error(f"OpenAI Error: {e}"))
            return

        with self.lock:
            self.current_recommendation = rec

        # fetch OMDB in same worker thread
        poster_imgtk, plot = self._get_poster_and_plot(rec)

        # update UI on main thread
        self.after(0, lambda: self._update_recommendation_ui(rec, poster_imgtk, plot))

    def _ask_openai(self, prompt: str) -> str:
        # You can change model to a smaller/cheaper one if desired, e.g., "gpt-4o-mini"
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are MovieMan, a movie recommendation assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=40,
            temperature=0.7,
        )
        text = resp.choices[0].message.content.strip()
        # keep it to a single line (title only) if possible
        return text.split("\n")[0].strip(' "')

    def _get_poster_and_plot(self, title):
        # cache poster image by title to avoid re-downloading
        poster_imgtk = None
        plot = None

        if not self.omdb_api_key:
            return None, None

        url = f"http://www.omdbapi.com/?t={requests.utils.quote(title)}&apikey={self.omdb_api_key}"
        try:
            r = requests.get(url, timeout=8)
            data = r.json()
            if data.get("Response") == "True":
                poster_url = data.get("Poster")
                plot = data.get("Plot")
                if poster_url and poster_url.lower() != "n/a":
                    if title in self.poster_cache:
                        poster_imgtk = self.poster_cache[title]
                    else:
                        img_data = requests.get(poster_url, timeout=8).content
                        img = Image.open(BytesIO(img_data))
                        img.thumbnail((220, 320))
                        poster_imgtk = ImageTk.PhotoImage(img)
                        self.poster_cache[title] = poster_imgtk
        except Exception:
            pass

        return poster_imgtk, plot

    def _update_recommendation_ui(self, rec, poster_imgtk, plot):
        self._append_chat(f"{rec}\n\n")

        if poster_imgtk:
            self.poster_label.config(image=poster_imgtk, text="")
            self.poster_label.image = poster_imgtk
        else:
            self.poster_label.config(image="", text="Poster not available")

        if plot:
            self._append_chat(f"Plot: {plot}\n\n")
        else:
            self._append_chat("Plot not available.\n\n")

        self.loading_label.config(text="")
        self.like_button.pack(side=tk.LEFT, padx=20, pady=(0, 10), in_=self.btn_row)
        self.dislike_button.pack(side=tk.RIGHT, padx=20, pady=(0, 10), in_=self.btn_row)

    def smash(self):
        # user liked the rec -> continue with recommendation loop
        self.like_button.pack_forget()
        self.dislike_button.pack_forget()
        if self.current_recommendation:
            self.current_movie = self.current_recommendation
            self.session_label.config(text=f"Your movie: {self.current_movie}")
            self.show_recommendation()

    def pass_movie(self):
        # Instead of quitting, offer to start over
        answer = messagebox.askyesno("Session Ended", "You passed. Start a new session?")
        if answer:
            self.reset_session()
        else:
            # keep app open
            self._enable_input()

    def reset_session(self):
        # clear UI/state for a fresh start
        self.current_movie = None
        self.current_recommendation = None
        self.poster_label.config(image="", text="Poster will appear here")
        self.poster_label.image = None
        self.chat_log.config(state=tk.NORMAL)
        self.chat_log.delete("1.0", tk.END)
        self.chat_log.config(state=tk.DISABLED)
        self.session_label.config(text="")
        self.like_button.pack_forget()
        self.dislike_button.pack_forget()
        self.loading_label.config(text="")
        self._enable_input()
        self.entry.focus_set()

    # -----------------------
    # Helpers
    # -----------------------
    def _append_chat(self, text, tag=None):
        self.chat_log.config(state=tk.NORMAL)
        if tag:
            self.chat_log.insert(tk.END, text, tag)
        else:
            self.chat_log.insert(tk.END, text)
        self.chat_log.config(state=tk.DISABLED)
        self.chat_log.yview(tk.END)

    def _on_error(self, msg):
        self.loading_label.config(text="")
        messagebox.showerror("Error", msg)
        self._enable_input()

    def _enable_input(self):
        self.entry.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            bg, fg = "#2e2e2e", "#f0f0f0"
            btn_bg, btn_fg = "#3c3c3c", "#f0f0f0"
            self.dark_mode_button.config(text="🌞 Light Mode")
        else:
            bg, fg = "#f0f0f0", "#000000"
            btn_bg, btn_fg = "#f0f0f0", "#000000"
            self.dark_mode_button.config(text="🌙 Dark Mode")

        # apply colors
        for w in (
            self, self.chat_frame, self.entry_frame, self.title_label,
            self.session_label, self.loading_label, self.info_frame,
            self.btn_row, self.restart_button
        ):
            try:
                w.config(bg=bg)
            except Exception:
                pass

        # text widgets
        self.chat_log.config(bg=btn_bg if isinstance(self.chat_log, tk.Text) else bg, fg=fg, insertbackground=fg)
        self.entry.config(bg=btn_bg, fg=fg, insertbackground=fg)
        self.poster_label.config(bg=bg, fg=fg if self.poster_label.cget("image") == "" else fg)

        # buttons
        self.send_button.config(bg="#4CAF50", fg="white")
        self.like_button.config(bg="#2196F3", fg="white")
        self.dislike_button.config(bg="#f44336", fg="white")
        self.dark_mode_button.config(bg=btn_bg, fg=btn_fg)


# =========================
# 3) run
# =========================
if __name__ == "__main__":
    app = MovieManApp()
    app.mainloop()
