"""Bounded, read-only Elasticsearch acquisition for the mobile display."""

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import math
from typing import Any, Callable, Mapping

from elasticsearch import NotFoundError

TIMEFRAMES = {"1m": "1s", "15m": "15s", "1h": "1m", "24h": "24m"}
MAX_EVENTS = 200
MAX_PAGES = 10
PAGE_SIZE = 100
SOURCE_FIELDS = [
    "@timestamp", "type", "src_ip", "dest_port", "geoip", "geoip_ext",
    "t-pot_hostname", "ip_rep", "input", "username", "password", "msg",
    "payload_printable", "data_type", "event_type", "http_user_agent", "http.url",
    "headers", "user-agent_os", "user-agent_browser", "user_agent_browser",
    "path", "ipp_query.operation", "data", "info", "action", "request_uri",
    "browser_family", "browser_version", "url", "plugin", "request",
]
DETAIL_FIELDS = {
    "input": "Command", "payload_printable": "Payload", "username": "Username",
    "password": "Password", "msg": "Request", "data_type": "Data type",
    "event_type": "Event type", "http_user_agent": "User agent", "http.url": "URL",
    "headers.user-agent": "User agent", "user-agent_os": "OS",
    "user-agent_browser": "Browser", "user_agent_browser": "Browser",
    "path": "Path", "ipp_query.operation": "IPP operation", "data": "Data",
    "info": "Info", "action": "Action", "request_uri": "Request URI",
    "browser_family": "Browser", "browser_version": "Browser version",
    "url": "URL", "plugin": "Plugin", "request.requestURI": "Request URI",
    "request.userAgent": "User agent",
}
PORTS = {
    20: "FTP", 21: "FTP", 22: "SSH", 2222: "SSH", 23: "TELNET", 2223: "TELNET",
    25: "EMAIL", 110: "EMAIL", 143: "EMAIL", 993: "EMAIL", 995: "EMAIL",
    53: "DNS", 80: "HTTP", 81: "HTTP", 8080: "HTTP", 8888: "HTTP",
    443: "HTTPS", 8443: "HTTPS", 161: "SNMP", 445: "SMB", 631: "PRINTER",
    9100: "PRINTER", 1433: "DATABASE", 1521: "DATABASE", 3306: "DATABASE",
    3389: "RDP", 5060: "VOIP", 5061: "VOIP", 5555: "ANDROID", 5900: "VNC",
    6379: "REDIS", 2575: "MEDICAL", 11112: "MEDICAL",
}


def field(source: Mapping[str, Any], name: str) -> Any:
    if name in source:
        return source[name]
    value: Any = source
    for part in name.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def text(value: Any, limit: int = 1000) -> str:
    if value is None:
        return ""
    rendered = str(value).replace("\x00", "")
    return rendered if len(rendered) <= limit else rendered[:limit] + " [truncated]"


def coordinate(value: Any, limit: float) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and abs(number) <= limit else None


@dataclass(frozen=True)
class Event:
    identity: str
    timestamp: str
    honeypot: str
    country: str
    country_code: str
    source_ip: str
    protocol: str
    latitude: float | None
    longitude: float | None
    details: tuple[tuple[str, str], ...]
    destination_latitude: float | None = None
    destination_longitude: float | None = None

    def variant(self) -> dict[str, Any]:
        return {
            "identity": self.identity, "timestamp": self.timestamp,
            "honeypot": self.honeypot, "country": self.country,
            "countryCode": self.country_code, "sourceIp": self.source_ip,
            "protocol": self.protocol,
            "latitude": self.latitude, "longitude": self.longitude,
            "details": [{"label": label, "value": value} for label, value in self.details],
            "reputation": dict(self.details).get("Reputation", "Unknown"),
            "username": dict(self.details).get("Username", ""),
            "password": dict(self.details).get("Password", ""),
            "command": next((value for label, value in self.details if label in ("Command", "Payload", "Request", "Request URI", "Data", "URL")), ""),
            "destinationLatitude": self.destination_latitude,
            "destinationLongitude": self.destination_longitude,
        }


