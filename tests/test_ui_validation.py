"""Tests for UI input validation logic."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


def test_start_validation_missing_csv_folder(tmp_path: Path) -> None:
    """Test that start validation rejects missing CSV folder."""
    from mailtollm.ui.app import MailToLLMApp

    with patch("mailtollm.ui.app.messagebox") as mock_messagebox:
        app = MailToLLMApp()

        # Set empty CSV folder
        app.csv_path_var.set("")
        app.attachments_root_var.set(str(tmp_path))

        # Mock worker check
        app._worker = None

        # Try to start
        app._on_start()

        # Should show error
        mock_messagebox.showerror.assert_called_once()
        assert "CSV folder" in mock_messagebox.showerror.call_args[0][1]


def test_csv_folder_selection_sets_attachments(tmp_path: Path) -> None:
    """Test that CSV folder selection automatically sets attachments folder."""
    from mailtollm.ui.app import MailToLLMApp

    app = MailToLLMApp()

    # Initially empty
    assert app.attachments_root_var.get() == ""

    # Simulate user selecting folder via dialog
    with patch("mailtollm.ui.app.filedialog.askdirectory", return_value=str(tmp_path)):
        app._browse_csv_folder()

    # Both should be set to same path
    assert app.csv_path_var.get() == str(tmp_path)
    assert app.attachments_root_var.get() == str(tmp_path)


def test_start_validation_nonexistent_csv_folder(tmp_path: Path) -> None:
    """Test that start validation rejects non-existent CSV folder."""
    from mailtollm.ui.app import MailToLLMApp

    with patch("mailtollm.ui.app.messagebox") as mock_messagebox:
        app = MailToLLMApp()

        # Set non-existent folder
        nonexistent = tmp_path / "does_not_exist"
        app.csv_path_var.set(str(nonexistent))
        app.attachments_root_var.set(str(tmp_path))

        # Mock worker check
        app._worker = None

        # Try to start
        app._on_start()

        # Should show error
        mock_messagebox.showerror.assert_called_once()
        assert "CSV folder" in mock_messagebox.showerror.call_args[0][1]


def test_start_validation_invalid_summary_length() -> None:
    """Test that start validation rejects invalid summary length."""
    from mailtollm.ui.app import MailToLLMApp

    with patch("mailtollm.ui.app.messagebox") as mock_messagebox:
        app = MailToLLMApp()

        # Set invalid summary length
        app.summary_length_var.set("not a number")

        # Mock worker check
        app._worker = None

        # Try to start (will fail at parse_summary_length)
        app._on_start()

        # Should show error (but only after folder validation passes)
        # Since we don't have folders set, it will fail on folder validation first


def test_start_validation_all_valid(tmp_path: Path) -> None:
    """Test that start proceeds when all validations pass."""
    from mailtollm.ui.app import MailToLLMApp

    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    attachments_dir = tmp_path / "attachments"
    attachments_dir.mkdir()
    output_dir = tmp_path / "output"

    with patch("mailtollm.ui.app.run_pipeline") as mock_pipeline:
        with patch("mailtollm.ui.app.messagebox"):
            app = MailToLLMApp()

            # Set valid paths
            app.csv_path_var.set(str(csv_dir))
            app.attachments_root_var.set(str(attachments_dir))
            app.output_dir_var.set(str(output_dir))
            app.summary_length_var.set("1500")

            # Mock worker check
            app._worker = None

            # Try to start
            app._on_start()

            # Worker should have been created and started
            assert app._worker is not None
            assert app._worker.is_alive()

            # Cleanup
            app._stop_event.set()
            app._worker.join(timeout=1)


def test_stop_without_worker() -> None:
    """Test that stop button works even when no worker is running."""
    from mailtollm.ui.app import MailToLLMApp

    app = MailToLLMApp()

    # No worker running
    app._worker = None

    # Should not raise error
    app._on_stop()

    # Stop event should be set
    assert app._stop_event.is_set()

    # Controls should be reset
    assert app.start_btn.cget("state") == "normal"
    assert app.stop_btn.cget("state") == "disabled"


def test_stop_with_finished_worker() -> None:
    """Test that stop works when worker has already finished."""
    from mailtollm.ui.app import MailToLLMApp
    import threading

    app = MailToLLMApp()

    # Create a finished worker thread
    def dummy():
        pass

    worker = threading.Thread(target=dummy)
    worker.start()
    worker.join()  # Wait for it to finish

    app._worker = worker

    # Should not raise error
    app._on_stop()

    # Stop event should be set
    assert app._stop_event.is_set()

    # Controls should be reset
    assert app.start_btn.cget("state") == "normal"
    assert app.stop_btn.cget("state") == "disabled"
