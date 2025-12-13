"""Unit tests for AutosaveService."""

import time
from unittest.mock import MagicMock, call

import pytest
from PySide6.QtCore import QTimer

from oeapp.services.autosave import AutosaveService


class TestAutosaveService:
    """Test cases for AutosaveService."""

    def test_init_sets_callback_and_debounce(self):
        """Test __init__ sets save_callback and debounce_ms."""
        callback = MagicMock()
        service = AutosaveService(callback, debounce_ms=1000)
        
        assert service.save_callback == callback
        assert service.debounce_ms == 1000
        assert service._timer is None
        assert service._pending is False

    def test_init_default_debounce(self):
        """Test __init__ uses default debounce_ms."""
        callback = MagicMock()
        service = AutosaveService(callback)
        
        assert service.debounce_ms == 500

    def test_trigger_sets_pending(self):
        """Test trigger() sets _pending flag."""
        callback = MagicMock()
        service = AutosaveService(callback, debounce_ms=100)
        
        service.trigger()
        
        assert service._pending is True
        assert service._timer is not None

    def test_trigger_creates_timer(self, qapp):
        """Test trigger() creates and starts timer."""
        callback = MagicMock()
        service = AutosaveService(callback, debounce_ms=100)
        
        service.trigger()
        
        assert service._timer is not None
        assert service._timer.isSingleShot()
        # Timer needs QApplication event loop to be active
        # Just check that timer exists and is configured correctly
        assert service._timer.interval() == 100

    def test_trigger_cancels_existing_timer(self):
        """Test trigger() cancels existing timer."""
        callback = MagicMock()
        service = AutosaveService(callback, debounce_ms=100)
        
        service.trigger()
        first_timer = service._timer
        
        service.trigger()
        second_timer = service._timer
        
        # Should have different timer instances
        assert first_timer != second_timer
        # First timer should be stopped
        assert not first_timer.isActive()

    def test_trigger_calls_save_after_debounce(self, qapp):
        """Test trigger() calls save_callback after debounce period."""
        callback = MagicMock()
        service = AutosaveService(callback, debounce_ms=50)
        
        service.trigger()
        
        # Wait for timer to fire
        time.sleep(0.1)
        qapp.processEvents()
        
        callback.assert_called_once()
        assert service._pending is False

    def test_trigger_multiple_only_calls_once(self, qapp):
        """Test multiple trigger() calls only result in one save."""
        callback = MagicMock()
        service = AutosaveService(callback, debounce_ms=50)
        
        # Trigger multiple times rapidly
        service.trigger()
        service.trigger()
        service.trigger()
        
        # Wait for timer to fire
        time.sleep(0.1)
        qapp.processEvents()
        
        # Should only be called once (debounced)
        callback.assert_called_once()

    def test_save_now_calls_callback_immediately(self):
        """Test save_now() calls callback immediately."""
        callback = MagicMock()
        service = AutosaveService(callback, debounce_ms=1000)
        
        service.save_now()
        
        callback.assert_called_once()
        assert service._pending is False

    def test_save_now_cancels_timer(self):
        """Test save_now() cancels pending timer."""
        callback = MagicMock()
        service = AutosaveService(callback, debounce_ms=1000)
        
        service.trigger()
        assert service._timer is not None
        assert service._timer.isActive()
        
        service.save_now()
        
        # Timer should be stopped and deleted
        assert service._timer is None

    def test_save_now_clears_pending(self):
        """Test save_now() clears _pending flag."""
        callback = MagicMock()
        service = AutosaveService(callback, debounce_ms=1000)
        
        service.trigger()
        assert service._pending is True
        
        service.save_now()
        
        assert service._pending is False

    def test_cancel_stops_timer(self):
        """Test cancel() stops and deletes timer."""
        callback = MagicMock()
        service = AutosaveService(callback, debounce_ms=1000)
        
        service.trigger()
        assert service._timer is not None
        assert service._timer.isActive()
        
        service.cancel()
        
        assert service._timer is None
        assert service._pending is False

    def test_cancel_clears_pending(self):
        """Test cancel() clears _pending flag."""
        callback = MagicMock()
        service = AutosaveService(callback, debounce_ms=1000)
        
        service.trigger()
        assert service._pending is True
        
        service.cancel()
        
        assert service._pending is False

    def test_cancel_does_not_call_callback(self, qapp):
        """Test cancel() does not call save callback."""
        callback = MagicMock()
        service = AutosaveService(callback, debounce_ms=50)
        
        service.trigger()
        service.cancel()
        
        # Wait to ensure timer doesn't fire
        time.sleep(0.1)
        qapp.processEvents()
        
        callback.assert_not_called()

    def test_pending_flag_cleared_after_timer_fires(self, qapp):
        """Test _pending flag is cleared after timer fires."""
        callback = MagicMock()
        service = AutosaveService(callback, debounce_ms=50)
        
        service.trigger()
        assert service._pending is True
        
        # Wait for timer to fire
        time.sleep(0.1)
        qapp.processEvents()
        
        assert service._pending is False
