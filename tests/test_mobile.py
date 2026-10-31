from datetime import datetime, timezone
import configparser
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import tempfile
import time
import threading
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PyQt6.QtCore import QCoreApplication, QEvent, QObject, QPoint, QPointF, QUrl, Qt, qInstallMessageHandler
from PyQt6.QtGui import QFont, QFontDatabase, QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine, QQmlExpression
from PyQt6.QtQuick import QQuickItem, QQuickWindow
from PyQt6.QtTest import QTest
from elasticsearch import Elasticsearch

from modules.backend import Backend, EventModel, Worker
from modules.events import Acquisition, EventBuffer, MAX_EVENTS, normalize
from modules.ina219_module import INA219
from modules.system import Battery, PowerPolicy, SystemSampler
from tools.configure import boot_config, environment
from tools.system_control import brightness, status

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)

def visual_items(window, name):
    def walk(item):
        if item.objectName() == name:
            yield item
        for child in item.childItems():
            yield from walk(child)
    return list(walk(window.contentItem()))


def hit(number: int, **source):
    return {
        "_index": "logstash-2026.10.31", "_id": str(number), "sort": [NOW.isoformat(), number],
        "_source": {
            "@timestamp": NOW.isoformat(), "type": "Cowrie", "src_ip": "2001:db8::1",
            "dest_port": "22", **source,
        },
    }


