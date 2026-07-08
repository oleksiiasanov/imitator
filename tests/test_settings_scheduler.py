import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as vtx_app


class SettingsSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_config_path = vtx_app.CONFIG_PATH
        self.original_generation = vtx_app.scheduler_generation
        vtx_app.CONFIG_PATH = Path(self.tempdir.name) / "config.json"
        vtx_app.scheduler_generation = 0
        vtx_app.app.config["TESTING"] = True
        self.client = vtx_app.app.test_client()

    def tearDown(self):
        vtx_app.CONFIG_PATH = self.original_config_path
        vtx_app.scheduler_generation = self.original_generation
        self.tempdir.cleanup()

    def read_config(self):
        return json.loads(vtx_app.CONFIG_PATH.read_text(encoding="utf-8"))

    def test_settings_post_saves_autoplay_delay_and_interval(self):
        with (
            patch.object(vtx_app, "stop_player") as stop_player,
            patch.object(vtx_app, "restart_scheduler") as restart_scheduler,
        ):
            response = self.client.post(
                "/settings",
                data={
                    "autoplay_enabled": "on",
                    "delay_minutes": "3",
                    "interval_minutes": "7",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        self.assertEqual(
            self.read_config(),
            {
                "autoplay_enabled": True,
                "start_delay_seconds": 180,
                "interval_seconds": 420,
            },
        )
        stop_player.assert_called_once_with()
        restart_scheduler.assert_called_once_with()

    def test_settings_post_normalizes_invalid_values(self):
        with (
            patch.object(vtx_app, "stop_player"),
            patch.object(vtx_app, "restart_scheduler"),
        ):
            response = self.client.post(
                "/settings",
                data={
                    "delay_minutes": "-10",
                    "interval_minutes": "0",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.read_config(),
            {
                "autoplay_enabled": False,
                "start_delay_seconds": 0,
                "interval_seconds": 60,
            },
        )

    def test_restart_scheduler_starts_new_generation_thread(self):
        created_threads = []

        class FakeThread:
            def __init__(self, target, args, daemon):
                self.target = target
                self.args = args
                self.daemon = daemon
                self.started = False
                created_threads.append(self)

            def start(self):
                self.started = True

        with patch.object(vtx_app.threading, "Thread", FakeThread):
            vtx_app.restart_scheduler()

        self.assertEqual(vtx_app.scheduler_generation, 1)
        self.assertEqual(len(created_threads), 1)
        self.assertIs(created_threads[0].target, vtx_app.scheduler_loop)
        self.assertEqual(created_threads[0].args, (1,))
        self.assertTrue(created_threads[0].daemon)
        self.assertTrue(created_threads[0].started)

    def test_scheduler_uses_configured_start_delay_and_interval(self):
        config = {
            "autoplay_enabled": True,
            "start_delay_seconds": 2,
            "interval_seconds": 3,
        }
        sleep_calls = []
        play_calls = []
        vtx_app.scheduler_generation = 1

        def fake_sleep(seconds):
            sleep_calls.append(seconds)
            if len(sleep_calls) >= 5:
                with vtx_app.scheduler_lock:
                    vtx_app.scheduler_generation += 1

        def fake_play_video_once():
            play_calls.append(True)
            return True

        with (
            patch.object(vtx_app, "load_config", return_value=config),
            patch.object(vtx_app, "play_video_once", side_effect=fake_play_video_once),
            patch.object(vtx_app.time, "sleep", side_effect=fake_sleep),
        ):
            vtx_app.scheduler_loop(1)

        self.assertEqual(sleep_calls, [1, 1, 1, 1, 1])
        self.assertEqual(len(play_calls), 1)


if __name__ == "__main__":
    unittest.main()
