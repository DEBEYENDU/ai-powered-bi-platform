"""Main launcher window: controls, status panel, health panel, system stats."""

from __future__ import annotations

import contextlib
import subprocess
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox
from typing import Any

try:
    import customtkinter as ctk
except ImportError:  # pragma: no cover - GUI dependency
    ctk = None  # type: ignore

from launcher import checks
from launcher.config import SettingsManager
from launcher.health import HealthMonitor, StatusMonitor
from launcher.logs import LogStore
from launcher.paths import ProjectPaths
from launcher.processes import ProcessManager

DOT_COLORS = {
    "running": "#2ecc71",
    "starting": "#f1c40f",
    "stopped": "#e74c3c",
    "warning": "#f39c12",
}


class Sparkline(tk.Canvas):
    """Minimal rolling line graph (no extra dependencies)."""

    def __init__(self, master, width: int = 220, height: int = 48, color: str = "#0288d1") -> None:
        super().__init__(master, width=width, height=height, bg="#2b2b2b", highlightthickness=0)
        self._values: list[float] = []
        self._color = color
        self._width = width
        self._height = height

    def push(self, value: float) -> None:
        self._values.append(max(0.0, min(100.0, value)))
        if len(self._values) > 60:
            self._values.pop(0)
        self.delete("all")
        if len(self._values) < 2:
            return
        step = self._width / 59
        points: list[float] = []
        for i, sample in enumerate(self._values):
            x = i * step
            y = self._height - (sample / 100.0) * (self._height - 4) - 2
            points.extend([x, y])
        self.create_line(points, fill=self._color, width=2)


