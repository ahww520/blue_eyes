import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt5.QtCore import QCoreApplication, QEvent
from PyQt5.QtWidgets import QApplication

import mainpro


class OffscreenUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        cls.application.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        config_path = os.path.join(self.directory.name, "settings.json")
        config = dict(mainpro.CareEyesApp._DEFAULTS)
        config.update({
            "pet_enabled": False,
            "sound_enabled": False,
            "pet_kind": "mint_bunny",
        })
        self.config_path = config_path
        with open(config_path, "w", encoding="utf-8") as handle:
            json.dump(config, handle)

        def fake_tray(window):
            window.tray = Mock()

        patches = [
            patch("mainpro.CONFIG_FILE", config_path),
            patch("mainpro.DisplayManager.apply", return_value=True),
            patch("mainpro.DisplayManager.reset", return_value=True),
            patch("mainpro.WindowsActivityMonitor"),
            patch("mainpro.CareEyesApp.init_tray", fake_tray),
            patch("mainpro.CareEyesApp.init_hotkeys"),
            patch("mainpro.CareEyesApp._read_autostart", return_value=False),
            patch("mainpro.CareEyesApp._set_autostart"),
            patch("mainpro.CareEyesApp._refresh_system_metrics"),
            patch("mainpro._is_admin", return_value=True),
        ]
        for patcher in patches:
            started = patcher.start()
            self.addCleanup(patcher.stop)
            if patcher.attribute == "WindowsActivityMonitor":
                started.return_value.idle_seconds.return_value = 0
        self.window = mainpro.CareEyesApp()
        self.addCleanup(self.close_window)
        self.application.processEvents()

    def close_window(self):
        self.window._cleanup()
        if self.window.pet is not None:
            self.window.pet._anim_timer.stop()
            self.window.pet._chat_timer.stop()
            self.window.pet._msg_timer.stop()
            self.window.pet.deleteLater()
        self.window.deleteLater()
        self.application.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def test_construct_pause_toggle_and_resume(self):
        self.assertTrue(self.window._work_clock.active)
        self.window._set_session_pause(locked=True)
        self.assertIn("锁屏暂停", self.window.next_rest_label.text())
        self.assertFalse(self.window._work_clock.active)
        self.window._hk_toggle()
        self.assertFalse(self.window.is_enabled)
        self.assertEqual(self.window.next_rest_label.text(), "已暂停")
        self.window._set_session_pause(locked=False)
        self.window._hk_toggle()
        self.assertTrue(self.window.is_enabled)
        self.assertTrue(self.window._work_clock.active)
        self.window.interval_spin.setValue(6)
        self.window.apply_timer_settings()
        self.assertEqual(self.window._next_rest_secs, 360)

    def test_rest_overlay_close_and_settings_reset(self):
        self.window.show_rest_overlay()
        overlay = self.window.overlay
        self.assertIsNotNone(overlay)
        self.assertFalse(self.window._work_clock.active)
        self.window.show_rest_overlay()
        self.assertIs(self.window.overlay, overlay)
        self.application.processEvents()
        overlay._close()
        self.assertIsNone(self.window.overlay)
        self.assertTrue(self.window._work_clock.active)
        self.window._reset_settings()
        self.assertEqual(self.window.today_minutes, 0)
        self.assertEqual(self.window._next_rest_secs, 45 * 60)
        self.assertTrue(self.window.is_enabled)

    def test_pet_styles_change_and_persist(self):
        expected_new_styles = {
            "seagull": "小海鸥",
            "cream_cat": "奶油猫",
            "pixel_robot": "像素机器人",
        }
        self.assertEqual(self.window.pages.count(), 5)
        self.assertEqual(
            [button.text() for button in self.window.nav_btns],
            ["护眼", "休息", "统计", "桌宠", "设置"],
        )
        self.assertFalse(hasattr(self.window, "pet_cb"))
        self.assertFalse(hasattr(self.window, "pet_style_combo"))
        self.assertGreaterEqual(len(mainpro.DesktopPet.PET_STYLES), 9)
        self.assertEqual(
            set(self.window.pet_skin_buttons),
            set(mainpro.DesktopPet.PET_STYLES),
        )
        for pet_kind, label in expected_new_styles.items():
            self.assertEqual(
                mainpro.DesktopPet.PET_STYLES[pet_kind]["label"], label
            )

        self.assertEqual(self.window.pet_kind, "mint_bunny")
        self.assertEqual(self.window.pet._pet_kind, "mint_bunny")
        self.assertTrue(self.window.pet_skin_buttons["mint_bunny"].isChecked())
        self.assertEqual(self.window.pet_preview._pet_kind, "mint_bunny")

        self.window.pet_skin_buttons["pixel_robot"].click()
        self.assertEqual(self.window.pet._pet_kind, "pixel_robot")
        self.assertEqual(self.window.pet_preview._pet_kind, "pixel_robot")
        self.assertTrue(self.window.pet_skin_buttons["pixel_robot"].isChecked())
        self.assertEqual(self.window.pet_name_label.text(), "像素机器人")

        self.window.pet_enable_toggle.click()
        self.assertTrue(self.window.pet_enabled)
        self.assertTrue(self.window.pet.isVisible())
        self.assertEqual(self.window.pet_status_label.text(), "桌宠已开启")
        self.window._save_settings()

        with open(self.config_path, encoding="utf-8") as handle:
            saved = json.load(handle)
        self.assertEqual(saved["pet_kind"], "pixel_robot")
        self.assertTrue(saved["pet_enabled"])

        for pet_kind in mainpro.DesktopPet.PET_STYLES:
            pet = mainpro.DesktopPet(pet_kind=pet_kind)
            for state in ("idle", "tired", "resting", "off"):
                pet._state = state
                pet.show()
                self.application.processEvents()
                self.assertFalse(pet.grab().isNull(), f"{pet_kind}:{state}")
            pet._anim_timer.stop()
            pet._chat_timer.stop()
            pet._msg_timer.stop()
            pet.deleteLater()
        self.application.processEvents()


if __name__ == "__main__":
    unittest.main()
