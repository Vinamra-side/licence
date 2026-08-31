import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend_config import LICENCE_API_URL

APP_NAME = "Saiko Licence Control"
CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SaikoLicenceControl"
CONFIG_FILE = CONFIG_DIR / "session.json"


class ApiError(Exception):
    pass


def load_settings():
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(settings):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(settings), encoding="utf-8")


def clear_session():
    settings = load_settings()
    settings.pop("token", None)
    save_settings(settings)


class ApiClient:
    def __init__(self, base_url, token=""):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def request(self, method, path, payload=None):
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json", "User-Agent": "SaikoLicenceControl-Windows/1.0"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(f"{self.base_url}{path}", data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                message = json.loads(exc.read().decode("utf-8")).get("error")
            except (ValueError, AttributeError):
                message = None
            raise ApiError(message or f"Server returned error {exc.code}.") from exc
        except URLError as exc:
            raise ApiError("Cannot reach Saiko Inventory. Check the internet connection.") from exc
        except (TimeoutError, json.JSONDecodeError) as exc:
            raise ApiError("Saiko Inventory returned an invalid or delayed response.") from exc


class LicenceApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("760x620")
        self.root.minsize(680, 560)
        self.root.configure(bg="#f4eee9")
        self.settings = load_settings()
        self.client = None
        self._set_icon()
        self._configure_style()
        if self.settings.get("token"):
            self.show_control()
            self.refresh()
        else:
            self.show_login()

    def _set_icon(self):
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        icon = base / "assets" / "app-icon.ico"
        if icon.exists():
            try:
                self.root.iconbitmap(str(icon))
            except tk.TclError:
                pass

    def _configure_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4eee9")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f4eee9", foreground="#241820", font=("Segoe UI", 10))
        style.configure("Card.TLabel", background="#ffffff", foreground="#241820", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#ffffff", foreground="#241820", font=("Segoe UI Semibold", 24))
        style.configure("Metric.TLabel", background="#ffffff", foreground="#8b3d55", font=("Segoe UI Semibold", 20))
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(14, 9))
        style.configure("Primary.TButton", background="#8b3d55", foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#6f2f43")])
        style.configure("TEntry", padding=8)

    def clear(self):
        for child in self.root.winfo_children():
            child.destroy()

    def card(self):
        outer = ttk.Frame(self.root, padding=32)
        outer.pack(fill="both", expand=True)
        card = ttk.Frame(outer, style="Card.TFrame", padding=34)
        card.pack(fill="both", expand=True)
        return card

    def show_login(self):
        self.clear()
        card = self.card()
        ttk.Label(card, text="SAIKO · OWNER", style="Card.TLabel").pack(anchor="w")
        ttk.Label(card, text="Licence Control", style="Title.TLabel").pack(anchor="w", pady=(8, 4))
        ttk.Label(
            card,
            text="Sign in to the dedicated Windows licence application.",
            style="Card.TLabel",
        ).pack(anchor="w", pady=(0, 24))

        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(fill="x")
        ttk.Label(form, text="Owner login ID", style="Card.TLabel").pack(anchor="w")
        self.username_entry = ttk.Entry(form)
        self.username_entry.pack(fill="x", pady=(5, 15))
        ttk.Label(form, text="Password", style="Card.TLabel").pack(anchor="w")
        self.password_entry = ttk.Entry(form, show="●")
        self.password_entry.pack(fill="x", pady=(5, 22))
        self.password_entry.bind("<Return>", lambda _event: self.login())
        self.login_button = ttk.Button(form, text="Sign in", style="Primary.TButton", command=self.login)
        self.login_button.pack(anchor="e")
        self.login_status = ttk.Label(form, text="", style="Card.TLabel")
        self.login_status.pack(anchor="w", pady=(14, 0))
        self.username_entry.focus_set()

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showerror(APP_NAME, "Enter the owner login ID and password.")
            return
        self.login_button.state(["disabled"])
        self.login_status.configure(text="Signing in…")
        client = ApiClient(LICENCE_API_URL)

        def task():
            return client.request(
                "POST", "/api/login", {"username": username, "password": password}
            )

        def success(data):
            token = data.get("token")
            if not token:
                raise ApiError("The backend did not return a login session.")
            self.settings = {"token": token}
            save_settings(self.settings)
            self.password_entry.delete(0, "end")
            self.show_control()
            self.refresh()

        self.run_async(task, success, lambda: self.login_button.state(["!disabled"]))

    def show_control(self):
        self.clear()
        self.client = ApiClient(LICENCE_API_URL, self.settings["token"])
        card = self.card()
        header = ttk.Frame(card, style="Card.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Licence Control", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Sign out", command=self.logout).pack(side="right")

        self.state_text = tk.StringVar(value="Loading…")
        self.seats_text = tk.StringVar(value="—")
        ttk.Label(card, textvariable=self.state_text, style="Metric.TLabel").pack(anchor="w", pady=(28, 4))
        ttk.Label(card, textvariable=self.seats_text, style="Card.TLabel").pack(anchor="w", pady=(0, 24))

        self.active_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(card, text="Inventory application is active", variable=self.active_var).pack(anchor="w", pady=8)
        ttk.Label(card, text="Total active-user seats", style="Card.TLabel").pack(anchor="w", pady=(12, 4))
        self.max_users_var = tk.IntVar(value=5)
        ttk.Spinbox(card, from_=1, to=100000, textvariable=self.max_users_var, width=12).pack(anchor="w")
        ttk.Label(card, text="Message shown while paused", style="Card.TLabel").pack(anchor="w", pady=(16, 4))
        self.note_text = tk.Text(card, height=4, wrap="word", font=("Segoe UI", 10), relief="solid", borderwidth=1)
        self.note_text.pack(fill="x")

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.pack(fill="x", pady=(22, 0))
        self.refresh_button = ttk.Button(actions, text="Refresh", command=self.refresh)
        self.refresh_button.pack(side="left")
        self.save_button = ttk.Button(actions, text="Save licence", style="Primary.TButton", command=self.save)
        self.save_button.pack(side="right")
        self.action_status = ttk.Label(card, text="", style="Card.TLabel")
        self.action_status.pack(anchor="w", pady=(14, 0))

    def refresh(self):
        self.refresh_button.state(["disabled"])
        self.action_status.configure(text="Loading licence…")

        def success(data):
            self.render_license(data)
            self.action_status.configure(text="Licence is up to date.")

        self.run_async(
            lambda: self.client.request("GET", "/api/license"),
            success,
            lambda: self.refresh_button.state(["!disabled"]),
        )

    def render_license(self, data):
        seats = data["seats"]
        self.active_var.set(bool(data["is_active"]))
        self.max_users_var.set(int(data["max_users"]))
        self.note_text.delete("1.0", "end")
        self.note_text.insert("1.0", data.get("note", ""))
        self.state_text.set("Inventory active" if data["is_active"] else "Inventory paused")
        self.seats_text.set(
            f'{seats["active"]} / {seats["limit"]} seats used  ·  '
            f'{seats["accounts"]} login accounts  ·  {seats["subscribers"]} operational users'
        )

    def save(self):
        try:
            max_users = int(self.max_users_var.get())
        except (TypeError, ValueError, tk.TclError):
            messagebox.showerror(APP_NAME, "Seat limit must be a whole number.")
            return
        payload = {
            "is_active": bool(self.active_var.get()),
            "max_users": max_users,
            "note": self.note_text.get("1.0", "end").strip(),
        }
        self.save_button.state(["disabled"])
        self.action_status.configure(text="Saving…")

        def success(data):
            self.render_license(data["license"])
            self.action_status.configure(text="Licence settings saved immediately.")

        self.run_async(
            lambda: self.client.request("PUT", "/api/license", payload),
            success,
            lambda: self.save_button.state(["!disabled"]),
        )

    def run_async(self, task, success, finished):
        def worker():
            try:
                result = task()
            except ApiError as exc:
                self.root.after(0, lambda: self.show_error(str(exc)))
            except Exception:
                self.root.after(0, lambda: self.show_error("Unexpected application error."))
            else:
                self.root.after(0, lambda: success(result))
            finally:
                self.root.after(0, finished)

        threading.Thread(target=worker, daemon=True).start()

    def show_error(self, message):
        if "session" in message.lower() and "sign in" in message.lower():
            clear_session()
            self.settings = load_settings()
            self.show_login()
        messagebox.showerror(APP_NAME, message)

    def logout(self):
        clear_session()
        self.settings = load_settings()
        self.show_login()


def main():
    root = tk.Tk()
    LicenceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
