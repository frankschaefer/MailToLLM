from __future__ import annotations

import queue
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from mailtollm.core.pipeline import run_pipeline


class MailToLLMApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("light")

        self.title("MailToLLM")
        self.geometry("980x680")
        self.minsize(920, 620)

        self.csv_path_var = ctk.StringVar()
        self.attachments_root_var = ctk.StringVar()
        self.output_dir_var = ctk.StringVar(value=str(Path("data/output").resolve()))
        self.summary_length_var = ctk.StringVar(value="1500")
        self.detail_logging_var = ctk.BooleanVar(value=False)

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._start_time: float | None = None
        self._total_records = 0
        self._processed_records = 0

        self._build_ui()
        self.after(200, self._poll_logs)

    def _build_ui(self) -> None:
        self.configure(fg_color="#f4f6fb")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="#1f2a44", corner_radius=14)
        header.grid(row=0, column=0, padx=20, pady=(20, 12), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="MailToLLM",
            text_color="#ffffff",
            font=("Helvetica", 24, "bold"),
        )
        title.grid(row=0, column=0, padx=16, pady=(14, 4), sticky="w")

        subtitle = ctk.CTkLabel(
            header,
            text="CSV Emails + Attachments in LLM-ready outputs",
            text_color="#d7deef",
            font=("Helvetica", 14),
        )
        subtitle.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="w")

        input_frame = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=14)
        input_frame.grid(row=1, column=0, padx=20, pady=(0, 16), sticky="ew")
        input_frame.grid_columnconfigure(1, weight=1)

        self._add_path_row(
            input_frame,
            row=0,
            label="CSV Folder",
            variable=self.csv_path_var,
            command=self._browse_csv_folder,
        )
        self._add_path_row(
            input_frame,
            row=1,
            label="Attachments Root",
            variable=self.attachments_root_var,
            command=self._browse_attachments,
        )
        self._add_path_row(
            input_frame,
            row=2,
            label="Output Directory",
            variable=self.output_dir_var,
            command=self._browse_output,
        )
        self._add_summary_row(input_frame, row=3)
        self._add_detail_logging_row(input_frame, row=4)

        actions = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=14)
        actions.grid(row=2, column=0, padx=20, pady=(0, 8), sticky="nsew")
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_rowconfigure(1, weight=1)

        buttons = ctk.CTkFrame(actions, fg_color="#ffffff")
        buttons.grid(row=0, column=0, padx=16, pady=16, sticky="ew")

        self.start_btn = ctk.CTkButton(
            buttons,
            text="Start",
            fg_color="#2f7d32",
            hover_color="#27662a",
            command=self._on_start,
            width=120,
        )
        self.start_btn.grid(row=0, column=0, padx=(0, 12))

        self.pause_btn = ctk.CTkButton(
            buttons,
            text="Pause",
            fg_color="#d49a1e",
            hover_color="#b98519",
            command=self._on_pause,
            width=120,
            state="disabled",
        )
        self.pause_btn.grid(row=0, column=1, padx=(0, 12))

        self.stop_btn = ctk.CTkButton(
            buttons,
            text="Stop",
            fg_color="#b71c1c",
            hover_color="#991616",
            command=self._on_stop,
            width=120,
            state="disabled",
        )
        self.stop_btn.grid(row=0, column=2)

        help_btn = ctk.CTkButton(
            buttons,
            text="Help",
            fg_color="#394a6d",
            hover_color="#2f3e5c",
            command=self._on_help,
            width=120,
        )
        help_btn.grid(row=0, column=3, padx=(12, 0))

        self.status = ctk.CTkTextbox(actions, height=320)
        self.status.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")

        footer = ctk.CTkFrame(self, fg_color="#e9edf5", corner_radius=12)
        footer.grid(row=3, column=0, padx=20, pady=(0, 16), sticky="ew")
        footer.grid_columnconfigure((1, 3, 5), weight=1)

        ctk.CTkLabel(footer, text="Start", text_color="#1f2a44").grid(
            row=0, column=0, padx=12, pady=8, sticky="w"
        )
        self.start_time_label = ctk.CTkLabel(footer, text="--", text_color="#1f2a44")
        self.start_time_label.grid(row=0, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(footer, text="Duration", text_color="#1f2a44").grid(
            row=0, column=2, padx=12, pady=8, sticky="w"
        )
        self.duration_label = ctk.CTkLabel(footer, text="00:00:00", text_color="#1f2a44")
        self.duration_label.grid(row=0, column=3, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(footer, text="ETA", text_color="#1f2a44").grid(
            row=0, column=4, padx=12, pady=8, sticky="w"
        )
        self.eta_label = ctk.CTkLabel(footer, text="--", text_color="#1f2a44")
        self.eta_label.grid(row=0, column=5, padx=12, pady=8, sticky="w")

    def _add_path_row(
        self,
        parent: ctk.CTkFrame,
        row: int,
        label: str,
        variable: ctk.StringVar,
        command,
    ) -> None:
        ctk.CTkLabel(parent, text=label, text_color="#1f2a44").grid(
            row=row, column=0, padx=16, pady=10, sticky="w"
        )
        ctk.CTkEntry(parent, textvariable=variable).grid(
            row=row, column=1, padx=16, pady=10, sticky="ew"
        )
        ctk.CTkButton(
            parent,
            text="Browse",
            fg_color="#394a6d",
            hover_color="#2f3e5c",
            width=110,
            command=command,
        ).grid(row=row, column=2, padx=16, pady=10)

    def _add_summary_row(self, parent: ctk.CTkFrame, row: int) -> None:
        ctk.CTkLabel(parent, text="Summary Length (chars)", text_color="#1f2a44").grid(
            row=row, column=0, padx=16, pady=10, sticky="w"
        )
        ctk.CTkEntry(parent, textvariable=self.summary_length_var).grid(
            row=row, column=1, padx=16, pady=10, sticky="ew"
        )
        ctk.CTkLabel(parent, text="Default: 1500", text_color="#5f6b85").grid(
            row=row, column=2, padx=16, pady=10, sticky="w"
        )

    def _add_detail_logging_row(self, parent: ctk.CTkFrame, row: int) -> None:
        ctk.CTkLabel(parent, text="Detail Logging", text_color="#1f2a44").grid(
            row=row, column=0, padx=16, pady=10, sticky="w"
        )
        ctk.CTkCheckBox(
            parent,
            text="Enable timing logs",
            variable=self.detail_logging_var,
        ).grid(row=row, column=1, padx=16, pady=10, sticky="w")

    def _browse_csv_folder(self) -> None:
        path = filedialog.askdirectory(title="Select CSV Folder")
        if path:
            self.csv_path_var.set(path)

    def _browse_attachments(self) -> None:
        path = filedialog.askdirectory(title="Select Attachments Root")
        if path:
            self.attachments_root_var.set(path)

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_dir_var.set(path)

    def _on_help(self) -> None:
        message = (
            "1) Select the folder that contains CSV files.\n"
            "2) Select the attachments root folder.\n"
            "3) Choose the output directory.\n"
            "4) Set the summary length (chars).\n"
            "5) Enable detail logging if needed.\n"
            "6) Start the pipeline. Use Pause/Stop as needed."
        )
        messagebox.showinfo("MailToLLM Help", message)

    def _on_start(self) -> None:
        if self._worker and self._worker.is_alive():
            return

        csv_path = Path(self.csv_path_var.get()).expanduser()
        attachments_root = Path(self.attachments_root_var.get()).expanduser()
        output_dir = Path(self.output_dir_var.get()).expanduser()
        summary_length = self._parse_summary_length()
        detail_logging = bool(self.detail_logging_var.get())
        if summary_length is None:
            return

        if not csv_path.exists() or not csv_path.is_dir():
            messagebox.showerror("Missing CSV folder", "Please select a valid CSV folder.")
            return
        if not attachments_root.exists():
            messagebox.showerror("Missing folder", "Please select a valid attachments folder.")
            return

        self._pause_event.clear()
        self._stop_event.clear()
        self._start_time = time.time()
        self._total_records = 0
        self._processed_records = 0
        self._update_timing()
        self._set_controls(running=True)
        self._enqueue_log("Starting pipeline...")

        self._worker = threading.Thread(
            target=self._run_pipeline,
            args=(csv_path, attachments_root, output_dir, summary_length, detail_logging),
            daemon=True,
        )
        self._worker.start()

    def _on_pause(self) -> None:
        if not self._worker or not self._worker.is_alive():
            return
        if self._pause_event.is_set():
            self._pause_event.clear()
            self.pause_btn.configure(text="Pause")
            self._enqueue_log("Resumed.")
        else:
            self._pause_event.set()
            self.pause_btn.configure(text="Resume")
            self._enqueue_log("Paused.")

    def _on_stop(self) -> None:
        if not self._worker or not self._worker.is_alive():
            return
        self._stop_event.set()
        self._pause_event.clear()
        self.pause_btn.configure(text="Pause")
        self._enqueue_log("Stop requested.")

    def _run_pipeline(
        self,
        csv_path: Path,
        attachments_root: Path,
        output_dir: Path,
        summary_length: int,
        detail_logging: bool,
    ) -> None:
        try:
            results = run_pipeline(
                csv_path,
                attachments_root,
                output_dir,
                summary_length=summary_length,
                pause_event=self._pause_event,
                stop_event=self._stop_event,
                on_log=self._enqueue_log,
                on_progress=self._on_progress,
                detail_logging=detail_logging,
            )
            self._enqueue_log(f"Finished. Outputs: {len(results)}")
        except Exception as exc:
            self._enqueue_log(f"Error: {exc}")
        finally:
            self.after(0, lambda: self._set_controls(running=False))

    def _set_controls(self, running: bool) -> None:
        self.start_btn.configure(state="disabled" if running else "normal")
        self.pause_btn.configure(state="normal" if running else "disabled")
        self.stop_btn.configure(state="normal" if running else "disabled")

    def _on_progress(self, processed: int, total: int) -> None:
        self._processed_records = processed
        self._total_records = total

    def _parse_summary_length(self) -> int | None:
        value = self.summary_length_var.get().strip()
        parsed = parse_summary_length(value)
        if parsed is None:
            messagebox.showerror("Invalid summary length", "Use a numeric value.")
        return parsed

    def _enqueue_log(self, message: str) -> None:
        self._log_queue.put(message)

    def _poll_logs(self) -> None:
        while not self._log_queue.empty():
            message = self._log_queue.get()
            self.status.insert("end", f"{message}\n")
            self.status.see("end")
        self.after(200, self._poll_logs)

    def _update_timing(self) -> None:
        if self._start_time is None:
            self.start_time_label.configure(text="--")
            self.duration_label.configure(text="00:00:00")
            self.eta_label.configure(text="--")
            return

        start_dt = datetime.fromtimestamp(self._start_time)
        self.start_time_label.configure(text=start_dt.strftime("%H:%M:%S"))

        elapsed = time.time() - self._start_time
        self.duration_label.configure(text=_format_duration(elapsed))

        eta = _estimate_eta(elapsed, self._processed_records, self._total_records)
        self.eta_label.configure(text=eta)

        if self._worker and self._worker.is_alive():
            self.after(1000, self._update_timing)


def parse_summary_length(value: str) -> int | None:
    cleaned = value.strip()
    if not cleaned:
        return 0
    if not cleaned.isdigit():
        return None
    return int(cleaned)


def _format_duration(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _estimate_eta(elapsed: float, processed: int, total: int) -> str:
    if total <= 0:
        return "--"
    if processed <= 0:
        return "calculating"
    remaining = total - processed
    if remaining <= 0:
        return "00:00:00"
    per_item = elapsed / processed
    eta_seconds = remaining * per_item
    return _format_duration(eta_seconds)


if __name__ == "__main__":
    app = MailToLLMApp()
    app.mainloop()
