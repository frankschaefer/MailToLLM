from __future__ import annotations

import queue
import threading
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

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None

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
            label="CSV File",
            variable=self.csv_path_var,
            command=self._browse_csv,
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

        actions = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=14)
        actions.grid(row=2, column=0, padx=20, pady=(0, 16), sticky="nsew")
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

    def _browse_csv(self) -> None:
        path = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV", "*.csv")])
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
            "1) Select the CSV file with email data.\n"
            "2) Select the attachments root folder.\n"
            "3) Choose the output directory.\n"
            "4) Set the summary length (chars).\n"
            "5) Start the pipeline. Use Pause/Stop as needed."
        )
        messagebox.showinfo("MailToLLM Help", message)

    def _on_start(self) -> None:
        if self._worker and self._worker.is_alive():
            return

        csv_path = Path(self.csv_path_var.get()).expanduser()
        attachments_root = Path(self.attachments_root_var.get()).expanduser()
        output_dir = Path(self.output_dir_var.get()).expanduser()
        summary_length = self._parse_summary_length()
        if summary_length is None:
            return

        if not csv_path.exists():
            messagebox.showerror("Missing CSV", "Please select a valid CSV file.")
            return
        if not attachments_root.exists():
            messagebox.showerror("Missing folder", "Please select a valid attachments folder.")
            return

        self._pause_event.clear()
        self._stop_event.clear()
        self._set_controls(running=True)
        self._enqueue_log("Starting pipeline...")

        self._worker = threading.Thread(
            target=self._run_pipeline,
            args=(csv_path, attachments_root, output_dir, summary_length),
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

    def _parse_summary_length(self) -> int | None:
        value = self.summary_length_var.get().strip()
        if not value:
            return 0
        if not value.isdigit():
            messagebox.showerror(\"Invalid summary length\", \"Use a numeric value.\")
            return None
        return int(value)

    def _enqueue_log(self, message: str) -> None:
        self._log_queue.put(message)

    def _poll_logs(self) -> None:
        while not self._log_queue.empty():
            message = self._log_queue.get()
            self.status.insert("end", f"{message}\n")
            self.status.see("end")
        self.after(200, self._poll_logs)


if __name__ == "__main__":
    app = MailToLLMApp()
    app.mainloop()
