from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from mailtollm.core.pipeline import run_pipeline


class MailToLLMApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MailToLLM")
        self.geometry("900x600")

        self.csv_path_var = ctk.StringVar()
        self.attachments_root_var = ctk.StringVar()
        self.output_dir_var = ctk.StringVar(value=str(Path("data/output").resolve()))

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="CSV Path").grid(row=0, column=0, padx=12, pady=12, sticky="w")
        ctk.CTkEntry(self, textvariable=self.csv_path_var).grid(
            row=0, column=1, padx=12, pady=12, sticky="ew"
        )

        ctk.CTkLabel(self, text="Attachments Root").grid(
            row=1, column=0, padx=12, pady=12, sticky="w"
        )
        ctk.CTkEntry(self, textvariable=self.attachments_root_var).grid(
            row=1, column=1, padx=12, pady=12, sticky="ew"
        )

        ctk.CTkLabel(self, text="Output Dir").grid(row=2, column=0, padx=12, pady=12, sticky="w")
        ctk.CTkEntry(self, textvariable=self.output_dir_var).grid(
            row=2, column=1, padx=12, pady=12, sticky="ew"
        )

        ctk.CTkButton(self, text="Run", command=self._on_run).grid(
            row=3, column=1, padx=12, pady=18, sticky="e"
        )

        self.status = ctk.CTkTextbox(self, height=320)
        self.status.grid(row=4, column=0, columnspan=2, padx=12, pady=12, sticky="nsew")

        self.grid_rowconfigure(4, weight=1)

    def _on_run(self) -> None:
        csv_path = Path(self.csv_path_var.get()).expanduser()
        attachments_root = Path(self.attachments_root_var.get()).expanduser()
        output_dir = Path(self.output_dir_var.get()).expanduser()

        self.status.insert("end", f"Running pipeline for {csv_path}\n")
        outputs = run_pipeline(csv_path, attachments_root, output_dir)
        self.status.insert("end", f"Finished. Outputs: {len(outputs)}\n")


if __name__ == "__main__":
    app = MailToLLMApp()
    app.mainloop()
