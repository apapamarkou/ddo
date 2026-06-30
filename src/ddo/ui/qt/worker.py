"""Worker thread that runs backend operations without blocking the GUI."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import QThread, pyqtSignal


class BackendWorker(QThread):
    """Run a callable on a background thread and emit signals for progress/result.

    Usage::

        worker = BackendWorker(my_function, arg1, arg2)
        worker.progress.connect(status_bar.showMessage)
        worker.finished.connect(on_done)
        worker.error.connect(on_error)
        worker.start()
    """

    progress = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(Exception)

    def __init__(
        self,
        fn: Callable[..., object],
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(exc)
