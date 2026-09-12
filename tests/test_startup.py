import unittest
from unittest.mock import patch

import mainpro


class StartupTests(unittest.TestCase):
    def setUp(self):
        targets = {
            "application": "mainpro.QApplication",
            "instance": "mainpro.SingleInstance",
            "window": "mainpro.CareEyesApp",
            "restore": "mainpro.DisplayManager.reset",
            "message": "mainpro.QMessageBox",
        }
        for name, target in targets.items():
            patcher = patch(target)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        self.instance.return_value.acquire.return_value = True
        self.instance.return_value.activation_message = 0xC001
        self.application.return_value.exec_.return_value = 0
        self.window.return_value.winId.return_value = 1234

    def test_secondary_exits_before_creating_window_or_touching_displays(self):
        guard = self.instance.return_value
        guard.acquire.return_value = False
        guard.activate_existing.return_value = True
        self.assertEqual(mainpro.main(), 0)
        guard.activate_existing.assert_called_once()
        guard.close.assert_called_once()
        self.window.assert_not_called()
        self.restore.assert_not_called()
        self.application.return_value.exec_.assert_not_called()

    def test_startup_failure_restores_before_releasing_mutex(self):
        events = []
        self.window.side_effect = RuntimeError("startup failure")
        self.restore.side_effect = lambda: events.append("restore")
        self.instance.return_value.close.side_effect = lambda: events.append("release")
        with self.assertRaisesRegex(RuntimeError, "startup failure"):
            mainpro.main()
        self.assertEqual(events, ["restore", "release"])

    def test_event_loop_failure_cleans_up_before_releasing_mutex(self):
        events = []
        self.application.return_value.exec_.side_effect = RuntimeError("loop failure")
        self.window.return_value._cleanup.side_effect = lambda: events.append("cleanup")
        self.restore.side_effect = lambda: events.append("restore")
        self.instance.return_value.close.side_effect = lambda: events.append("release")
        with self.assertRaisesRegex(RuntimeError, "loop failure"):
            mainpro.main()
        self.assertEqual(events, ["cleanup", "restore", "release"])

    def test_lock_failure_does_not_start_an_unprotected_instance(self):
        self.instance.return_value.acquire.side_effect = OSError("lock failure")
        self.assertEqual(mainpro.main(), 1)
        self.message.critical.assert_called_once()
        self.window.assert_not_called()
        self.restore.assert_not_called()


if __name__ == "__main__":
    unittest.main()