class LauncherApp:
    def __init__(self, root_path=None) -> None:
        if ctk is None:
            raise RuntimeError("customtkinter is not installed")
        self.paths = ProjectPaths(root_path)
        self.settings = SettingsManager(self.paths.config_file)
        self.logs = LogStore(self.paths.logs_dir)
        self.processes = ProcessManager(self.paths, self.logs)
        self.processes.on_change = lambda: self.root.after(0, self.refresh_status)
        self.health = HealthMonitor(int(self.settings.get("backend_port")), self.logs)
        self.health.on_update = lambda _snap: self.root.after(0, self._render_health)
        self.status_monitor = StatusMonitor(self.paths)
        self._starting = {"backend": False, "frontend": False}
        self._redis_started_by_us = False
        self._tray = None
        self._log_window = None
        self._cpu_history: Sparkline | None = None
        self._mem_history: Sparkline | None = None
        self._build()
        self.apply_theme()
        self.refresh_status()
        self._render_health()

    # -- construction --
    def _build(self) -> None:
        self.root = ctk.CTk()
        self.root.title("BI Platform Launcher")
        self.root.geometry("1060x700")
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        info = checks.git_info(self.paths.root)
        sidebar = ctk.CTkFrame(self.root, width=250)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        ctk.CTkLabel(sidebar, text="BI Platform", font=("Arial", 20, "bold")).pack(pady=(12, 0))
        ctk.CTkLabel(
            sidebar,
            text=f"v{info['version']} · {info['branch']}@{info['commit']}",
            font=("Arial", 11),
        ).pack(pady=(0, 10))

        buttons: list[tuple[str, Any]] = [
            ("▶  Start Project", self.start_project),
            ("■  Stop Project", self.stop_project),
            ("↻  Restart Project", self.restart_project),
            ("🌐  Open Frontend", self.open_frontend),
            ("📄  Open Swagger Docs", self.open_swagger),
            ("📊  Open Metrics", self.open_metrics),
            ("❤️  Health Check", self.manual_health_check),
            ("📝  View Logs", self.open_logs),
            ("⚙  Settings", self.open_settings),
        ]
        for text, command in buttons:
            ctk.CTkButton(sidebar, text=text, command=command, anchor="w").pack(
                fill="x", padx=10, pady=3
            )
        self.theme_switch = ctk.CTkSwitch(sidebar, text="Dark mode", command=self.toggle_theme)
        self.theme_switch.pack(padx=10, pady=8, anchor="w")
        if str(self.settings.get("theme")) == "dark":
            self.theme_switch.select()

        extra = ctk.CTkFrame(sidebar, fg_color="transparent")
        extra.pack(fill="x", padx=10, pady=4)
        ctk.CTkButton(extra, text="📁 Folder", width=110, command=self.open_folder).pack(
            side="left", padx=2
        )
        ctk.CTkButton(extra, text="💻 VS Code", width=110, command=self.open_vscode).pack(
            side="left", padx=2
        )

        main = ctk.CTkFrame(self.root)
        main.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        main.grid_columnconfigure((0, 1), weight=1)

        status_box = ctk.CTkFrame(main)
        status_box.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        ctk.CTkLabel(status_box, text="Status", font=("Arial", 15, "bold")).pack(
            anchor="w", padx=8, pady=4
        )
        self.status_rows: dict[str, Any] = {}
        for name in (
            "Backend",
            "Frontend",
            "Database",
            "Redis",
            "Storage",
            "Health",
            "Maintenance",
            "CPU",
            "Memory",
            "Disk",
        ):
            row = ctk.CTkFrame(status_box, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=1)
            dot = ctk.CTkLabel(row, text="●", font=("Arial", 16), width=24)
            dot.pack(side="left")
            ctk.CTkLabel(row, text=name, width=110, anchor="w").pack(side="left")
            detail = ctk.CTkLabel(row, text="—", anchor="w")
            detail.pack(side="left", fill="x", expand=True)
            self.status_rows[name] = (dot, detail)

        right = ctk.CTkFrame(main)
        right.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        ctk.CTkLabel(right, text="System", font=("Arial", 15, "bold")).pack(
            anchor="w", padx=8, pady=4
        )
        self.cpu_bar = ctk.CTkProgressBar(right)
        self.cpu_bar.pack(fill="x", padx=8, pady=2)
        self.cpu_graph = Sparkline(right)
        self.cpu_graph.pack(padx=8, pady=2)
        self.mem_bar = ctk.CTkProgressBar(right)
        self.mem_bar.pack(fill="x", padx=8, pady=2)
        self.mem_graph = Sparkline(right, color="#2ecc71")
        self.mem_graph.pack(padx=8, pady=2)
        ctk.CTkLabel(right, text="Uptime", font=("Arial", 15, "bold")).pack(
            anchor="w", padx=8, pady=4
        )
        self.uptime_label = ctk.CTkLabel(right, text="backend: —   frontend: —", anchor="w")
        self.uptime_label.pack(anchor="w", padx=8)

        health_box = ctk.CTkFrame(main)
        health_box.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 8))
        ctk.CTkLabel(health_box, text="Health", font=("Arial", 15, "bold")).pack(
            anchor="w", padx=8, pady=4
        )
        self.health_text = ctk.CTkTextbox(health_box, height=130, font=("Consolas", 12))
        self.health_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.health_text.configure(state="disabled")

        self.status_label = ctk.CTkLabel(main, text="Ready.", anchor="w")
        self.status_label.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- helpers --
    def apply_theme(self) -> None:
        mode = str(self.settings.get("theme"))
        ctk.set_appearance_mode(mode)
        ctk.set_default_color_theme("blue")

    def toggle_theme(self) -> None:
        new = "light" if str(self.settings.get("theme")) == "dark" else "dark"
        self.settings.set("theme", new)
        self.settings.save()
        self.apply_theme()

    def say(self, message: str) -> None:
        self.status_label.configure(text=message)
        self.logs.append("launcher", message)

    def _set_dot(self, name: str, status: str, detail: str = "") -> None:
        dot, label = self.status_rows[name]
        dot.configure(text_color=DOT_COLORS.get(status, "#95a5a6"))
        label.configure(text=f"{status}  {detail}".strip())

    # -- start/stop --
    def start_project(self) -> None:
        if self.processes.backend.running and self.processes.frontend.running:
            messagebox.showinfo("Launcher", "Project is already running.")
            return
        threading.Thread(target=self._start_sequence, daemon=True).start()

    def _start_sequence(self) -> None:
        def step(message: str) -> None:
            self.root.after(0, lambda: self.say(message))

        backend_port = int(self.settings.get("backend_port"))
        frontend_port = int(self.settings.get("frontend_port"))
        try:
            step("Checking dependencies...")
            py = checks.check_python()
            node, npm = checks.check_node(), checks.check_npm()
            if not node.ok or not npm.ok:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Launcher", "Node.js/npm is required for the frontend.\n" + node.message
                    ),
                )
                step("Startup aborted: Node.js missing.")
                return
            self.logs.append("launcher", f"{py.message}; {node.message}; {npm.message}")
            pg = checks.check_postgres()
            if not pg.ok:
                self.root.after(
                    0, lambda: messagebox.showwarning("Launcher", pg.message + "\n" + pg.detail)
                )
            redis = checks.check_redis()
            if not redis.ok and bool(self.settings.get("manage_redis_container")):
                step("Redis is not running — starting container...")
                result = checks.ensure_redis_container(str(self.settings.get("redis_container")))
                self.logs.append("redis", result.message + " " + result.detail)
                self._redis_started_by_us = self._redis_started_by_us or result.ok
                if not result.ok:
                    self.root.after(0, lambda: messagebox.showwarning("Launcher", result.message))
            dotenv = checks.check_dotenv(self.paths)
            if not dotenv.ok:
                self.root.after(0, lambda m=dotenv.message: messagebox.showerror("Launcher", m))
                step("Startup aborted: no .env available.")
                return
            for _, raw in (
                ("storage", str(self.settings.get("storage_path") or "")),
                ("reports", str(self.settings.get("reports_path") or "")),
            ):
                if raw:
                    from pathlib import Path as _Path

                    result = checks.ensure_dir(_Path(raw))
                    if not result.ok:
                        self.root.after(
                            0, lambda m=result.message: messagebox.showerror("Launcher", m)
                        )
                        step("Startup aborted: storage folder issue.")
                        return
            step("Installing frontend packages if needed...")
            if not self.processes.ensure_frontend_deps():
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Launcher", "Frontend failed to install (npm install)."
                    ),
                )
                step("Startup aborted: npm install failed.")
                return
            self._starting["backend"] = True
            self.root.after(0, self.refresh_status)
            step("Starting backend...")
            env_extra = {
                "DATABASE_URL": str(self.settings.get("database_url")),
                "REDIS_URL": str(self.settings.get("redis_url")),
            }
            self.processes.start_backend(backend_port, env_extra=env_extra)
            if not self.processes.wait_ready(
                f"http://127.0.0.1:{backend_port}/health", timeout=120.0, label="backend"
            ):
                self._starting["backend"] = False
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Launcher", "Backend failed to start. See Backend logs."
                    ),
                )
                step("Startup aborted: backend failed to start.")
                return
            self._starting["backend"] = False
            self._starting["frontend"] = True
            self.root.after(0, self.refresh_status)
            step("Starting frontend...")
            self.processes.start_frontend(frontend_port)
            if not self.processes.wait_ready(
                f"http://127.0.0.1:{frontend_port}/", timeout=180.0, label="frontend"
            ):
                self._starting["frontend"] = False
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Launcher", "Frontend failed to compile. See Frontend logs."
                    ),
                )
                step("Startup aborted: frontend failed to start.")
                return
            self._starting["frontend"] = False
            self.health.backend_port = backend_port
            self.health.start()
            step("Project running.")
            self.root.after(0, self.refresh_status)
            if bool(self.settings.get("auto_start_browser")):
                webbrowser.open(f"http://localhost:{frontend_port}")
        except Exception as exc:
            self._starting = {"backend": False, "frontend": False}
            self.root.after(
                0, lambda exc=exc: messagebox.showerror("Launcher", f"Startup failed: {exc}")
            )
            step(f"Startup failed: {exc}")

    def stop_project(self) -> None:
        self.health.stop()
        self.processes.stop_all()
        if self._redis_started_by_us:
            try:
                subprocess.run(
                    ["docker", "stop", str(self.settings.get("redis_container"))],
                    capture_output=True,
                    timeout=60,
                    check=False,
                )
                self.logs.append("redis", "Redis container stopped.")
            except Exception as exc:
                self.logs.append("redis", f"Could not stop Redis container: {exc}")
            self._redis_started_by_us = False
        self.processes.kill_orphans()
        self.say("Project stopped.")
        self.refresh_status()

    def restart_project(self) -> None:
        self.stop_project()
        time.sleep(2.0)
        self.start_project()

    # -- openers --
    def _url(self, path: str) -> str:
        return f"http://localhost:{int(self.settings.get('frontend_port'))}{path}"

    def _api(self, path: str) -> str:
        return f"http://127.0.0.1:{int(self.settings.get('backend_port'))}{path}"

    def open_frontend(self) -> None:
        webbrowser.open(f"http://localhost:{int(self.settings.get('frontend_port'))}")

    def open_swagger(self) -> None:
        webbrowser.open(self._api("/docs"))

    def open_metrics(self) -> None:
        webbrowser.open(self._api("/api/v1/admin/metrics/prometheus"))

    def open_folder(self) -> None:
        try:
            import os

            if os.name == "nt":
                os.startfile(str(self.paths.root))  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", str(self.paths.root)], check=False)
        except Exception as exc:
            messagebox.showerror("Launcher", f"Cannot open folder: {exc}")

    def open_vscode(self) -> None:
        try:
            subprocess.Popen(["code", str(self.paths.root)])
        except Exception:
            messagebox.showwarning("Launcher", "VS Code CLI ('code') was not found on PATH.")

    # -- panels --
    def manual_health_check(self) -> None:
        self.say("Running health check...")
        threading.Thread(target=self._manual_poll, daemon=True).start()

    def _manual_poll(self) -> None:
        try:
            snapshot = self.health.poll_once()
            self.root.after(0, self._render_health)
            self.root.after(0, lambda: self.say(f"Health: {snapshot.get('overall', '?')}"))
        except Exception as exc:
            self.root.after(
                0,
                lambda exc=exc: messagebox.showerror("Launcher", f"Health check failed: {exc}"),
            )

    def refresh_status(self) -> None:
        with contextlib.suppress(Exception):
            items = self.status_monitor.collect(
                self.processes.backend.running,
                self.processes.frontend.running,
                self._starting["backend"],
                self._starting["frontend"],
                self.health.snapshot or None,
            )
            for item in items:
                if item.name in self.status_rows:
                    self._set_dot(item.name, item.status, item.detail)
            stats = StatusMonitor.system_stats()
            self._set_dot("CPU", "running", f"{stats['cpu']:.0f}%")
            self._set_dot("Memory", "running", f"{stats['memory']:.0f}%")
            self._set_dot("Disk", "running", f"{stats['disk']:.0f}%")
            self.cpu_bar.set(stats["cpu"] / 100.0)
            self.mem_bar.set(stats["memory"] / 100.0)
            self.cpu_graph.push(stats["cpu"])
            self.mem_graph.push(stats["memory"])
            backend_up = self._fmt_uptime(self.processes.backend.uptime_seconds)
            frontend_up = self._fmt_uptime(self.processes.frontend.uptime_seconds)
            self.uptime_label.configure(text=f"backend: {backend_up}   frontend: {frontend_up}")
        with contextlib.suppress(Exception):
            self.root.after(2000, self.refresh_status)

    @staticmethod
    def _fmt_uptime(seconds: float) -> str:
        if seconds <= 0:
            return "—"
        minutes, sec = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours}h {minutes}m" if hours else f"{minutes}m {sec}s"

    def _render_health(self) -> None:
        snapshot = self.health.snapshot
        box = self.health_text
        box.configure(state="normal")
        box.delete("1.0", "end")
        if not snapshot:
            box.insert("end", "Backend unreachable — start the project to see health.")
        else:
            lines = [
                f"overall={snapshot.get('overall')}  maintenance={snapshot.get('maintenance')}  "
                f"response={snapshot.get('response_ms')}ms",
                "",
            ]
            for service in snapshot.get("services", []):
                lines.append(
                    f"[{service.get('status', '?').upper():8s}] {service.get('service', '?'):12s} "
                    f"{service.get('latency_ms', '?')}ms  {service.get('detail', '')}"
                )
            box.insert("end", "\n".join(lines))
        box.configure(state="disabled")

    # -- windows --
    def open_logs(self) -> None:
        try:
            from launcher.ui_logs import LogViewer

            if self._log_window is None:
                self._log_window = LogViewer(self.root, self.logs)
            else:
                try:
                    self._log_window.window.lift()
                    self._log_window.window.focus()
                except Exception:
                    self._log_window = LogViewer(self.root, self.logs)
        except Exception as exc:
            messagebox.showerror("Launcher", f"Cannot open log viewer: {exc}")

    def open_settings(self) -> None:
        try:
            from launcher.ui_settings import SettingsDialog

            old_backend = int(self.settings.get("backend_port"))

            def saved() -> None:
                new_backend = int(self.settings.get("backend_port"))
                if new_backend != old_backend:
                    self.health.backend_port = new_backend
                self.apply_theme()
                self.say("Settings saved.")

            SettingsDialog(self.root, self.settings, on_saved=saved)
        except Exception as exc:
            messagebox.showerror("Launcher", f"Cannot open settings: {exc}")

    # -- tray / lifecycle --
    def _on_close(self) -> None:
        if self._tray is not None:
            self.root.withdraw()
            self.say("Minimized to system tray.")
        else:
            self.quit_app()

    def enable_tray(self) -> None:
        try:
            from launcher.tray import create_tray_icon

            icon = create_tray_icon(
                on_show=self._tray_show,
                on_start=self.start_project,
                on_stop=self.stop_project,
                on_quit=self.quit_app,
            )
            if icon is None:
                return
            self._tray = icon
            threading.Thread(target=icon.run, daemon=True).start()
            self.logs.append("launcher", "System tray icon enabled.")
        except Exception as exc:
            self.logs.append("launcher", f"Tray unavailable: {exc}")

    def _tray_show(self) -> None:
        with contextlib.suppress(Exception):
            self.root.after(0, self._show_window)

    def _show_window(self) -> None:
        with contextlib.suppress(Exception):
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

    def quit_app(self) -> None:
        with contextlib.suppress(Exception):
            if self._tray is not None:
                self._tray.stop()
        with contextlib.suppress(Exception):
            self.health.stop()
        with contextlib.suppress(Exception):
            self.processes.stop_all()
        with contextlib.suppress(Exception):
            self.root.destroy()

    def run(self) -> None:
        self.enable_tray()
        self.root.mainloop()


def show_splash(root) -> Any:
    splash = ctk.CTkToplevel(root)
    splash.title("BI Platform Launcher")
    splash.geometry("420x180")
    splash.transient(root)
    with contextlib.suppress(Exception):
        splash.overrideredirect(True)
        x = (splash.winfo_screenwidth() - 420) // 2
        y = (splash.winfo_screenheight() - 180) // 2
        splash.geometry(f"+{x}+{y}")
    ctk.CTkLabel(splash, text="BI Platform Launcher", font=("Arial", 22, "bold")).pack(pady=(36, 4))
    status = ctk.CTkLabel(splash, text="Initializing...")
    status.pack(pady=4)
    bar = ctk.CTkProgressBar(splash, mode="indeterminate")
    bar.pack(padx=40, pady=12, fill="x")
    bar.start()
    splash.update()
    return splash, status
