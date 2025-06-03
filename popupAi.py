# chat_assistant.py (Improved UI and UX for Quick Assistant)

import tkinter as tk
from tkinter import ttk, scrolledtext
from pynput import keyboard as pynput_keyboard
import threading
import sys
import json
from datetime import datetime
from testing import authenticate_google, get_task_plan, execute_task_plan, convert_composite

class QuickAssistantPopup:
    def __init__(self):
        self.root = None
        self.is_visible = False
        self.creds = None

        self.listener = pynput_keyboard.GlobalHotKeys({
            '<cmd>+j': lambda: self.root.after(0, self.toggle_popup) if self.root else print("Popup not initialized yet.")
        })
        self.listener.start()

        print("\U0001F680 Quick Assistant loaded! Press Command+J to open.")

    def toggle_popup(self):
        if self.is_visible:
            self.hide_popup()
        else:
            self.show_popup()

    def show_popup(self):
        if self.root is None:
            self.create_popup()
        else:
            self.root.deiconify()

        self.center_window()
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.focus_force()
        self.input_text.focus_set()
        self.root.after(500, lambda: self.root.attributes('-topmost', False))
        self.is_visible = True

    def hide_popup(self):
        if self.root:
            self.root.withdraw()
        self.is_visible = False

    def create_popup(self):
        self.root = tk.Tk()
        self.root.title("Jarvis AI Assistant")
        self.root.geometry("520x480")
        self.root.configure(bg='#1e1e1e')

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Dark.TFrame', background='#1e1e1e')
        style.configure('Dark.TLabel', background='#1e1e1e', foreground='#d4d4d4', font=('Segoe UI', 10))
        style.configure('Dark.TButton', background='#007acc', foreground='white')

        main_frame = ttk.Frame(self.root, style='Dark.TFrame', padding="12")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Jarvis Assistant", style='Dark.TLabel', font=('Segoe UI', 14, 'bold')).pack(anchor=tk.W)
        ttk.Label(main_frame, text="Ask anything, or choose a shortcut.", style='Dark.TLabel').pack(anchor=tk.W, pady=(0, 10))

        self.input_text = scrolledtext.ScrolledText(main_frame, height=5, font=('Segoe UI', 10), bg='#1e1e1e', fg='#d4d4d4', insertbackground='white', wrap=tk.WORD, borderwidth=1, relief=tk.SOLID)
        self.input_text.pack(fill=tk.X, padx=2, pady=(0, 10))

        quick_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        quick_frame.pack(fill=tk.X, pady=(0, 10))

        shortcuts = [
            ("\U0001F4DD Doc", "Create a document about "),
            ("\U0001F4CA Sheet", "Create a spreadsheet for "),
            ("\U0001F4C5 Event", "Add calendar event: "),
            ("\U0001F4E7 Email", "Check my recent emails")
        ]

        for i, (label, prompt) in enumerate(shortcuts):
            ttk.Button(quick_frame, text=label, style='Dark.TButton', command=lambda p=prompt: self.fill_and_run(p)).grid(row=i//2, column=i%2, padx=5, pady=3, sticky='ew')

        quick_frame.columnconfigure(0, weight=1)
        quick_frame.columnconfigure(1, weight=1)

        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, style='Dark.TLabel', font=('Segoe UI', 9))
        status_label.pack(anchor=tk.W, pady=(10, 0))

        self.root.bind('<Return>', self.on_enter)
        self.root.bind('<Escape>', lambda e: self.hide_popup())

        self.init_credentials()

    def center_window(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")

    def fill_and_run(self, text):
        self.input_text.delete(1.0, tk.END)
        self.input_text.insert(1.0, text)
        self.execute_task()

    def on_enter(self, event):
        if not event.state:  # Ensure shift/ctrl not pressed
            self.execute_task()

    def init_credentials(self):
        def auth():
            try:
                self.root.after(0, lambda: self.status_var.set("Authenticating..."))
                self.creds = authenticate_google()
                self.root.after(0, lambda: self.status_var.set("✅ Google authenticated."))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"❌ Auth error: {e}"))

        threading.Thread(target=auth, daemon=True).start()

    def execute_task(self):
        user_input = self.input_text.get(1.0, tk.END).strip()
        if not user_input:
            self.status_var.set("Enter a request to continue")
            return

        def run():
            try:
                self.root.after(0, lambda: self.status_var.set("Thinking..."))
                plan = get_task_plan(user_input)
                plan_dict = convert_composite(plan)
                execute_task_plan(plan_dict, self.creds)
                self.root.after(0, lambda: self.status_var.set("✅ Done!"))
                self.root.after(2500, self.hide_popup)
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"❌ Error: {e}"))

        threading.Thread(target=run, daemon=True).start()

    def run(self):
        self.create_popup()
        self.root.mainloop()

if __name__ == "__main__":
    app = QuickAssistantPopup()
    app.run()