def normalize(hit: Mapping[str, Any]) -> Event:
    source = hit.get("_source")
    if not isinstance(source, Mapping):
        raise ValueError("Event has no object _source")
    raw_time = text(source.get("@timestamp"))
    try:
        event_time = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Event has an invalid timestamp") from error
    if event_time.tzinfo is None:
        raise ValueError("Event timestamp has no timezone")
    code = text(field(source, "geoip.country_code2")).lower()
    if len(code) != 2 or not code.isascii() or not code.isalpha():
        code = ""
    port = source.get("dest_port")
    if isinstance(port, (str, int)) and not isinstance(port, bool):
        try:
            protocol = PORTS.get(int(port), text(port, 20))
        except ValueError:
            protocol = "OTHER"
    else:
        protocol = "OTHER"
    honeypot = text(source.get("type"), 100) or "Unknown"
    if honeypot in ("Beelzebub", "Galah"):
        protocol = "SSH / LLM" if honeypot == "Beelzebub" else "HTTP / LLM"
    details = [
        ("Timestamp", event_time.astimezone().isoformat(timespec="seconds")),
        ("Country", text(field(source, "geoip.country_name")) or "Unknown"),
        ("Region", text(field(source, "geoip.region_name"))),
        ("City", text(field(source, "geoip.city_name"))),
        ("Source IP", text(source.get("src_ip"))),
        ("AS organization", text(field(source, "geoip.as_org"))),
        ("Reputation", text(source.get("ip_rep"))),
        ("Port", text(port)), ("Honeypot", honeypot),
        ("Host", text(source.get("t-pot_hostname"))),
    ]
    details.extend((label, text(field(source, key))) for key, label in DETAIL_FIELDS.items())
    return Event(
        identity=f"{hit['_index']}/{hit['_id']}",
        timestamp=event_time.astimezone(timezone.utc).isoformat(),
        honeypot=honeypot,
        country=text(field(source, "geoip.country_name")) or "Unknown",
        country_code=code, source_ip=text(source.get("src_ip")),
        protocol=protocol or "OTHER",
        latitude=coordinate(field(source, "geoip.latitude"), 90),
        longitude=coordinate(field(source, "geoip.longitude"), 180),
        details=tuple((label, value) for label, value in details if value),
        destination_latitude=coordinate(field(source, "geoip_ext.latitude"), 90),
        destination_longitude=coordinate(field(source, "geoip_ext.longitude"), 180),
    )


class EventBuffer:
    def __init__(self) -> None:
        self.events: dict[str, Event] = {}
        self.seen: OrderedDict[str, None] = OrderedDict()

    def merge(self, incoming: list[Event]) -> tuple[list[Event], list[Event]]:
        fresh = []
        for event in incoming:
            if event.identity not in self.seen:
                fresh.append(event)
            self.seen[event.identity] = None
            self.seen.move_to_end(event.identity)
            self.events[event.identity] = event
        while len(self.seen) > 5000:
            self.seen.popitem(last=False)
        ordered = sorted(self.events.values(), key=lambda event: (event.timestamp, event.identity), reverse=True)
        ordered = ordered[:MAX_EVENTS]
        self.events = {event.identity: event for event in ordered}
        return ordered, fresh


