"""Autosave service with debounced writes."""

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class AutosaveService:
    """
    Service for debounced autosave operations.

    Args:
        save_callback: Function to call when saving
        debounce_ms: Debounce delay in milliseconds

    """

    def __init__(
        self, save_callback: Callable[[], None], debounce_ms: int = 500
    ) -> None:
        #: The function to call when saving.
        self.save_callback = save_callback
        #: The debounce delay in seconds.j
        self.debounce_ms = debounce_ms / 1000.0  # Convert to seconds
        #: The timer for the debounce.
        self._timer: threading.Timer | None = None
        #: The lock for the autosave.
        self._lock = threading.Lock()
        #: Whether there is a pending autosave.
        self._pending = False

    def trigger(self) -> None:
        """
        Trigger autosave (will be debounced).
        """
        with self._lock:
            self._pending = True
            # Cancel existing timer if any
            if self._timer:
                self._timer.cancel()
            # Start new timer
            self._timer = threading.Timer(self.debounce_ms, self._save)
            self._timer.start()

    def _save(self) -> None:
        """
        Execute the save callback.

        This method is either called manually by the user via the :meth:`save_now`
        method or called by the autosave timer when the debounce delay has
        elapsed. It checks if there is a pending autosave and if so, calls the
        save callback. If the save callback raises an exception, it is caught
        and the pending autosave is set to False.
        """
        with self._lock:
            if self._pending:
                try:
                    self.save_callback()
                    self._pending = False
                except Exception as e:
                    print(f"Autosave error: {e}")
                    self._pending = False

    def save_now(self) -> None:
        """
        Force immediate save (bypasses debounce), meaning the autosave timer is
        cancelled and the save callback is called immediately.

        """
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self._pending = False
        try:
            self.save_callback()
        except Exception as e:
            print(f"Save error: {e}")

    def cancel(self) -> None:
        """
        Cancel pending autosave, meaning the autosave timer is cancelled and the
        save callback is not called.
        """
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self._pending = False
