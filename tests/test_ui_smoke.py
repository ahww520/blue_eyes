import json
import math
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt5.QtCore import QCoreApplication, QEvent, QRect, Qt
from PyQt5.QtGui import QColor, QImage, QPainter
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

    def test_pet_interaction_modes_render_and_persist(self):
        pet = self.window.pet
        self.assertEqual(pet.interaction_mode, "move")
        self.assertEqual(self.window.pet_interaction_mode, "move")
        self.assertTrue(self.window.pet_interaction_buttons["move"].isChecked())

        self.window._set_pet_interaction_mode("tickle")
        self.assertEqual(pet.interaction_mode, "tickle")
        self.assertEqual(self.window.pet_preview.interaction_mode, "tickle")
        self.assertTrue(self.window.pet_interaction_buttons["tickle"].isChecked())
        self.assertIn("挠痒痒", self.window.pet_interaction_hint_label.text())

        # 拖动时应产生 wobble 与粒子，松手后回弹而不是停在形变状态。
        pet._begin_interaction(75, 85, 200, 200)
        pet._update_drag_interaction(118, 84, 245, 199)
        self.assertTrue(pet._interaction_active)
        self.assertGreater(pet._interaction_target["wobble"], 0)
        pet._finish_interaction(was_dragged=True)
        self.assertFalse(pet._interaction_active)
        self.assertGreater(len(pet._particles), 0)

        # "抛一下"和双击彩蛋都需要绘制通过，覆盖局部变换和粒子 renderer。
        self.window._set_pet_interaction_mode("toss")
        pet._begin_interaction(75, 82, 100, 100)
        pet._update_drag_interaction(109, 53, 170, 25)
        pet._finish_interaction(was_dragged=True)
        self.assertTrue(pet._toss_active)
        for _ in range(8):
            pet._tick_interaction(.06)
        pet.trigger_surprise("happy")
        self.assertEqual(pet._surprise_kind, "happy")
        pet.show()
        self.application.processEvents()
        self.assertFalse(pet.grab().isNull())

        self.window._save_settings()
        with open(self.config_path, encoding="utf-8") as handle:
            saved = json.load(handle)
        self.assertEqual(saved["pet_interaction_mode"], "toss")


class PetArtworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        cls.application.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.preview = mainpro.PetPreview("blue_cat", animated=False, halo=False)

    def tearDown(self):
        self.preview.deleteLater()
        self.application.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    @staticmethod
    def _image_bytes(image):
        converted = image.convertToFormat(QImage.Format_RGBA8888)
        return converted.constBits().asstring(converted.byteCount())

    def _render(self, pet_kind, state="idle", decoration="scarf", scale=1.0,
                blink=0, look=(0.0, 0.0), surprise=None):
        self.preview._pet_kind = pet_kind
        self.preview._state = state
        self.preview._decoration = decoration
        self.preview._phase = .35
        self.preview._blink = blink
        self.preview._look = look
        self.preview._surprise_kind = surprise
        image = QImage(round(self.preview.W * scale), round(self.preview.H * scale),
                       QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.scale(scale, scale)
        transform = painter.worldTransform()
        try:
            self.preview._paint_scene(painter, show_bar=False, show_bubble=False)
            self.assertEqual(painter.worldTransform(), transform)
        finally:
            painter.end()
        return image

    def test_all_skins_states_and_unlocked_decorations_fit_the_canvas(self):
        for pet_kind, style in mainpro.DesktopPet.PET_STYLES.items():
            for state in style["palette"]:
                for decoration, info in mainpro.DesktopPet.DECORATIONS.items():
                    if not info["unlocked"]:
                        continue
                    with self.subTest(pet_kind=pet_kind, state=state, decoration=decoration):
                        image = self._render(pet_kind, state, decoration)
                        alpha = self._image_bytes(image)[3::4]
                        width = image.width()
                        border = alpha[:width] + alpha[-width:] + alpha[::width] + alpha[width - 1::width]
                        self.assertFalse(any(border), "Artwork is clipped at the window edge")
                        self.assertGreater(sum(value > 0 for value in alpha), 3500)

    def test_every_character_blinks_without_changing_its_silhouette(self):
        face = QRect(44, mainpro.DesktopPet.BODY_TOP + 20, 62, 40)
        for pet_kind in mainpro.DesktopPet.PET_STYLES:
            with self.subTest(pet_kind=pet_kind):
                awake = self._render(pet_kind)
                blinking = self._render(pet_kind, blink=3)
                self.assertNotEqual(self._image_bytes(awake.copy(face)),
                                    self._image_bytes(blinking.copy(face)))
                self.assertEqual(self._image_bytes(awake)[3::4],
                                 self._image_bytes(blinking)[3::4])

    def test_interaction_poses_do_not_crop_ears_or_tails(self):
        poses = {
            "squish": {"scale_x": 1.25, "scale_y": .64, "y": 8},
            "stretch": {"scale_x": .9, "scale_y": 1.35, "y": -12, "rotation": .2},
            "toss": {"x": 16, "y": -27, "rotation": .3, "scale_y": 1.14},
        }
        for pet_kind in mainpro.DesktopPet.PET_STYLES:
            for decoration in ("scarf", "sprout"):
                for pose_name, pose in poses.items():
                    with self.subTest(pet_kind=pet_kind, decoration=decoration, pose=pose_name):
                        self.preview._interaction_current = self.preview._neutral_interaction_values()
                        self.preview._interaction_current.update(pose)
                        image = self._render(pet_kind, decoration=decoration)
                        alpha = self._image_bytes(image)[3::4]
                        width = image.width()
                        border = alpha[:width] + alpha[-width:] + alpha[::width] + alpha[width - 1::width]
                        self.assertFalse(any(border), "Interaction crops the character")

    def test_every_character_tracks_the_pointer(self):
        face = QRect(44, mainpro.DesktopPet.BODY_TOP + 20, 62, 40)
        for pet_kind in mainpro.DesktopPet.PET_STYLES:
            with self.subTest(pet_kind=pet_kind):
                left = self._render(pet_kind, look=(-3.0, -2.5))
                right = self._render(pet_kind, look=(3.0, 2.5))
                self.assertNotEqual(self._image_bytes(left.copy(face)),
                                    self._image_bytes(right.copy(face)))

    def test_surprises_and_tickle_change_expression_not_care_state(self):
        face = QRect(44, mainpro.DesktopPet.BODY_TOP + 20, 62, 40)
        for pet_kind in mainpro.DesktopPet.PET_STYLES:
            with self.subTest(pet_kind=pet_kind):
                normal = self._render(pet_kind)
                happy = self._render(pet_kind, surprise="happy")
                self.assertEqual(self.preview._pet_expression(), "happy")
                self.assertEqual(self.preview._state, "idle")
                self.assertNotEqual(self._image_bytes(normal.copy(face)),
                                    self._image_bytes(happy.copy(face)))
                self._render(pet_kind, surprise="sleep")
                self.assertEqual(self.preview._pet_expression(), "sleep")
                self.assertEqual(self.preview._state, "idle")
        self.preview._surprise_kind = None
        self.preview._interaction_active = True
        self.preview._interaction_mode = "tickle"
        self.assertEqual(self.preview._pet_expression(), "happy")
        self.preview._state = "resting"
        self.assertEqual(self.preview._pet_expression(), "sleep")

    def test_robot_accessories_do_not_cover_the_pixel_heart(self):
        baseline = round(mainpro.DesktopPet.BODY_TOP + math.sin(.35) * 3 - 5)
        for decoration in ("scarf", "sprout"):
            with self.subTest(decoration=decoration):
                image = self._render("pixel_robot", decoration=decoration)
                heart_pixels = sum(
                    image.pixelColor(pixel_x, pixel_y) == QColor("#f0b6b6")
                    for pixel_x in range(68, 83)
                    for pixel_y in range(baseline + 79, baseline + 94)
                )
                self.assertEqual(heart_pixels, 144)

    def test_thumbnail_and_high_dpi_rendering(self):
        for pet_kind in mainpro.DesktopPet.PET_STYLES:
            for scale in (.35, 1.25, 2.0):
                with self.subTest(pet_kind=pet_kind, scale=scale):
                    image = self._render(pet_kind, scale=scale)
                    self.assertEqual(image.width(), round(mainpro.DesktopPet.W * scale))
                    self.assertEqual(image.height(), round(mainpro.DesktopPet.H * scale))
                    alpha = self._image_bytes(image)[3::4]
                    self.assertGreater(sum(value > 0 for value in alpha), 3000 * scale * scale)

    def test_sleep_marks_do_not_require_font_glyphs(self):
        with patch.object(QPainter, "drawText") as draw_text:
            for pet_kind in mainpro.DesktopPet.PET_STYLES:
                self._render(pet_kind, state="resting")
        draw_text.assert_not_called()


if __name__ == "__main__":
    unittest.main()
