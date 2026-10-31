"""Linux telemetry and conservative battery policies; no GUI dependencies."""

from collections import deque
from dataclasses import dataclass
import ipaddress
import json
import logging
import math
from pathlib import Path
import subprocess
import time
from typing import Any

import dns.resolver
from dns.exception import DNSException

HELPER = "/usr/local/libexec/tpotmobile-control"


def command(arguments: list[str], timeout: float = 3) -> str:
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=True)
    except subprocess.CalledProcessError as error:
        raise OSError(f"{arguments[0]} failed: {error.stderr.strip()}") from error
    return result.stdout.strip()


def control(action: str, value: int | None = None) -> dict[str, Any]:
    arguments = ["/usr/bin/sudo", "-n", HELPER, action]
    if value is not None:
        arguments.append(str(value))
    return json.loads(command(arguments, timeout=5))


@dataclass(frozen=True)
class Battery:
    voltage: float
    current: float
    watts: float
    percentage: float
    charging: bool | None

    @classmethod
    def read(cls, device: Any) -> "Battery":
        voltage = device.getBusVoltage_V()
        current = device.getCurrent_mA() / 1000
        watts = device.getPower_W()
        if not all(math.isfinite(value) for value in (voltage, current, watts)):
            raise ValueError("Non-finite UPS measurement")
        if not 5.5 <= voltage <= 8.8 or abs(current) >= 3.2 or not 0 <= watts <= 30:
            raise ValueError("UPS measurement outside the supported calibration range")
        percentage = max(0.0, min(100.0, (voltage - 6.0) / 2.4 * 100))
        # Waveshare UPS HAT: negative current means battery discharge.
        charging = None if abs(current) < 0.02 else current > 0
        return cls(voltage, current, watts, percentage, charging)

    def variant(self) -> dict[str, Any]:
        return {
            "voltage": self.voltage, "current": self.current, "watts": self.watts,
            "percentage": self.percentage, "charging": self.charging,
        }


class PowerPolicy:
    def __init__(self) -> None:
        self.mode: bool | None = None
        self.manual = 100
        self.override = False
        self.low_samples = 0
        self.shutdown_requested = False

    def set_manual(self, percentage: int) -> int:
        if not 5 <= percentage <= 100:
            raise ValueError("Brightness must be between 5 and 100 percent")
        self.manual = percentage
        self.override = True
        return percentage

    def update(self, battery: Battery | None) -> tuple[int | None, bool]:
        if battery is None or battery.charging is None:
            self.low_samples = 0
            return None, False
        transition = battery.charging != self.mode
        if transition:
            if self.mode is not None:
                self.override = False
            self.mode = battery.charging
        self.low_samples = self.low_samples + 1 if battery.charging is False and battery.percentage < 10 else 0
        shutdown = self.low_samples >= 3 and not self.shutdown_requested
        if shutdown:
            self.shutdown_requested = True
        brightness = self.manual if self.override or battery.charging else min(self.manual, 60)
        return brightness, shutdown


class SystemSampler:
    def __init__(self) -> None:
        self.device: Any = None
        self.previous_cpu: tuple[int, int] | None = None
        self.history: deque[tuple[float, float]] = deque(maxlen=120)
        self.policy = PowerPolicy()
        self.last_brightness: int | None = None
        self.last_target: int | None = None

    def sample(self) -> dict[str, Any]:
        errors = []
        cutoff = time.monotonic() - 600
        while self.history and self.history[0][0] < cutoff:
            self.history.popleft()
        data: dict[str, Any] = {"battery": {}, "history": [watts for _, watts in self.history]}
        try:
            cpu = [int(value) for value in Path("/proc/stat").read_text().splitlines()[0].split()[1:9]]
            total, idle = sum(cpu), cpu[3] + cpu[4]
            if self.previous_cpu and total > self.previous_cpu[0]:
                data["cpu"] = 100 * (1 - (idle - self.previous_cpu[1]) / (total - self.previous_cpu[0]))
            self.previous_cpu = total, idle
            memory = {line.split(":")[0]: int(line.split()[1])
                      for line in Path("/proc/meminfo").read_text().splitlines()}
            data["ramUsed"] = (memory["MemTotal"] - memory["MemAvailable"]) / 1024
            data["ramTotal"] = memory["MemTotal"] / 1024
            data["temperature"] = float(Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000
        except (OSError, ValueError, KeyError, IndexError) as error:
            logging.warning("System telemetry unavailable: %s", error)
            errors.append(f"System telemetry: {error}")
        battery = None
        try:
            if self.device is None:
                from modules.ina219_module import INA219
                self.device = INA219(addr=0x42)
            battery = Battery.read(self.device)
            self.history.append((time.monotonic(), battery.watts))
            data["battery"] = battery.variant()
            data["history"] = [watts for _, watts in self.history]
        except (OSError, ValueError) as error:
            logging.warning("UPS telemetry unavailable: %s", error)
            errors.append(f"UPS: {error}")
        brightness, shutdown = self.policy.update(battery)
        if brightness is not None and brightness != self.last_target:
            try:
                result = control("brightness", brightness)
                self.last_brightness = result["brightness"]
                self.last_target = brightness
            except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
                logging.warning("Brightness control failed: %s", error)
                errors.append(f"Brightness: {error}")
        data["brightness"] = self.last_brightness
        data["shutdown"] = shutdown
        data["error"] = "; ".join(errors)
        return data

    def manual_brightness(self, percentage: int) -> dict[str, Any]:
        if not 5 <= percentage <= 100:
            raise ValueError("Brightness must be between 5 and 100 percent")
        result = control("brightness", percentage)
        self.policy.set_manual(percentage)
        self.last_brightness = result["brightness"]
        self.last_target = percentage
        return result

    def network(self) -> dict[str, Any]:
        errors = []
        data: dict[str, Any] = {}
        try:
            routes = json.loads(command(["/usr/sbin/ip", "-j", "route", "show", "default"]))
            interface = next((route["dev"] for route in routes if "dev" in route), None)
            if interface:
                addresses = json.loads(command(["/usr/sbin/ip", "-j", "address", "show", "dev", interface]))
                data["localIp"] = next(
                    (entry["local"] for address in addresses for entry in address.get("addr_info", [])
                     if entry.get("family") == "inet"), "No IPv4 address",
                )
            else:
                data["localIp"] = "No default route"
            wifi = command(["/usr/bin/nmcli", "-t", "-f", "IN-USE,SIGNAL", "device", "wifi", "list", "--rescan", "no"])
            data["signal"] = next((int(line.split(":")[1]) for line in wifi.splitlines() if line.startswith("*:")), None)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            logging.warning("Network status unavailable: %s", error)
            errors.append(f"Network: {error}")
        try:
            resolver = dns.resolver.Resolver(configure=False)
            resolver.nameservers = ["208.67.222.222"]
            answer = resolver.resolve("myip.opendns.com", "A", lifetime=2)
            data["externalIp"] = str(ipaddress.ip_address(str(answer[0])))
        except (OSError, ValueError, DNSException) as error:
            logging.warning("Public IP unavailable: %s", error)
            errors.append(f"Public IP: {error}")
        try:
            data["containers"] = control("status")["containers"]
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            logging.warning("Container status unavailable: %s", error)
            errors.append(f"Containers: {error}")
        data["networkError"] = "; ".join(errors)
        return data

    def close(self) -> None:
        if self.device is not None:
            self.device.bus.close()
