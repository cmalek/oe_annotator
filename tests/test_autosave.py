"""Unit tests for AutosaveService."""

import unittest
import time
from unittest.mock import Mock

from PySide6.QtWidgets import QApplication

from oeapp.services.autosave import AutosaveService


class TestAutosaveService(unittest.TestCase):
    """Test cases for AutosaveService."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for all tests."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    @classmethod
    def tearDownClass(cls):
        """Clean up QApplication after all tests."""
        if cls.app:
            cls.app.quit()

    def test_debounce_single_call(self):
        """Test that a single trigger call results in one save_now call."""
        save_callback = Mock()
        service = AutosaveService(save_callback, debounce_ms=100)

        service.trigger()

        # Wait for debounce to complete and process Qt events
        start_time = time.time()
        while time.time() - start_time < 0.15:
            self.app.processEvents()
            time.sleep(0.01)

        # Verify save was called exactly once
        save_callback.assert_called_once()

    def test_debounce_multiple_rapid_calls(self):
        """Test that multiple rapid trigger calls are debounced into a single save."""
        save_callback = Mock()
        service = AutosaveService(save_callback, debounce_ms=100)

        # Trigger multiple times in quick succession
        service.trigger()
        self.app.processEvents()
        time.sleep(0.02)
        service.trigger()
        self.app.processEvents()
        time.sleep(0.02)
        service.trigger()
        self.app.processEvents()
        time.sleep(0.02)
        service.trigger()
        self.app.processEvents()

        # Wait for debounce to complete and process Qt events
        start_time = time.time()
        while time.time() - start_time < 0.12:
            self.app.processEvents()
            time.sleep(0.01)

        # Verify save was called exactly once despite 4 triggers
        save_callback.assert_called_once()

    def test_debounce_separated_calls(self):
        """Test that trigger calls separated by debounce period result in multiple saves."""
        save_callback = Mock()
        service = AutosaveService(save_callback, debounce_ms=50)

        # First trigger
        service.trigger()
        # Wait for first debounce to complete and process Qt events
        start_time = time.time()
        while time.time() - start_time < 0.07:
            self.app.processEvents()
            time.sleep(0.01)

        # Second trigger after first one completed
        service.trigger()
        # Wait for second debounce to complete and process Qt events
        start_time = time.time()
        while time.time() - start_time < 0.07:
            self.app.processEvents()
            time.sleep(0.01)

        # Verify save was called twice
        self.assertEqual(save_callback.call_count, 2)

    def test_save_now_bypasses_debounce(self):
        """Test that save_now immediately calls the callback without debouncing."""
        save_callback = Mock()
        service = AutosaveService(save_callback, debounce_ms=1000)

        # Call save_now (should be immediate)
        service.save_now()

        # Verify save was called immediately without waiting
        save_callback.assert_called_once()

    def test_save_now_cancels_pending_trigger(self):
        """Test that save_now cancels any pending debounced trigger."""
        save_callback = Mock()
        service = AutosaveService(save_callback, debounce_ms=100)

        # Trigger (will wait 100ms)
        service.trigger()
        self.app.processEvents()

        # Call save_now immediately (should cancel pending trigger)
        time.sleep(0.02)
        service.save_now()

        # Wait to ensure no additional call happens and process Qt events
        start_time = time.time()
        while time.time() - start_time < 0.12:
            self.app.processEvents()
            time.sleep(0.01)

        # Verify save was called only once (by save_now, not by trigger)
        save_callback.assert_called_once()

    def test_cancel_pending_trigger(self):
        """Test that cancel prevents pending trigger from executing."""
        save_callback = Mock()
        service = AutosaveService(save_callback, debounce_ms=100)

        # Trigger
        service.trigger()
        self.app.processEvents()

        # Cancel before debounce completes
        time.sleep(0.02)
        service.cancel()

        # Wait to ensure no call happens and process Qt events
        start_time = time.time()
        while time.time() - start_time < 0.12:
            self.app.processEvents()
            time.sleep(0.01)

        # Verify save was never called
        save_callback.assert_not_called()

    def test_multiple_triggers_with_intermediate_completion(self):
        """Test complex pattern of triggers with intermediate completions."""
        save_callback = Mock()
        service = AutosaveService(save_callback, debounce_ms=50)

        # First burst of triggers
        service.trigger()
        self.app.processEvents()
        time.sleep(0.01)
        service.trigger()
        self.app.processEvents()
        time.sleep(0.01)
        service.trigger()
        self.app.processEvents()

        # Wait for first debounce to complete and process Qt events
        start_time = time.time()
        while time.time() - start_time < 0.07:
            self.app.processEvents()
            time.sleep(0.01)

        # Second burst of triggers
        service.trigger()
        self.app.processEvents()
        time.sleep(0.01)
        service.trigger()
        self.app.processEvents()

        # Wait for second debounce to complete and process Qt events
        start_time = time.time()
        while time.time() - start_time < 0.07:
            self.app.processEvents()
            time.sleep(0.01)

        # Should have exactly 2 saves (one for each burst)
        self.assertEqual(save_callback.call_count, 2)

    def test_error_in_callback_doesnt_break_service(self):
        """Test that errors in the save callback don't break the service."""
        save_callback = Mock(side_effect=[Exception("Save failed"), None])
        service = AutosaveService(save_callback, debounce_ms=50)

        # First trigger (will fail)
        service.trigger()
        # Wait for debounce to complete and process Qt events
        start_time = time.time()
        while time.time() - start_time < 0.07:
            self.app.processEvents()
            time.sleep(0.01)

        # Second trigger (should succeed)
        service.trigger()
        # Wait for debounce to complete and process Qt events
        start_time = time.time()
        while time.time() - start_time < 0.07:
            self.app.processEvents()
            time.sleep(0.01)

        # Verify both attempts were made
        self.assertEqual(save_callback.call_count, 2)

    def test_debounce_timing_accuracy(self):
        """Test that debounce timing is reasonably accurate."""
        save_callback = Mock()
        debounce_ms = 100
        service = AutosaveService(save_callback, debounce_ms=debounce_ms)

        start_time = time.time()
        service.trigger()

        # Wait for completion and process Qt events
        while time.time() - start_time < 0.12:
            self.app.processEvents()
            time.sleep(0.01)

        elapsed = time.time() - start_time

        # Verify callback was called
        save_callback.assert_called_once()

        # Verify timing is approximately correct (within 50ms tolerance)
        self.assertGreaterEqual(elapsed, debounce_ms / 1000.0)
        self.assertLess(elapsed, (debounce_ms + 50) / 1000.0)

    def test_concurrent_trigger_and_save_now(self):
        """Test interaction between trigger and save_now."""
        save_callback = Mock()
        service = AutosaveService(save_callback, debounce_ms=100)

        # Start a trigger
        service.trigger()
        self.app.processEvents()
        time.sleep(0.05)

        # Call save_now while trigger is pending
        service.save_now()

        # Wait to ensure trigger doesn't fire and process Qt events
        start_time = time.time()
        while time.time() - start_time < 0.08:
            self.app.processEvents()
            time.sleep(0.01)

        # Should only have one call (from save_now)
        save_callback.assert_called_once()


if __name__ == '__main__':
    unittest.main()