class EventTests(unittest.TestCase):
    def test_normalized_ui_fields_and_destination(self):
        event = normalize(hit(1, username="root", password="fixture-only", input="id",
                              ip_rep="Known attacker", geoip_ext={"latitude": 48.14, "longitude": 11.58}))
        data = event.variant()
        self.assertEqual(data["reputation"], "Known attacker")
        self.assertEqual(data["command"], "id")
        self.assertEqual(data["destinationLatitude"], 48.14)
        self.assertIsNone(normalize(hit(2)).variant()["destinationLatitude"])

    def test_partial_ipv6_and_details(self):
        event = normalize(hit(1, input="<script>not markup</script>", geoip={"country_code2": "../etc", "latitude": "nan"}))
        self.assertEqual(event.source_ip, "2001:db8::1")
        self.assertEqual(event.country_code, "")
        self.assertIsNone(event.latitude)
        self.assertIn(("Command", "<script>not markup</script>"), event.details)
        self.assertEqual(event.protocol, "SSH")

    def test_bad_timestamp_is_not_silently_defaulted(self):
        for timestamp in ("invalid", "2026-10-31T12:00:00"):
            with self.assertRaises(ValueError):
                normalize(hit(1, **{"@timestamp": timestamp}))

    def test_buffer_is_bounded_and_deduplicated(self):
        buffer = EventBuffer()
        incoming = [normalize(hit(number)) for number in range(300)]
        events, fresh = buffer.merge(incoming + incoming)
        self.assertEqual(len(events), MAX_EVENTS)
        self.assertEqual(len(fresh), 300)
        self.assertEqual(buffer.merge(incoming)[1], [])
        buffer.merge([normalize(hit(number)) for number in range(6000)])
        self.assertEqual(len(buffer.seen), 5000)
        self.assertEqual(len(buffer.events), 200)

    def client(self):
        client = Mock()
        client.open_point_in_time.return_value = {"id": "pit"}
        return client

    def test_pagination_equal_timestamps_and_overlap(self):
        client = self.client()
        client.search.side_effect = [
            {"hits": {"hits": [hit(number) for number in range(150, 50, -1)]}, "pit_id": "pit-2"},
            {"hits": {"hits": [hit(number) for number in range(50, -1, -1)]}},
            {"hits": {"hits": [hit(1)]}},
        ]
        acquisition = Acquisition(client)
        result = acquisition.poll(NOW)
        self.assertEqual(len(result["events"]), 151)
        arguments = client.search.call_args_list[1].kwargs
        self.assertEqual(arguments["search_after"], hit(51)["sort"])
        self.assertEqual(arguments["pit"]["id"], "pit-2")
        self.assertEqual(acquisition.poll(NOW)["fresh"], [])
        self.assertEqual(client.open_point_in_time.call_count, 2)
        acquisition.close()
        self.assertEqual([call.kwargs["id"] for call in client.close_point_in_time.call_args_list], ["pit-2", "pit"])
        client.close.assert_called_once()

    def test_poll_cap_is_explicit(self):
        client = self.client()
        client.search.return_value = {"hits": {"hits": [hit(number) for number in range(100)]}}
        result = Acquisition(client).poll(NOW)
        self.assertEqual(client.search.call_count, 10)
        self.assertIn("capped", result["notice"])
        self.assertLessEqual(len(result["fresh"]), 32)

    def test_timeout_preserves_watermark(self):
        client = self.client()
        client.search.return_value = {"timed_out": True}
        acquisition = Acquisition(client)
        with self.assertRaises(TimeoutError):
            acquisition.poll(NOW)
        self.assertIsNone(acquisition.watermark)

    def test_counts_and_selected_chart_use_one_request(self):
        client = self.client()
        client.search.return_value = {"aggregations": {
            "counts": {"buckets": {duration: {"doc_count": 123} for duration in ("1m", "15m", "1h", "24h")}},
            "selected": {"timeline": {"buckets": [{"doc_count": 2, "key": 1793448000000}]},
                         "countries": {"buckets": []}, "honeypots": {"buckets": []}, "services": {"buckets": []}},
        }}
        result = Acquisition(client).statistics("24h")
        self.assertEqual(client.search.call_count, 1)
        self.assertEqual(result["counts"]["24h"], 123)
        self.assertEqual(result["timeline"], [2])
        self.assertEqual(result["timelineTimes"], [1793448000000])
        self.assertEqual(len(client.search.call_args.kwargs["aggs"]["counts"]["filters"]["filters"]), 4)
        with self.assertRaises(ValueError):
            Acquisition(client).statistics("forever")

    def test_cancellation(self):
        acquisition = Acquisition(self.client(), cancelled=lambda: True)
        with self.assertRaises(InterruptedError):
            acquisition.poll(NOW)

    def test_actual_es9_sdk_serializes_requests(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                data = json.loads(body) if body else {}
                requests.append((self.path, data, self.headers.get("Accept", "")))
                if "/_pit" in self.path:
                    response = {"id": "snapshot"}
                else:
                    response = {"hits": {"hits": [hit(1)]}, "pit_id": "snapshot"}
                encoded = json.dumps(response).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("X-Elastic-Product", "Elasticsearch")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def do_DELETE(self):
                self.do_POST()

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        acquisition = Acquisition(Elasticsearch(f"http://127.0.0.1:{server.server_port}", max_retries=0))
        try:
            self.assertEqual(len(acquisition.poll(NOW)["events"]), 1)
        finally:
            acquisition.close()
            server.shutdown()
            server.server_close()
            thread.join()
        search = next(request for request in requests if "/_search" in request[0])
        self.assertIsInstance(search[1]["_source"]["includes"], list)
        self.assertIn("compatible-with=9", search[2])
        self.assertIn("allow_partial_search_results=false", search[0])


class PowerTests(unittest.TestCase):
    def battery(self, percentage=70, charging=False):
        return Battery(7.7, -0.8, 6.2, percentage, charging)

    def test_brightness_transitions_and_override(self):
        policy = PowerPolicy()
        self.assertEqual(policy.update(self.battery())[0], 60)
        policy.set_manual(85)
        self.assertEqual(policy.update(self.battery())[0], 85)
        self.assertEqual(policy.update(self.battery(charging=True))[0], 85)
        self.assertEqual(policy.update(self.battery())[0], 60)
        policy.set_manual(35)
        self.assertEqual(policy.update(self.battery())[0], 35)
        self.assertIsNone(policy.update(None)[0])
        self.assertIsNone(policy.update(self.battery(charging=None))[0])
        with self.assertRaises(ValueError):
            policy.set_manual(0)
        policy = PowerPolicy()
        policy.set_manual(85)
        policy.update(None)
        self.assertEqual(policy.update(self.battery())[0], 85)

    def test_shutdown_requires_three_consecutive_valid_discharge_samples(self):
        policy = PowerPolicy()
        self.assertFalse(policy.update(self.battery(5))[1])
        self.assertFalse(policy.update(None)[1])
        self.assertFalse(policy.update(self.battery(5))[1])
        self.assertFalse(policy.update(self.battery(5))[1])
        self.assertTrue(policy.update(self.battery(5))[1])
        self.assertFalse(policy.update(self.battery(5))[1])
        policy = PowerPolicy()
        for _ in range(5):
            self.assertFalse(policy.update(self.battery(5, charging=True))[1])

    def test_sensor_units_and_limits(self):
        device = Mock()
        device.getBusVoltage_V.return_value = 7.2
        device.getCurrent_mA.return_value = -1000
        device.getPower_W.return_value = 7.2
        value = Battery.read(device)
        self.assertAlmostEqual(value.current, -1)
        self.assertAlmostEqual(value.percentage, 50)
        self.assertFalse(value.charging)
        device.getBusVoltage_V.return_value = float("nan")
        with self.assertRaises(ValueError):
            Battery.read(device)

    def test_ina219_register_signedness(self):
        device = INA219.__new__(INA219)
        device._cal_value = 4096
        device._current_lsb = 0.1
        device._power_lsb = 0.002
        device.read = Mock(return_value=65535)
        device.write = Mock()
        self.assertAlmostEqual(device.getCurrent_mA(), -0.1)
        self.assertAlmostEqual(device.getShuntVoltage_mV(), -0.01)
        self.assertAlmostEqual(device.getPower_W(), 131.07)
        device.read.reset_mock()
        device.getBusVoltage_V()
        self.assertEqual(device.read.call_count, 1)

    def test_no_control_when_ups_is_unavailable(self):
        sampler = SystemSampler()
        with patch("modules.ina219_module.INA219", side_effect=OSError("missing")), patch("modules.system.control") as helper:
            data = sampler.sample()
        helper.assert_not_called()
        self.assertEqual(data["battery"], {})
        self.assertIn("missing", data["error"])
        self.assertFalse(data["shutdown"])

    def test_history_expires_by_time_even_when_sensor_fails(self):
        sampler = SystemSampler()
        sampler.history.extend([(0, 1), (599, 2), (601, 3)])
        with patch("modules.system.time.monotonic", return_value=1200), \
             patch("modules.ina219_module.INA219", side_effect=OSError("missing")):
            data = sampler.sample()
        self.assertEqual(data["history"], [3])


class ConfigurationTests(unittest.TestCase):
    def test_services_keep_gpu_access_without_docker_or_network_dependency(self):
        display = configparser.ConfigParser()
        display.read(ROOT / "settings" / "tpotdisplay.service")
        self.assertEqual(display["Service"]["User"], "tpotui")
        groups = display["Service"]["SupplementaryGroups"].split()
        self.assertIn("render", groups)
        self.assertIn("i2c", groups)
        self.assertNotIn("docker", groups)
        self.assertEqual(display["Unit"]["Wants"], "tpotweston.service")
        self.assertNotIn("network", display["Unit"]["After"])
        compositor = configparser.ConfigParser()
        compositor.read(ROOT / "settings" / "tpotweston.service")
        self.assertEqual(compositor["Service"]["Restart"], "always")
        self.assertEqual(compositor["Unit"]["Wants"], "seatd.service")

    def test_display_config_idempotence_backup_and_switch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.txt"
            original = "dtparam=i2c_arm=on\n[all]\ndtoverlay=vc4-kms-v3d\n"
            config.write_text(original)
            for overlay in ("vc4-kms-v3d", "vc4-kms-dsi-7inch", "vc4-kms-dsi-waveshare-panel"):
                (root / f"{overlay}.dtbo").touch()
            boot_config(config, "8", root)
            first = config.read_text()
            boot_config(config, "8", root)
            self.assertEqual(config.read_text(), first)
            boot_config(config, "43", root)
            self.assertNotIn("8_0_inch", config.read_text())
            self.assertEqual(config.read_text().count("dtoverlay=vc4-kms-v3d"), 1)
            self.assertEqual((root / "config.txt.tpotmobile.bak").read_text(), original)

    def test_environment_policy_and_unrelated_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("TPOT_TYPE=HIVE\nTPOT_PULL_POLICY=always\nTPOT_VERSION=24.04.2\n")
            environment(path)
            first = path.read_text()
            environment(path)
            self.assertEqual(path.read_text(), first)
            self.assertIn("TPOT_PULL_POLICY=missing", first)
            self.assertIn("TPOT_VERSION=24.04.2", first)

    def test_backlight_uses_hardware_maximum_and_never_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            device = root / "rpi_backlight"
            device.mkdir()
            (device / "max_brightness").write_text("255")
            (device / "brightness").write_text("255")
            self.assertEqual(brightness(60, root)["brightness"], 60)
            self.assertEqual((device / "brightness").read_text(), "153")
            brightness(5, root)
            self.assertGreater(int((device / "brightness").read_text()), 0)
            with self.assertRaises(ValueError):
                brightness(0, root)
            (root / "10-0045").mkdir()
            with self.assertRaises(ValueError):
                brightness(60, root)

    def test_container_scope_is_fixed(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.ini"
            config.write_text("[tpot]\nproject=tpotce\n")
            with patch("tools.system_control.subprocess.run", return_value=Mock(stdout=json.dumps({
                "Names": "cowrie", "State": "running", "Status": "Up 1 hour",
            }))) as run:
                self.assertEqual(status(config)["containers"][0]["name"], "cowrie")
            self.assertIn("label=com.docker.compose.project=tpotce", run.call_args.args[0])


class QtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QGuiApplication.instance() or QGuiApplication([])
        cls.application.setFont(QFont(QFontDatabase.families()[0]))

    def load_design(self, width=800, height=480):
        backend = Backend("normal")
        sample = [normalize(hit(index, geoip={
            "country_name": "Germany" if index % 2 == 0 else "Japan",
            "country_code2": "DE" if index % 2 == 0 else "JP",
            "latitude": 50.11 if index % 2 == 0 else 35.68,
            "longitude": 8.68 if index % 2 == 0 else 139.76,
        }, geoip_ext={"latitude": 48.14, "longitude": 11.58},
            username="root", password="fixture-only", input="uname -a; id",
            ip_rep="Known attacker")).variant() for index in range(6)]
        backend.receive_data({
            "events": sample, "eventsOk": True, "statsOk": True, "timeframe": "1h",
            "counts": {"1m": 42, "15m": 762, "1h": 3186, "24h": 28641},
            "timeline": [10, 30, 12, 44], "timelineTimes": [NOW.timestamp() * 1000 + i * 60000 for i in range(4)],
            "countries": [{"name": "Germany", "count": 1268, "code": "de"}, {"name": "Japan", "count": 318, "code": "jp"}],
            "honeypots": [{"name": "Cowrie", "count": 1268}, {"name": "Tanner", "count": 318}],
            "services": [{"name": "SSH / 22", "count": 1268}],
        })
        engine = QQmlApplicationEngine()
        context = engine.rootContext()
        for name, value in (("backend", backend), ("fixtureWidth", width), ("fixtureHeight", height),
                            ("uiFontFamily", self.application.font().family()), ("uiMonoFamily", self.application.font().family())):
            context.setContextProperty(name, value)
        engine.load(QUrl.fromLocalFile(str(ROOT / "qml/Main.qml")))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        window.setProperty("startupVisible", False)
        window.setProperty("startupComplete", True)
        def dispose():
            backend.close()
            engine.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.addCleanup(dispose)
        QTest.qWait(70)
        return backend, engine, window

    def test_live_follow_and_held_selection(self):
        backend = Backend("normal")
        first = normalize(hit(1)).variant()
        second = normalize(hit(2)).variant()
        backend.receive_data({"events": [first]})
        self.assertEqual(backend.selected["identity"], first["identity"])
        backend.selectEvent(first["identity"])
        backend.receive_data({"events": [second, first]})
        self.assertFalse(backend.state["following"])
        self.assertEqual(backend.selected["identity"], first["identity"])
        backend.receive_data({"events": [second]})
        self.assertEqual(backend.selected["identity"], first["identity"])
        backend.followLive()
        self.assertTrue(backend.state["following"])
        self.assertEqual(backend.selected["identity"], second["identity"])
        backend.close()

    def test_native_three_complete_events_and_stream_timestamps(self):
        for width, height in ((800, 480), (1280, 800)):
            backend, engine, window = self.load_design(width, height)
            reputation = visual_items(window, "visibleReputation")[0]
            detail = visual_items(window, "alarmDetails")[0]
            self.assertLessEqual(reputation.mapToItem(detail, QPointF(reputation.width(), reputation.height())).y(), detail.height())
            if width == 1280:
                feed = visual_items(window, "eventFeed")[0]
                cards = [item for item in visual_items(window, "eventCard") if item.y() + item.height() <= feed.height()]
                self.assertGreaterEqual(len(cards), 3)
                self.assertTrue(all(item.property("font").pixelSize() == 18 for item in visual_items(window, "eventTimestamp")))
            window.setProperty("page", 2)
            QTest.qWait(50)
            feed = visual_items(window, "eventFeed")[0]
            self.assertEqual(feed.property("columns"), 1 if width == 800 else 2)
            cards = [item for item in visual_items(window, "eventCard") if item.y() + item.height() <= feed.height()]
            self.assertGreaterEqual(len(cards), 3)

    def test_header_icons_share_visual_center_and_touch_size(self):
        for width, height in ((800, 480), (1280, 800)):
            backend, engine, window = self.load_design(width, height)
            backend.receive_system({"signal": 82, "battery": {"percentage": 72, "charging": False}})
            QTest.qWait(50)
            icons = visual_items(window, "statusIcon")
            self.assertEqual(len(icons), 4)
            centers = [icon.mapToScene(QPointF(icon.width() / 2, icon.height() / 2)).y() for icon in icons]
            self.assertLess(max(centers) - min(centers), .1)
            image = window.grabWindow()
            painted_heights = []
            for icon in icons:
                self.assertEqual((icon.width(), icon.height()), (46, 46))
                origin = icon.mapToScene(QPointF(0, 0))
                pixels = []
                for y in range(46):
                    for x in range(46):
                        color = image.pixelColor(round(origin.x()) + x, round(origin.y()) + y)
                        if max(color.red(), color.green(), color.blue()) > 130:
                            pixels.append((x, y))
                self.assertTrue(pixels)
                top, bottom = min(y for _, y in pixels), max(y for _, y in pixels)
                self.assertLessEqual(abs((top + bottom + 1) / 2 - 23), 2)
                painted_heights.append(bottom - top + 1)
            self.assertLessEqual(max(painted_heights) - min(painted_heights), 4)

    def test_event_outline_is_rounded_and_selection_is_stronger(self):
        backend, engine, window = self.load_design(1280, 800)
        image = window.grabWindow()
        cards = visual_items(window, "eventCard")
        selected = next(card for card in cards if card.property("chosen"))
        other = next(card for card in cards if not card.property("chosen"))
        for card, expected in ((selected, 2), (other, 1)):
            expression = QQmlExpression(engine.rootContext(), card, "border.width")
            actual, _ = expression.evaluate()
            self.assertFalse(expression.hasError())
            self.assertEqual(actual, expected)
        origin = selected.mapToScene(QPointF(0, 0))
        corner = image.pixelColor(round(origin.x()), round(origin.y()))
        side = image.pixelColor(round(origin.x()) + 1, round(origin.y() + selected.height() / 2))
        self.assertGreater(side.red(), 150)
        self.assertLess(corner.red(), 100)
        self.assertFalse(any(child.width() == 3 and child.height() == selected.height() for child in selected.childItems()))

    def test_distribution_legends_are_centered_compact_and_right_anchored(self):
        for width, height in ((800, 480), (1280, 800)):
            backend, engine, window = self.load_design(width, height)
            window.setProperty("page", 3)
            QTest.qWait(60)
            legends = visual_items(window, "distributionLegend")
            self.assertEqual(len(legends), 2)
            for legend in legends:
                area = legend.parentItem()
                self.assertAlmostEqual(legend.x() + legend.width(), area.width(), places=2)
                self.assertAlmostEqual(legend.y() + legend.height() / 2, area.height() / 2, delta=.5)
            for name in visual_items(window, "legendName"):
                number = next(child for child in name.parentItem().childItems() if child.objectName() == "legendNumber")
                self.assertAlmostEqual(number.x() - name.x() - name.width(), 16 if width == 800 else 32, places=2)

    def test_legend_flags_follow_rendered_capital_center(self):
        for width, height in ((800, 480), (1280, 800)):
            backend, engine, window = self.load_design(width, height)
            window.setProperty("page", 3)
            QTest.qWait(60)
            flags = [flag for flag in visual_items(window, "legendFlag") if flag.isVisible()]
            self.assertTrue(flags)
            image = window.grabWindow()
            for flag in flags:
                self.assertAlmostEqual(flag.y() + flag.height() / 2, flag.parentItem().property("nameInkCenter"), places=2)
                name = next(child for child in flag.parentItem().childItems() if child.objectName() == "legendName")
                name_origin = name.mapToScene(QPointF(0, 0))
                flag_origin = flag.mapToScene(QPointF(0, 0))
                text_rows, flag_rows = [], []
                for y in range(int(name.property("baselineOffset"))):
                    for x in range(int(name.width())):
                        color = image.pixelColor(round(name_origin.x()) + x, round(name_origin.y()) + y)
                        if min(color.red(), color.green(), color.blue()) > 70:
                            text_rows.append(round(name_origin.y()) + y)
                for y in range(int(flag.height())):
                    for x in range(int(flag.width())):
                        color = image.pixelColor(round(flag_origin.x()) + x, round(flag_origin.y()) + y)
                        if abs(color.red() - 18) + abs(color.green() - 20) + abs(color.blue() - 30) > 35:
                            flag_rows.append(round(flag_origin.y()) + y)
                self.assertTrue(text_rows)
                self.assertTrue(flag_rows)
                self.assertAlmostEqual((min(text_rows) + max(text_rows)) / 2,
                                       (min(flag_rows) + max(flag_rows)) / 2, delta=1.5)

    def test_port_tracks_are_equal_despite_different_digit_counts(self):
        for width, height in ((800, 480), (1280, 800)):
            backend, engine, window = self.load_design(width, height)
            counts = [1488, 467, 100003, 8]
            backend.state["services"] = [{"name": name, "count": count} for name, count in
                                        zip(("SSH / 22", "HTTP / 80", "SMB / 445", "SSH / 2222"), counts)]
            backend.stateChanged.emit()
            window.setProperty("page", 3)
            QTest.qWait(60)
            tracks = visual_items(window, "portTrack")
            self.assertEqual(len(tracks), 4)
            self.assertLessEqual(max(track.width() for track in tracks) - min(track.width() for track in tracks), 1)
            values = visual_items(window, "portValue")
            self.assertLessEqual(max(value.width() for value in values) - min(value.width() for value in values), 1)
            for track, count in zip(tracks, counts):
                fill = next(child for child in track.childItems() if child.objectName() == "portFill")
                self.assertAlmostEqual(fill.width() / track.width(), count / max(counts), places=4)

    def test_service_coordinates_and_local_timestamp_presentation(self):
        backend, engine, window = self.load_design(1280, 800)
        values = [item.property("text") for item in visual_items(window, "alarmValue")]
        self.assertIn("22 / SSH", values)
        self.assertIn("50.11° N / 8.68° E", values)
        value = visual_items(window, "displayTimestamp")[0].property("text")
        self.assertIn("2026-10-31 ", value)
        self.assertNotIn("T12:", value)

    def test_map_labels_stay_clear_of_overlays_without_moving_markers(self):
        for width, height in ((800, 480), (1280, 800)):
            backend, engine, window = self.load_design(width, height)
            window.setProperty("page", 1)
            QTest.qWait(120)
            map_item = visual_items(window, "attackMap")[0]
            for marker in visual_items(window, "mapMarker")[:6]:
                if not marker.isVisible():
                    continue
                label = next(child for child in marker.childItems() if child.objectName() == "mapLabel")
                origin = label.mapToItem(map_item, QPointF(0, 0))
                self.assertGreaterEqual(origin.y(), 72)
                self.assertLessEqual(origin.y() + label.height(), height - 128)
                self.assertGreaterEqual(origin.x(), 8)
                self.assertLessEqual(origin.x() + label.width(), width - 8)
                expression = QQmlExpression(engine.rootContext(), map_item, f"project({marker.property('latitude')}, {marker.property('longitude')})")
                point, _ = expression.evaluate()
                self.assertFalse(expression.hasError())
                self.assertAlmostEqual(marker.x() + 24, point.x(), places=2)
                self.assertAlmostEqual(marker.y() + 24, point.y(), places=2)

    def test_histogram_controls_dimensions_and_divider(self):
        for width, height in ((800, 480), (1280, 800)):
            backend, engine, window = self.load_design(width, height)
            window.setProperty("chartExpanded", True)
            QTest.qWait(50)
            controls = visual_items(window, "histogramControl")
            self.assertEqual(len(controls), 5)
            for control in controls:
                self.assertAlmostEqual(control.width(), 64)
                self.assertAlmostEqual(control.height(), 52)
            divider = visual_items(window, "histogramDivider")[0]
            self.assertEqual(divider.width(), 1)
            self.assertGreater(divider.x(), controls[-2].x() + controls[-2].width())
            self.assertLess(divider.x(), controls[-1].x())
            control = controls[-1]
            point = control.mapToScene(QPointF(control.width() / 2, control.height() / 2)).toPoint()
            QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=point)
            self.assertFalse(window.property("chartExpanded"))

    def test_native_map_projection_and_bezier_motion(self):
        backend, engine, window = self.load_design()
        window.setProperty("page", 1)
        QTest.qWait(120)
        map_item = visual_items(window, "attackMap")[0]
        expression = QQmlExpression(engine.rootContext(), map_item, "project(80, -180)")
        point, _ = expression.evaluate()
        self.assertFalse(expression.hasError())
        image = visual_items(window, "worldMapImage")[0]
        self.assertAlmostEqual(point.x(), (map_item.width() - image.property("paintedWidth")) / 2, places=3)
        self.assertAlmostEqual(point.y(), (map_item.height() - image.property("paintedHeight")) / 2, places=3)
        flight = visual_items(window, "attackFlight")[0]
        expression = QQmlExpression(engine.rootContext(), flight, "start(Qt.point(100, 300), Qt.point(600, 200), true, '#e20074')")
        expression.evaluate()
        self.assertFalse(expression.hasError())
        QTest.qWait(300)
        self.assertTrue(flight.property("active"))
        progress = flight.property("travel")
        source = flight.property("origin")
        target = flight.property("destination")
        control = flight.property("control")
        expected_x = (1 - progress) ** 2 * source.x() + 2 * (1 - progress) * progress * control.x() + progress ** 2 * target.x()
        expected_y = (1 - progress) ** 2 * source.y() + 2 * (1 - progress) * progress * control.y() + progress ** 2 * target.y()
        self.assertAlmostEqual(flight.property("beamX"), expected_x, places=3)
        self.assertAlmostEqual(flight.property("beamY"), expected_y, places=3)
        beam = next(child for child in flight.childItems() if child.objectName() == "attackBeam")
        self.assertAlmostEqual(beam.x() + beam.width() / 2, expected_x, places=3)
        self.assertAlmostEqual(beam.y() + beam.height() / 2, expected_y, places=3)
        self.assertEqual(beam.property("color").name(), "#e20074")
        self.assertLess(flight.property("beamY"), source.y())
        QTest.qWait(1100)
        self.assertFalse(flight.property("active"))
        self.assertFalse(flight.isVisible())

    def test_boot_preview_and_status_popovers(self):
        backend, engine, window = self.load_design()
        window.setProperty("startupVisible", True)
        QTest.qWait(80)
        self.assertTrue(visual_items(window, "startupOverlay")[0].isVisible())
        expression = QQmlExpression(engine.rootContext(), window, "showStatus('BATTERY / UPS', 'Charging / 86%')")
        expression.evaluate()
        self.assertFalse(expression.hasError())
        self.assertEqual(window.property("statusTitle"), "BATTERY / UPS")
        self.assertEqual(window.property("statusText"), "Charging / 86%")

    def test_map_effect_cap_missing_destination_and_hidden_stop(self):
        backend, engine, window = self.load_design()
        window.setProperty("page", 1)
        QTest.qWait(120)
        map_item = visual_items(window, "attackMap")[0]
        self.assertEqual(len(visual_items(window, "attackFlight")), 3)
        backend.pings.emit([normalize(hit(number, geoip={"latitude": 38, "longitude": -97})).variant() for number in range(100)])
        self.assertEqual(map_item.property("activeFlights"), 3)
        self.assertTrue(all(not flight.property("destinationKnown") for flight in visual_items(window, "attackFlight")))
        window.setProperty("animationsEnabled", False)
        self.assertEqual(map_item.property("activeFlights"), 0)
        backend.pings.emit(backend.model.rows)
        self.assertEqual(map_item.property("activeFlights"), 0)
        window.setProperty("animationsEnabled", True)
        backend.pings.emit(backend.model.rows)
        self.assertEqual(map_item.property("activeFlights"), 3)
        window.setProperty("page", 0)
        QTest.qWait(50)
        self.assertEqual(visual_items(window, "attackFlight"), [])

    def test_map_fullscreen_and_timestamp_size(self):
        for width, height in ((800, 480), (1280, 800)):
            backend, engine, window = self.load_design(width, height)
            window.setProperty("page", 1)
            QTest.qWait(120)
            map_item = visual_items(window, "attackMap")[0]
            self.assertEqual((map_item.width(), map_item.height()), (width, height))
            labels = visual_items(window, "mapTimestamp")
            self.assertEqual(len(labels), 2 if width == 800 else 3)
            self.assertTrue(all(item.property("font").pixelSize() == 18 for item in labels))

    def test_missing_source_geolocation_does_not_animate_or_break_details(self):
        backend, engine, window = self.load_design()
        errors = []
        previous = qInstallMessageHandler(lambda _kind, _context, message: errors.append(message))
        try:
            partial = normalize(hit(1, geoip={})).variant()
            backend.receive_data({"events": [partial], "fresh": [partial], "eventsOk": True})
            window.setProperty("page", 1)
            QTest.qWait(120)
            backend.pings.emit([partial])
            map_item = visual_items(window, "attackMap")[0]
            self.assertEqual(map_item.property("activeFlights"), 0)
            self.assertTrue(all(not marker.isVisible() for marker in visual_items(window, "mapMarker")))
            window.setProperty("page", 0)
            QTest.qWait(50)
        finally:
            qInstallMessageHandler(previous)
        self.assertEqual(errors, [])

    def test_model_moves_and_removes_without_reset(self):
        model = EventModel()
        rows = [normalize(hit(number)).variant() for number in range(3)]
        resets = Mock()
        model.modelReset.connect(resets)
        model.update(rows)
        model.update([rows[2], rows[0]])
        self.assertEqual([row["identity"] for row in model.rows], [rows[2]["identity"], rows[0]["identity"]])
        self.assertEqual(model.rowCount(), 2)
        resets.assert_not_called()

    def test_stale_timeframe_response_does_not_overwrite_selection(self):
        backend = Backend("normal")
        backend.selectTimeframe("15m")
        backend.receive_data({"statsOk": True, "timeframe": "1h", "counts": {"1h": 5}})
        self.assertEqual(backend.state["counts"], {})
        self.assertEqual(backend.state["timeframe"], "15m")
        self.assertEqual(backend.state["statsRevision"], 0)
        backend.receive_data({"statsError": "Old request failed", "statsTimeframe": "1h"})
        self.assertEqual(backend.state["statsError"], "Refreshing selected timeframe")
        backend.close()

    def test_queued_snapshots_and_actions_are_bounded(self):
        worker = Worker()
        delivered = Mock()
        worker.snapshot.connect(delivered)
        worker.publish({"a": 1})
        worker.publish({"a": 2})
        delivered.assert_called_once()
        backend = Backend("normal")
        for value in range(20, 100):
            backend.system_worker.enqueue("brightness", value)
        self.assertEqual(len(backend.system_worker.actions), 1)
        backend.close()

    def test_fixture_never_constructs_real_clients_or_hardware(self):
        with patch("modules.backend.Elasticsearch") as client, patch("modules.backend.SystemSampler") as sampler, patch("modules.backend.control") as helper:
            backend = Backend("low-battery")
            backend.start()
            backend.action("poweroff")
            QTest.qWait(1200)
            backend.close()
            client.assert_not_called()
            sampler.assert_not_called()
            helper.assert_not_called()
            self.assertIn("simulated", backend.state["actionMessage"])
            self.assertLessEqual(backend.events.rowCount(), 200)

    def test_navigation_does_not_wait_for_acquisition(self):
        backend = Backend("normal")
        with patch("modules.backend.Acquisition.statistics", side_effect=lambda _: time.sleep(1)) as stats:
            start = time.monotonic()
            backend.selectTimeframe("24h")
            elapsed = time.monotonic() - start
        self.assertLess(elapsed, 0.1)
        stats.assert_not_called()
        backend.close()

    def test_actual_input_remains_responsive_during_blocked_search(self):
        entered = threading.Event()
        client = Mock()
        client.info.return_value = {"version": {"number": "9.5.4"}}
        client.open_point_in_time.return_value = {"id": "pit"}
        def slow_search(**_arguments):
            entered.set()
            time.sleep(0.5)
            return {"hits": {"hits": []}}
        client.search.side_effect = slow_search
        with patch("modules.backend.Elasticsearch", return_value=client), patch("modules.backend.SystemSampler") as sampler:
            sampler.return_value.sample.return_value = {"battery": {}, "history": []}
            sampler.return_value.network.return_value = {}
            backend = Backend()
            backend.state["fixture"] = True
            engine = QQmlApplicationEngine()
            context = engine.rootContext()
            for name, value in (("backend", backend), ("fixtureWidth", 800), ("fixtureHeight", 480), ("uiFontFamily", self.application.font().family()), ("uiMonoFamily", self.application.font().family())):
                context.setContextProperty(name, value)
            engine.load(QUrl.fromLocalFile(str(ROOT / "qml" / "Main.qml")))
            window = engine.rootObjects()[0]
            window.setProperty("startupVisible", False)
            window.setProperty("startupComplete", True)
            QTest.qWait(50)
            backend.start()
            try:
                self.assertTrue(entered.wait(2))
                started = time.monotonic()
                QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(240, 444))
                self.assertEqual(window.property("page"), 1)
                self.assertLess(time.monotonic() - started, 0.1)
            finally:
                backend.close()
                engine.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_old_elasticsearch_version_is_reported_without_searching(self):
        client = Mock()
        client.info.return_value = {"version": {"number": "8.18.1"}}
        with patch("modules.backend.Elasticsearch", return_value=client), patch("modules.backend.SystemSampler") as sampler:
            sampler.return_value.sample.return_value = {"battery": {}, "history": []}
            sampler.return_value.network.return_value = {}
            backend = Backend()
            backend.start()
            QTest.qWait(200)
            backend.close()
            client.search.assert_not_called()
            self.assertIn("Elasticsearch 9 required", backend.state["eventsError"])

    def test_all_views_load_at_both_resolutions_without_qml_warnings(self):
        errors = []
        previous = qInstallMessageHandler(lambda _kind, _context, message: errors.append(message))
        try:
            for width, height in ((800, 480), (1280, 800)):
                backend = Backend("normal")
                backend.start()
                engine = QQmlApplicationEngine()
                for name, value in (("backend", backend), ("fixtureWidth", width), ("fixtureHeight", height), ("uiFontFamily", self.application.font().family()), ("uiMonoFamily", self.application.font().family())):
                    engine.rootContext().setContextProperty(name, value)
                engine.load(QUrl.fromLocalFile(str(ROOT / "qml" / "Main.qml")))
                self.assertTrue(engine.rootObjects(), errors)
                window = engine.rootObjects()[0]
                self.assertIsInstance(window, QQuickWindow)
                QTest.qWait(250)
                for page in range(5):
                    window.setProperty("page", page)
                    QTest.qWait(100)
                self.assertEqual(window.grabWindow().width(), width)
                controls = visual_items(window, "navigationButton")
                self.assertTrue(controls)
                self.assertTrue(all(control.height() >= (52 if width == 800 else 60) for control in controls if control.isVisible()))
                self.assertFalse(window.property("presentation"))
                timer = window.findChild(QObject, "presentationTimer")
                self.assertIsNotNone(timer)
                timer.setProperty("interval", 30)
                window.setProperty("presentation", True)
                QTest.qWait(80)
                window.setProperty("presentationPaused", True)
                paused_page = window.property("page")
                QTest.qWait(80)
                self.assertEqual(window.property("page"), paused_page)
                window.setProperty("presentation", False)
                backend.selectEvent(backend.model.rows[0]["identity"])
                QTest.qWait(100)
                backend.close()
                window.close()
                engine.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        finally:
            qInstallMessageHandler(previous)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