class Acquisition:
    def __init__(self, client: Any, cancelled: Callable[[], bool] = lambda: False) -> None:
        self.client = client
        self.cancelled = cancelled
        self.pit: str | None = None
        self.watermark: datetime | None = None
        self.buffer = EventBuffer()
        self.last_stats: dict[str, Any] = {}

    @staticmethod
    def query() -> dict[str, Any]:
        # Identify events by source IP, rather than an obsolete honeypot-name whitelist.
        return {"bool": {
            "filter": [{"exists": {"field": "src_ip"}}, {"exists": {"field": "type"}}],
            "must_not": [{"terms": {"type.keyword": ["Suricata", "P0f", "Fatt"]}}],
        }}

    def poll(self, now: datetime) -> dict[str, Any]:
        if self.cancelled():
            raise InterruptedError("Acquisition cancelled")
        if self.pit is not None:
            try:
                self.client.close_point_in_time(id=self.pit)
            except NotFoundError:
                logging.info("Previous Elasticsearch snapshot already expired")
            self.pit = None
        # A PIT is immutable: each poll needs a fresh one to see newly indexed events.
        self.pit = self.client.open_point_in_time(index="logstash-*", keep_alive="1m")["id"]
        lower = (self.watermark or now - timedelta(seconds=60)) - timedelta(seconds=10)
        after = None
        collected = []
        truncated = False
        invalid = 0
        for page in range(MAX_PAGES):
            if self.cancelled():
                raise InterruptedError("Acquisition cancelled")
            query = self.query()
            query["bool"]["filter"].append({"range": {"@timestamp": {
                "gte": lower.isoformat(), "lte": now.isoformat(),
            }}})
            arguments: dict[str, Any] = {
                "pit": {"id": self.pit, "keep_alive": "1m"},
                "query": query, "size": PAGE_SIZE, "track_total_hits": False,
                "sort": [{"@timestamp": "desc"}, {"_shard_doc": "desc"}],
                "source": {"includes": SOURCE_FIELDS},
                "allow_partial_search_results": False,
                "timeout": "2s",
            }
            if after is not None:
                arguments["search_after"] = after
            response = self.client.search(**arguments)
            if response.get("timed_out"):
                raise TimeoutError("Elasticsearch event query timed out")
            self.pit = response.get("pit_id", self.pit)
            hits = response["hits"]["hits"]
            for hit in hits:
                try:
                    collected.append(normalize(hit))
                except (ValueError, KeyError) as error:
                    invalid += 1
                    logging.warning("Invalid event %s: %s", hit.get("_id"), error)
            if len(hits) < PAGE_SIZE:
                break
            after = hits[-1]["sort"]
            truncated = page == MAX_PAGES - 1
        self.watermark = now
        events, fresh = self.buffer.merge(collected)
        return {
            "events": [event.variant() for event in events],
            "fresh": [event.variant() for event in fresh[:32]],
            "notice": "Live view capped at 1,000 hits per poll; stored events are unaffected." if truncated
                      else f"{invalid} malformed events skipped; see journal." if invalid else "",
        }

    def statistics(self, timeframe: str) -> dict[str, Any]:
        if timeframe not in TIMEFRAMES:
            raise ValueError("Unsupported timeframe")
        response = self.client.search(
            index="logstash-*", size=0, query=self.query(), track_total_hits=False,
            allow_partial_search_results=False,
            timeout="2s",
            aggs={
                "counts": {"filters": {"filters": {
                    duration: {"range": {"@timestamp": {"gte": f"now-{duration}", "lte": "now"}}}
                    for duration in TIMEFRAMES
                }}},
                "selected": {
                    "filter": {"range": {"@timestamp": {"gte": f"now-{timeframe}", "lte": "now"}}},
                    "aggs": {
                        "timeline": {"date_histogram": {
                            "field": "@timestamp", "fixed_interval": TIMEFRAMES[timeframe],
                            "min_doc_count": 0,
                            "extended_bounds": {"min": f"now-{timeframe}", "max": "now"},
                        }},
                        "countries": {
                            "terms": {"field": "geoip.country_name.keyword", "size": 4},
                            "aggs": {"code": {"terms": {"field": "geoip.country_code2.keyword", "size": 1}}},
                        },
                        "honeypots": {"terms": {"field": "type.keyword", "size": 8}},
                        "services": {"terms": {"field": "dest_port", "size": 4}},
                    },
                },
            },
        )
        if response.get("timed_out"):
            raise TimeoutError("Elasticsearch statistics query timed out")
        data = response["aggregations"]
        selected = data["selected"]
        return {
            "timeframe": timeframe,
            "counts": {key: value["doc_count"] for key, value in data["counts"]["buckets"].items()},
            "timeline": [bucket["doc_count"] for bucket in selected["timeline"]["buckets"]],
            "timelineTimes": [bucket["key"] for bucket in selected["timeline"]["buckets"]],
            "countries": [{"name": bucket["key"], "count": bucket["doc_count"],
                           "code": text(bucket["code"]["buckets"][0]["key"]).lower() if bucket["code"]["buckets"] else ""}
                          for bucket in selected["countries"]["buckets"]],
            "honeypots": [{"name": bucket["key"], "count": bucket["doc_count"]}
                         for bucket in selected["honeypots"]["buckets"]],
            "services": [{"name": f"{PORTS.get(int(bucket['key']), 'OTHER')} / {bucket['key']}", "count": bucket["doc_count"]}
                         for bucket in selected["services"]["buckets"]],
        }

    def close(self) -> None:
        try:
            if self.pit:
                self.client.close_point_in_time(id=self.pit)
        finally:
            self.client.close()
