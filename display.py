from collections import deque
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from logging import exception
from modules.ina219_module import INA219
from tzlocal import get_localzone
import dns.resolver
import math
import netifaces
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"  # Suppress Pygame welcome message
import pygame
import pytz
import random
import re
import socket
import subprocess
import sys
import time

es = Elasticsearch('http://127.0.0.1:64298')
es_index = "logstash-*"
version = 'T-Pot Mobile v2.0'
local_tz = get_localzone()

# Some global settings
wifi_if = "wlan0"

# External IP Cache
ext_ip_cache = None
last_ext_ip_check = 0
EXT_IP_TTL = 300  # seconds (5 minutes)

# Counter, indices, etc.
circle_counter = 0
active_pings = []
bar_space, bar_depth = 1, 4
last_three_events = []
network_fails = 0

# Pygame Settings
os.environ['SDL_AUDIODRIVER'] = 'dummy'  # Prevent sound support
pygame.init()

# Get list of supported fullscreen modes
modes = pygame.display.list_modes()

# Check if there are any supported modes
if modes != -1 and len(modes) > 0:
    first_mode = modes[0]
    width, height = first_mode
else:
    print("No supported resolutions found. Assuming 800 x 480.")
    width, height = 800, 480

# Use the tools/map_builder.py to create correctly projected Mercator maps
#width=800
#height=480
if width == 800 and height == 480:
    background_image = "images/tpot_800480.png"
    map_image = "images/map_800477.png"
    font_size = 34
    button_font_size = 36
    info_font_size = 28
    map_font_size = 28
    axis_font_size = 22
    button_width, button_height = 120, 120
    button_spacing = 20
    circle_radius = 6
    chart_surface_height = 170
    event_surface_height = 195
    event_horizontal_offset = 175
    latrange_min = -60
    latrange_max = 80
elif width == 1280 and height == 800:
    background_image = "images/tpot_1280800.png"
    map_image = "images/map_1280794.png"
    font_size = 44
    button_font_size = 40
    info_font_size = 32
    map_font_size = 38
    axis_font_size = 32
    button_width, button_height = 160, 160
    button_spacing = 40
    circle_radius = 8
    chart_surface_height = 270
    event_surface_height = 430
    event_horizontal_offset = 230
    latrange_min = -64
    latrange_max = 80
else:
    print("Error. Resolution not supported.")
    exit()

fps = 60

# Colors
alpha = 100
magenta = (226, 0, 116)
green = (0, 255, 0)
orange = (255, 165, 0)
dark_orange = (205, 102, 0)
yellow = (255, 255, 0)
white = (255, 255, 255)
red = (255, 0, 0)
dark_red = (139, 0, 0)
grey = (75, 75, 75)
stats_surface_background = (75, 75, 75, alpha)
system_surface_background = (75, 75, 75, alpha)
color_bar_chart = (226, 0, 116, 200)

#### Buttons
button_font = pygame.font.Font(None, button_font_size)
# Buttons - Calculate button positions to be centered both horizontally and vertically
total_buttons_width = 4 * button_width + 3 * button_spacing
first_button_x_position = (width - total_buttons_width) / 2  # Adjust X position to center buttons horizontally
buttons_y_position = (height - button_height) / 2  # Center vertically
# Creating Rect objects for buttons
cancel_button_rect = pygame.Rect(first_button_x_position, buttons_y_position, button_width, button_height)
mode_button_rect = pygame.Rect(first_button_x_position + button_width + button_spacing, buttons_y_position,
                               button_width, button_height)
reboot_button_rect = pygame.Rect(first_button_x_position + 2 * (button_width + button_spacing), buttons_y_position,
                                 button_width, button_height)
poweroff_button_rect = pygame.Rect(first_button_x_position + 3 * (button_width + button_spacing), buttons_y_position,
                                   button_width, button_height)
#### /Buttons

# ES honeypot stats relative timeframes
last = {"1m", "15m", "1h", "24h"}
timeframes = [
    {"duration": "1m", "breakdown": "1s", "color": magenta},
    {"duration": "15m", "breakdown": "15s", "color": magenta},
    {"duration": "1h", "breakdown": "1m", "color": white},
    {"duration": "24h", "breakdown": "24m", "color": magenta}
]

# All the honeypot types
honeypot_types = [
    "Adbhoney", "Beelzebub", "Ciscoasa", "CitrixHoneypot", "ConPot",
    "Cowrie", "Ddospot", "Dicompot", "Dionaea", "ElasticPot",
    "Endlessh", "Galah", "Glutton", "Go-pot", "H0neytr4p", "Hellpot", "Heralding", 
    "Honeyaml", "Honeytrap", "Honeypots", "Log4pot", "Ipphoney", "Mailoney", 
    "Medpot", "Miniprint", "Redishoneypot", "Sentrypeer", "Tanner", "Wordpot"
]

# Color Codes for Attack Map
service_rgb = {
'ANDROID': (64, 255, 128),
'DATABASE': (0, 128, 0),
'DNS': (0, 153, 204),
'EMAIL': (128, 255, 0),
'FTP': (255, 0, 0),
'HTTP': (0, 0, 255),
'HTTPS': (0, 128, 255),
'MEDICAL': (255, 0, 255),
'PRINTER': (1, 205, 151),
'REDIS': (255, 46, 0),
'RDP': (255, 0, 96),
'VOIP': (255, 192, 255),
'SMB': (191, 0, 255),
'SNMP': (128, 0, 255),
'SSH': (255, 165, 80),
'TELNET': (255, 255, 0),
'VNC': (0, 0, 255),
'OTHER': (255, 255, 255)
# 'Red-Orange' : (255, 139, 0),
# 'Yellow-Green' : (51, 204, 0),
# 'Green-Cyan' : (0, 153, 204),
# 'Blue': (0, 0, 238),
# 'Violet-Red' : (143, 0, 62),
# 'Magenta-Cyan' : (0, 197, 255),
# 'Violet-White': (142, 36, 170),
# 'Pink' : (244, 192, 203),
# 'Red-Magenta' : (211, 0, 95)
}

def init_ina219():
    battery_device_address = 0x42
    try:
        ina219 = INA219(addr=battery_device_address)
    except FileNotFoundError:
        print("I2C bus not found. Please check your configuration.")
        ina219 = None
    except Exception as e:
        print("UPS HAT not found.")
        ina219 = None
    return ina219


def get_battery_info(device):
    ina219 = device
    if ina219 is None:
        battery = {
            "bus_voltage": "n/a",
            "shunt_voltage": "n/a",
            "current": "n/a",
            "power": "n/a",
            "percentage": "n/a",
        }

    else:
        try:
            bus_voltage = ina219.getBusVoltage_V()  # voltage on V- (load side)
            shunt_voltage = ina219.getShuntVoltage_mV() / 1000  # voltage between V+ and V- across the shunt
            current = ina219.getCurrent_mA()  # current in mA
            power = ina219.getPower_W()  # power in W
            percentage = (bus_voltage - 6) / 2.4 * 100
            if percentage > 100:
                percentage = 100
            if percentage < 0:
                percentage = 0

            battery = {
                "bus_voltage": "{:3.2f}V".format(bus_voltage),
                "shunt_voltage": "{:3.2f}mV".format(shunt_voltage),
                "current": "{:3.2f}mA".format(current / 1000),
                "power": "{:3.2f}W".format(power),
                "percentage": "{:3.2f}%".format(percentage),
            }
        except Exception as e:
            battery = {
                "bus_voltage": "n/a",
                "shunt_voltage": "n/a",
                "current": "n/a",
                "power": "n/a",
                "percentage": "n/a",
            }
    return battery


# Init Pygame
def init_screen():
    global clock
    global screen
    global font
    global axis_font
    global info_font
    global map_font
    global background
    global background_surface
    global background_position
    global dialog_surface
    global stats_surface
    global event_surface
    global chart_surface
    global map_background
    global map_width, map_height
    global map_surface
    global map_event_surface
    global static_circles_surface
    global system_surface
    global flags
    clock = pygame.time.Clock()
    screen = pygame.display.set_mode((width, height))
    print(f"Pygame driver: {pygame.display.get_driver()}")
    print(f"Pygame resolution: {width} x {height}")

    font = pygame.font.Font(None, font_size)
    info_font = pygame.font.Font(None, info_font_size)
    map_font = pygame.font.Font(None, map_font_size)
    axis_font = pygame.font.Font(None, axis_font_size)
    pygame.mouse.set_visible(False)
    # Flags
    # Define new dimensions
    flag_height = info_font.get_height()
    flag_height_map = map_font.get_height()
    flags_dir = "flags/"

    # Load flag images, resize them, and names into a list
    flags = []

    for filename in os.listdir(flags_dir):
        if filename.endswith('.png'):
            image = pygame.image.load(os.path.join(flags_dir, filename))
            aspect_ratio = image.get_width() / image.get_height()
            flag_width = int(flag_height * aspect_ratio)
            resized_image = pygame.transform.scale(image, (flag_width, flag_height))
            flags.append({'name': filename.upper()[:-4], 'image': resized_image})

    background_surface = pygame.Surface((width, height))
    background = pygame.image.load(background_image)
    background_position = (0, 0)
    background_surface.blit(background, background_position)
    dialog_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    dialog_surface.fill((50, 50, 50, 200))
    stats_surface = pygame.Surface((width, info_font.get_height() + 5), pygame.SRCALPHA)
    map_event_surface = pygame.Surface((width, ((map_font.get_height() + 5) * 3) + 2), pygame.SRCALPHA)
    event_surface = pygame.Surface((width, event_surface_height), pygame.SRCALPHA)
    chart_surface = pygame.Surface((width, chart_surface_height), pygame.SRCALPHA)
    map_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    static_circles_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    map_background = pygame.image.load(map_image)
    map_width, map_height = map_background.get_size()
    map_surface.fill((0, 0, 0))  # Need to fill, because maps might not fully cover screen
    map_surface.blit(map_background, (0, 0))
    system_surface = pygame.Surface((width, info_font.get_height() + 5), pygame.SRCALPHA)
    screen.blit(background_surface, (0, 0))
    draw_system_info()
    pygame.display.flip()


def close_app():
    pygame.quit()
    print('\nExiting')
    exit()


def port_to_type(port):
    try:
        port = int(port)
        port_map = {
            21: "FTP", 20: "FTP",
            22: "SSH", 2222: "SSH",
            23: "TELNET", 2223: "TELNET",
            25: "EMAIL", 143: "EMAIL", 110: "EMAIL", 993: "EMAIL", 995: "EMAIL",
            53: "DNS",
            80: "HTTP", 81: "HTTP", 8080: "HTTP", 8888: "HTTP",
            161: "SNMP",
            443: "HTTPS", 8443: "HTTPS",
            445: "SMB",
            631: "PRINTER", 9100: "PRINTER",
            1433: "DATABASE", 1521: "DATABASE", 3306: "DATABASE",
            2575: "MEDICAL", 11112: "MEDICAL",
            3389: "RDP",
            5060: "VOIP", 5061: "VOIP",
            5555: "ANDROID",
            5900: "VNC",
            6379: "REDIS"
        }
        return port_map.get(port, str(port))
    except:
        return "OTHER"


def get_flag_image(country_code):
    for flag in flags:
        if flag['name'] == country_code:
            return flag['image']
    return None  # Return None if no flag found


def get_honeypot_histogram(main_interval, breakdown):
    honeypot_histogram = {}
    date_format = "yyyy-MM-dd'T'HH:mm:ss'Z'"  # ISO 8601 format for Elasticsearch
    # Calculate the end time for the query interval
    end_time = "now"
    start_time = f"now-{main_interval}"

    # Elasticsearch aggregation query to get counts over the specified time interval
    es_honeypot_histogram = es.search(
        index=es_index,
        size=0,
        track_total_hits=True,
        query={
            "bool": {
                "filter": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": start_time,  # Start of the interval
                                "lte": end_time  # End of the interval
                            }
                        }
                    },
                    {
                        "terms": {
                            "type.keyword": honeypot_types
                        }
                    }
                ]
            }
        },
        aggs={
            "event_counts_over_time": {
                "date_histogram": {
                    "field": "@timestamp",
                    "fixed_interval": breakdown,
                    "format": date_format,
                    "min_doc_count": 0,
                    "extended_bounds": {
                        "min": start_time,  # Start time of the query interval
                        "max": end_time  # End time of the query interval
                    }
                }
            }
        }
    )
    honeypot_histogram[main_interval] = es_honeypot_histogram['aggregations']['event_counts_over_time']['buckets']
    return honeypot_histogram


def get_honeypot_stats():
    honeypot_stats = {}
    for timedelta in last:
        es_honeypot_stats = es.search(
            index=es_index,
            aggs={},
            size=0,
            track_total_hits=True,
            query={
                "bool": {
                    "must": [],
                    "filter": [
                        {
                            "terms": {
                                "type.keyword": honeypot_types
                            }
                        },
                        {
                            "range": {
                                "@timestamp": {
                                    "format": "strict_date_optional_time",
                                    "gte": "now-" + timedelta,
                                    "lte": "now"
                                }
                            }
                        }
                    ]
                }
            }
        )
        honeypot_stats.update({timedelta: es_honeypot_stats['hits']['total']['value']})
    # honeypot_stats.update({"type": "Stats"})
    return honeypot_stats


def get_honeypot_events(mylast, mynow):
    honeypot_data = es.search(
        index=es_index,
        size=100,
        query={
                "bool": {
                    "must": [],
                    "filter": [
                        {
                            "terms": {
                                "type.keyword": honeypot_types
                            }
                        },
                        {
                            "range": {
                                "@timestamp": {
                                    "format": "strict_date_optional_time",
                                    "gte": mylast[0] + "T" + mylast[1],
                                    "lte": mynow[0] + "T" + mynow[1]
                                }
                            }
                        }
                    ]
                }
            }
    )
    return honeypot_data


def process_honeypot_event(hit):
    try:
        event = {
            "honeypot": hit["_source"]["type"],
            "country": hit["_source"]["geoip"].get("country_name", ""),
            "country_code": hit["_source"]["geoip"].get("country_code2", ""),
            "region_name": hit["_source"]["geoip"].get("region_name"),
            "city": hit["_source"]["geoip"].get("city_name", "Unknown"),
            "continent_code": hit["_source"]["geoip"].get("continent_code", ""),
            "as_org": hit["_source"]["geoip"].get("as_org", ""),
            "dst_lat": hit["_source"]["geoip_ext"]["latitude"],
            "dst_long": hit["_source"]["geoip_ext"]["longitude"],
            "dst_ip": hit["_source"]["geoip_ext"]["ip"],
            "dst_iso_code": hit["_source"]["geoip_ext"].get("country_code2", ""),
            "dst_country_name": hit["_source"]["geoip_ext"].get("country_name", ""),
            "tpot_hostname": hit["_source"]["t-pot_hostname"],
            "event_time": str(hit["_source"]["@timestamp"][0:10]) + " " + str(hit["_source"]["@timestamp"][11:19]),
            "iso_code": hit["_source"]["geoip"]["country_code2"],
            "ip_rep": hit["_source"].get("ip_rep", "reputation unknown"),
            "latitude": hit["_source"]["geoip"]["latitude"],
            "longitude": hit["_source"]["geoip"]["longitude"],
            "dest_port": hit["_source"].get("dest_port", ""),
            "data_type": hit["_source"].get("data_type"), # conpot
            "event_type": hit["_source"].get("event_type"), # conpot, elasticpot
            "http_user_agent": hit["_source"].get("http_user_agent"), # elasticpot
            "http.url": hit["_source"].get("http.url"), # elasticpot
            "input": hit["_source"].get("input"), # cowrie, adbhoney
            "msg": hit["_source"].get("msg"), # dicompot
            "payload_printable": hit["_source"].get("payload_printable", ""), # ciscoasa
            "username": hit["_source"].get("username", ""),
            "password": hit["_source"].get("password", ""),
            "headers.user-agent": hit["_source"].get("headers", {}).get("user-agent"), # tanner
            "user-agent_os": hit["_source"].get("user-agent_os"), # h0neytr4p
            "user-agent_browser": hit["_source"].get("user-agent_browser"), # h0neytr4p
            "user_agent_browser": hit["_source"].get("user_agent_browser"), # honeyaml
            "path": hit["_source"].get("path"), # honeyaml, tanner
            "ipp_query.operation": hit["_source"].get("ipp_query.operation"), # ipphoney
            "data": hit["_source"].get("data"), # mailoney
            "info": hit["_source"].get("info"), # miniprint, wordpot
            "action": hit["_source"].get("action"), # redishoneypot
            "request_uri": hit["_source"].get("request_uri"), # h0neytr4p
            "browser_family": hit["_source"].get("browser_family"), # wordpot
            "browser_version": hit["_source"].get("browser_version"), # wordpot
            "url": hit["_source"].get("url"), # wordpot
            "plugin": hit["_source"].get("plugin"), # wordpot
            "request.requestURI": hit["_source"].get("request.requestURI"), # galah
            "request.userAgent": hit["_source"].get("request.userAgent"), # galah
            "protocol": port_to_type(hit["_source"].get("dest_port", "")),
            "src_ip": hit["_source"]["src_ip"]
        }
    except Exception as e:
        print(f"Exception on: {e} for {event['honeypot']}")
        pass
    if event["dest_port"] != "":
        try:
            event["color"] = service_rgb[event["protocol"].upper()]
        except:
            event["color"] = service_rgb["OTHER"]
        return event
    else:
        event["color"] = service_rgb["OTHER"]
        event["protocol"] = "N/A"
        if event["protocol"] == "N/A" and (event["input"] is None and event["payload_printable"] is None):
            pass
        else:  
            return event


def calculate_max_widths():
    # Returns the maximum width for the flag and a list of maximum widths for each column across the last_three_events.
    max_flag_width_map = 0
    max_column_widths = [0] * 5  # Assuming 5 columns, adjust if needed

    for event in last_three_events:
        # Calculate maximum flag width
        flag_image_map = get_flag_image(event["country_code"])
        max_flag_width_map = max(max_flag_width_map, flag_image_map.get_width())

        table_data = [
            event["country"], event["src_ip"], event["protocol"].lower(),
            event["honeypot"], event["ip_rep"].title()
        ]
        for i, value in enumerate(table_data):
            max_column_widths[i] = max(max_column_widths[i], map_font.size(value)[0])

    return max_flag_width_map, max_column_widths


def draw_honeypot_event_on_map(event):
    # Update the list of last three events
    last_three_events.insert(0, event)
    if len(last_three_events) > 3:
        last_three_events.pop()

    # Clear the surface
    map_event_surface.fill(stats_surface_background)

    # Calculate maximum widths for the flag and each column
    max_flag_width_map, max_column_widths = calculate_max_widths()

    # Calculate the total width needed and then find out the extra space available
    total_width_needed = max_flag_width_map + sum(max_column_widths) + (len(max_column_widths) - 1) * 5  # 5 as a base gap
    extra_space = width - total_width_needed - 2 * 4  # subtracting the x_offset on both sides

    # Distribute the extra space evenly among the gaps
    gap = 5 + extra_space // (len(max_column_widths) - 1)

    # Iterate over the events in the list and render them
    for idx, event in enumerate(last_three_events):
        # Calculate the y position based on the event's index
        y = idx * (map_font.get_height() + 5) + 4
        render_event_on_map(event, y, max_flag_width_map, max_column_widths, gap)


def render_event_on_map(event, y, max_flag_width_map, max_column_widths, gap):
    x, x_offset = 0, 4

    # Render the flag image
    flag_image_map = get_flag_image(event["country_code"])
    # Align the flag in the center of the allocated space
    flag_x = x_offset + (max_flag_width_map - flag_image_map.get_width()) // 2
    map_event_surface.blit(flag_image_map, (flag_x, y))

    table_data = [
        event["country"], event["src_ip"], event["protocol"].lower(),
        event["honeypot"], event["ip_rep"].title()
    ]

    x = x_offset + max_flag_width_map + 2
    for i, value in enumerate(table_data):
        map_event_text = map_font.render(value, True, event['color'])
        map_event_surface.blit(map_event_text, (int(x), y))
        x += max_column_widths[i] + gap


def draw_honeypot_event_loc_on_map(event):
    # Mercator projection map is needed to correctly plot geo coordinates on to the pixel based map
    global circle_counter
    circle_max = 100

    # Convert longitude to x coordinate
    x = (event["longitude"] + 180) * (map_width / 360)

    # Function to convert latitude using the Mercator projection
    def mercator(lat):
        # Clamp the latitude to the map's range to avoid extreme values
        lat = max(min(lat, latrange_max), latrange_min)
        return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

    # Calculate y coordinate using adjusted Mercator projection
    y = (mercator(event["latitude"]) - mercator(latrange_min)) / (mercator(latrange_max) - mercator(latrange_min))
    y = map_height - (y * map_height)  # Invert y for Pygame's coordinate system

    if circle_counter == circle_max:
        circle_counter = 0
        static_circles_surface.fill((0, 0, 0, 0))
    pygame.draw.circle(static_circles_surface, event["color"], (int(x), int(y)), circle_radius)

    ping = {
        "position": (int(x), int(y)),
        "color": event["color"],
        "current_radius": 0,
        "max_radius": 40,
        "alpha": 255,
        "fade_duration": 36,
        "frame_count": 0
    }
    active_pings.append(ping)


def update_and_draw_pings():
    global active_pings

    # Clear the previous frame
    map_surface.blit(map_background, (0, 0))

    # Blit the static circles onto the map surface
    map_surface.blit(static_circles_surface, (0, 0))

    # Update and draw each active ping
    for ping in active_pings[:]:
        # Calculate the current radius and alpha based on the frame count
        ping["current_radius"] = ping["max_radius"] * (ping["frame_count"] / ping["fade_duration"])
        ping["alpha"] = 255 * (1 - ping["frame_count"] / ping["fade_duration"])

        # Create a new surface for the radar ping
        ping_surface = pygame.Surface((ping["max_radius"] * 2, ping["max_radius"] * 2), pygame.SRCALPHA)
        pygame.draw.circle(ping_surface, ping["color"] + (int(ping["alpha"]),),
                           (ping["max_radius"], ping["max_radius"]), int(ping["current_radius"]))

        # Blit the radar ping surface onto the map surface
        map_surface.blit(ping_surface, (ping["position"][0] - ping["max_radius"],
                                        ping["position"][1] - ping["max_radius"]))

        # Increment frame count or remove the ping if the animation is done
        ping["frame_count"] += 1
        if ping["frame_count"] >= ping["fade_duration"]:
            active_pings.remove(ping)


def draw_honeypot_event(event):
    # Convert UTC to local time
    my_time = datetime.strptime(event["event_time"], "%Y-%m-%d %H:%M:%S")
    my_time = my_time.replace(tzinfo=pytz.UTC)  # Assuming event_time is in UTC
    local_event_time = my_time.astimezone(local_tz)
    local_event_time = local_event_time.strftime("%Y-%m-%d %H:%M:%S")
    max_length = 60

    # rewrite protocol for LLM based honeypots
    if event["honeypot"] == "Beelzebub":
        event["protocol"] = "SSH Interactive LLM"
    if event["honeypot"] == "Galah":
        event["protocol"] = "HTTP Interactive LLM"

    # Descriptions for each column
    descriptions = [
        "Timestamp:", "Country:", "City:", "Source IP:", "AS Org:", "IP Reputation:", "Port:", "Honeypot:"
    ]

    # Build the honeypot event table data
    table_data = [
        local_event_time, event["country"], event["city"], event["src_ip"], event["as_org"].title(),
        event["ip_rep"].title(), event["protocol"], event["honeypot"]
    ]

    # Enable more features at higher resolutions
    if width >= 1280 and height >= 800:
        # city
        if event["city"] == "Unknown":
            descriptions.remove("City:")
            table_data.remove(event["city"])

        # region
        if event["region_name"] is not None:
            descriptions.insert(descriptions.index("City:"), "Region:")
            table_data.insert(2, event["region_name"])
        
        # remove empty port
        if event["protocol"] == "N/A":
            descriptions.remove("Port:")
            table_data.remove(event["protocol"])

        # various honeypots
        if event["input"] is not None:
            descriptions.append("Command:")
            table_data.append(event["input"][:max_length])
        if event["username"] != "":
            descriptions.append("Username:")
            table_data.append(event["username"][:max_length])
        if event["password"] != "":
            descriptions.append("Password:")
            table_data.append(event["password"][:max_length])
        if event["payload_printable"] != "":
            descriptions.append("Command:")
            table_data.append(event["payload_printable"][:max_length])

        # conpot
        if event["data_type"] is not None:
            descriptions.append("Data Type:")
            table_data.append(event["data_type"].title())
        if event["event_type"] is not None:
            descriptions.append("Event Type:")
            table_data.append(event["event_type"].title())

        # dicompot, beelzebub
        if event["msg"] is not None and (event["honeypot"] == "Dicompot" or event["honeypot"] == "Beelzebub"):
            descriptions.append("Request:")
            table_data.append(event["msg"][:max_length])

        # elasticpot, ipphoney
        if event["http_user_agent"] is not None:
            descriptions.append("UserAgent:")
            table_data.append(event["http_user_agent"][:max_length])
        if event["http.url"] is not None:
            descriptions.append("Request:")
            table_data.append(event["http.url"][:max_length])

        # tanner
        if event["headers.user-agent"] is not None and event["honeypot"] == "Tanner":
            descriptions.append("UserAgent:")
            table_data.append(event["headers.user-agent"][:max_length])

        # galah
        if event["request.userAgent"] is not None:
            descriptions.append("UserAgent:")
            table_data.append(event["request.userAgent"][:max_length])
        if event["request.requestURI"] is not None:
            descriptions.append("Request:")
            table_data.append(event["request.requestURI"][:max_length])

        # honeyaml
        if event["user_agent_browser"] is not None:
            descriptions.append("UserAgent:")
            table_data.append(event["user_agent_browser"][:max_length])
        if event["path"] is not None and (event["honeypot"] == "Honeyaml" or event["honeypot"] == "Tanner"):
            descriptions.append("Request:")
            table_data.append(event["path"][:max_length])

        # h0neytr4p
        if event["user-agent_os"] is not None:
            descriptions.append("UserAgent OS:")
            table_data.append(event["user-agent_os"][:max_length])
        if event["user-agent_browser"] is not None:
            descriptions.append("UserAgent:")
            table_data.append(event["user-agent_browser"][:max_length])
        if event["request_uri"] is not None:
            descriptions.append("Request:")
            table_data.append(event["request_uri"][:max_length])

        # ipphoney
        if event["ipp_query.operation"] is not None:
            descriptions.append("Request:")
            table_data.append(event["ipp_query.operation"].title())

        # mailoney
        if event["data"] is not None and event["honeypot"] == "Mailoney":
            descriptions.append("Command:")
            table_data.append(event["data"][:max_length])

        # miniprint, wordpot
        if event["info"] is not None and (event["honeypot"] == "Miniprint" or event["honeypot"] == "Wordpot"):
            descriptions.append("Action:")
            table_data.append(event["info"].title()[:max_length])

        # redishoneypot
        if event["action"] is not None and event["honeypot"] == "Redishoneypot":
            descriptions.append("Action:")
            table_data.append(event["action"].title()[:max_length])

        # wordpot
        if event["plugin"] is not None:
            descriptions.append("Plugin:")
            table_data.append(event["plugin"].title()[:max_length])
        if event["url"] is not None:
            descriptions.append("Request:")
            table_data.append(event["url"][:max_length])
        if event["browser_family"] is not None and event["browser_version"] is not None:
            descriptions.append("UserAgent:")
            table_data.append(event["browser_family"]+"/"+event["browser_version"][:max_length])

    # Display the event table line by line
    flag_image = get_flag_image(event["country_code"])
    vertical_offset = 0
    event_surface.fill((0, 0, 0, 0))
    for desc in descriptions:
        line = desc
        event_text = font.render(line, True, magenta)
        event_surface.blit(event_text, (4, 2 + vertical_offset))
        vertical_offset += font.get_height()

    vertical_offset = 0
    for i, value in enumerate(table_data):
        line = value
        event_text = font.render(line, True, event["color"])
        if i == 1:
            event_surface.blit(flag_image, (event_horizontal_offset, 2 + vertical_offset))
            event_surface.blit(event_text, (event_horizontal_offset + 4 + flag_image.get_width(), 2 + vertical_offset))
        else:
            event_surface.blit(event_text, (event_horizontal_offset, 2 + vertical_offset))
        vertical_offset += font.get_height()


def draw_honeypot_bar_chart(data, interval, breakdown, space, depth, height):
    # The number of bars is relative to the interval / breakdown of the elastic events, i.e. 15m has a breakdown of 15s (15m*60s/15s=60)
    int_interval = int(interval.rstrip('hm'))
    int_breakdown = int(breakdown.rstrip('ms'))
    # num_bars = 60
    num_bars = (int_interval * 60) // (int_breakdown)

    # Clear surface before draw
    chart_surface.fill((0, 0, 0, 0))

    bar_width = chart_surface.get_width() / num_bars
    bar_width_s = int(bar_width - space)
    axis_y_pos = height - axis_font.get_linesize() - 1

    # Find the max value in the data for scaling
    max_value = max(item['doc_count'] for item in data[interval]) if data[interval] else 1
    scaled_max_height = axis_y_pos - depth

    # Draw bars
    for index, item in enumerate(data[interval]):
        # Scale the bar's height according to the data
        bar_height = int((item['doc_count'] / max_value) * scaled_max_height) if max_value != 0 else 0
        x_pos = int(index * bar_width + space)
        y_pos = axis_y_pos - bar_height
        pygame.draw.rect(chart_surface, color_bar_chart, (x_pos, y_pos, bar_width_s, bar_height))

        # Draw the top face of the 3D bar
        top_face_color = tuple([max(0, c - 30) for c in color_bar_chart])  # Slightly darker color
        pygame.draw.polygon(chart_surface, top_face_color, [(x_pos, y_pos),
                                                            (x_pos + depth, y_pos - depth),
                                                            (x_pos + bar_width_s + depth, y_pos - depth),
                                                            (x_pos + bar_width_s, y_pos)])

        # Draw the side face of the 3D bar
        side_face_color = tuple([max(0, c - 50) for c in color_bar_chart])  # Even darker color
        pygame.draw.polygon(chart_surface, side_face_color, [(x_pos + bar_width_s, y_pos),
                                                             (x_pos + bar_width_s + depth, y_pos - depth),
                                                             (x_pos + bar_width_s + depth, y_pos - depth + bar_height),
                                                             (x_pos + bar_width_s, y_pos + bar_height)])

    # X-Axis
    # Calculate and draw time labels and x-axis
    total_duration = {
        "1m": timedelta(minutes=1),
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24)
    }.get(interval, timedelta())

    current_time = datetime.now(get_localzone())
    pygame.draw.line(chart_surface, magenta, (0, axis_y_pos), (chart_surface.get_width(), axis_y_pos))  # Draw x-axis

    for i in range(4):
        label_time = current_time - total_duration * (3 - i) / 3
        label_str = label_time.strftime("%H:%M:%S")
        label_x_pos = int(chart_surface.get_width() * i / 3)

        # Adjust label position for the first and last labels
        if i == 0:
            label_position = (label_x_pos, axis_y_pos + 3)
        elif i == 3:
            last_label_width, _ = axis_font.size(label_str)
            label_position = (chart_surface.get_width() - last_label_width, axis_y_pos + 3)
        else:
            label_position = (label_x_pos - axis_font.size(label_str)[0] // 2, axis_y_pos + 3)

        chart_surface.blit(axis_font.render(label_str, True, white), label_position)

        # Draw small markers on the x-axis
        pygame.draw.line(chart_surface, white, (label_x_pos, axis_y_pos), (label_x_pos, axis_y_pos + 1), 3)

    # Y-Axis
    pygame.draw.line(chart_surface, magenta, (0, 0), (0, axis_y_pos))  # Draw y-axis line

    # Add label for max_value at the top of the y-axis
    max_value_str = str(max_value)
    max_value_label_width, max_value_label_height = axis_font.size(max_value_str)
    chart_surface.blit(axis_font.render(max_value_str, True, white), (5, max_value_label_height // 2))
    # Draw the marker for max_value
    pygame.draw.line(chart_surface, white, (0, 0), (5, 0), 2)


def draw_honeypot_stats(honeypot_stats):
    stats_last = []
    for timeframe in timeframes:
        stats_string_key = "string"
        stats_string = f"Last {timeframe['duration']}: {honeypot_stats.get(timeframe['duration'])}"
        stats_color_key = "color"
        stats_color = timeframe["color"]
        stats_dict = {stats_string_key: stats_string, stats_color_key: stats_color}
        stats_last.append(stats_dict)

    stats_surface.fill(stats_surface_background)
    x_offset, y = 4, 3

    # Calculate the total width of all texts
    total_text_width = sum([info_font.size(stat['string'])[0] for stat in stats_last])

    # Calculate the available width by subtracting the total text width and the 2 offsets
    available_width = width - total_text_width - 2 * x_offset

    # Divide the available width by the number of gaps (one less than the number of elements)
    gap = available_width / (len(stats_last) - 1)

    x = x_offset
    for i, stat in enumerate(stats_last):
        stats_text = info_font.render(stat['string'], True, stat['color'])
        stats_surface.blit(stats_text, (int(x), y))
        x += info_font.size(stat['string'])[0] + gap

        # Adjust for last element
        if i == len(stats_last) - 2:
            x = width - x_offset - info_font.size(stats_last[-1]['string'])[0]


def get_rssi(interface=wifi_if):
    try:
        rssi = os.popen(f"wpa_cli -i {interface} signal_poll | head -n1 | cut -f 2 -d '='").read().strip()
        
        # Check if the value is an integer
        if rssi.isdigit() or (rssi.startswith('-') and rssi[1:].isdigit()):
            return rssi
        else:
            return "n/a"
    except Exception as e:
        print(e)
        return "n/a"

def is_inet_reachable(endpoints=None, timeout=2):
    if endpoints is None:
        # List of reliable DNS servers
        endpoints = [
            "8.8.8.8",   # Google Public DNS
            "8.8.4.4",   # Google Public DNS (secondary)
            "1.1.1.1",   # Cloudflare DNS
            "1.0.0.1",   # Cloudflare DNS (secondary)
            "9.9.9.9",   # Quad9 DNS
            "149.112.112.112",  # Quad9 DNS (secondary)
            "208.67.222.222",   # OpenDNS
            "208.67.220.220",   # OpenDNS (secondary)
            "4.2.2.1",   # Level 3 Communications DNS
            "4.2.2.2"    # Level 3 Communications DNS (secondary)
        ]

    # Randomly choose one endpoint
    endpoint = random.choice(endpoints)
    try:
        # Attempt to connect to the selected endpoint on port 53
        with socket.create_connection((endpoint, 53), timeout=timeout):
            return True
    except Exception as e:
        return False

def get_external_ip_via_dns():
    global ext_ip_cache, last_ext_ip_check

    now = time.time()
    # If cache is still valid, return it immediately
    if ext_ip_cache is not None and (now - last_ext_ip_check) < EXT_IP_TTL:
        #print(f"[DEBUG] Returning cached external IP: {ext_ip_cache}")
        return ext_ip_cache

    dns_targets = [
        ("216.239.32.10", "o-o.myaddr.l.google.com", "TXT", "IN"),  # Google Public DNS
        ("216.239.32.10", "o-o.myaddr.l.google.com", "TXT", "IN"),  # Google Public DNS (secondary)
        ("208.67.222.222", "myip.opendns.com", "A", "IN"),          # OpenDNS
        ("208.67.220.220", "myip.opendns.com", "A", "IN"),          # OpenDNS (secondary)
        ("1.1.1.1", "whoami.cloudflare", "TXT", "CH"),              # Cloudflare DNS
        ("1.0.0.1", "whoami.cloudflare", "TXT", "CH"),              # Cloudflare DNS (secondary)
    ]

    dns_server, target_domain, query_type, query_class = random.choice(dns_targets)

    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [dns_server]
        resolver.lifetime = 2 # Timeout in seconds
        resolver.timeout = 2

        answer = resolver.resolve(
            target_domain,
            query_type,
            search=True,
            rdclass=dns.rdataclass.from_text(query_class)
        )

        # Convert the answer to a string and strip quotes
        response = str(answer[0]).strip('"')
        # Validate the response for an IP address
        ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', response)

        if ip_match:
            ext_ip_cache = ip_match.group(0)
            last_ext_ip_check = now
            #print(f"[DEBUG] External IP refreshed: {ext_ip_cache}")
            return ext_ip_cache
        else:
            #print(f"[DEBUG] Unexpected response format: {response}")
            ext_ip_cache = "n/a"
            last_ext_ip_check = now
            return ext_ip_cache

    except Exception as e:
        print(f"Failed to query {dns_server} ({target_domain}): {e}")
        ext_ip_cache = "n/a"
        last_ext_ip_check = now
        return ext_ip_cache

def draw_system_info():
    global running, network_fails, ext_ip_cache, last_ext_ip_check
    signal_strength = 0
    touch_pressed_time = 0
    int_ip = "n/a"
    ext_ip = "n/a"

    while int_ip == "n/a":
        try:
            interface = netifaces.gateways()['default'][netifaces.AF_INET][1]
            int_ip = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
            # Attempt to get the external IP address with timeout handling
            if is_inet_reachable():
                try:
                    ext_ip = get_external_ip_via_dns()
                except Exception as e:
                    ext_ip = "n/a"
                    print(f"Failed to get external IP: {e}")
            else:
                network_fails += 1
                if network_fails % 2 == 0:
                    try:
                        os.system(f"echo -n 'Reassociate {wifi_if}: ' && wpa_cli -i {wifi_if} reassociate")
                    except Exception as e:
                        print(f"Failed to reassociate: {e}")
        except Exception as e:
            int_ip = "n/a"
            print(f"Failed to get internal IP: {e}")
            
        if int_ip == "n/a":
            ext_ip_cache = None
            last_ext_ip_check = 0
            for i in range(31, 0, -1):
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        close_app()
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_q:
                            close_app()
                    elif event.type == pygame.FINGERDOWN:
                        touch_x = int(event.x * width)
                        touch_y = int(event.y * height)
                        # print (touch_x, touch_y)
                        touch_pressed_time = pygame.time.get_ticks()
                    elif event.type == pygame.FINGERUP:
                        touch_pressed_time = 0

                # Calculate the time the finger has been held down
                if touch_pressed_time > 0:
                    current_time = pygame.time.get_ticks()
                    if current_time - touch_pressed_time >= 5000:  # 5 seconds (5000 milliseconds)
                        running = False
                        subprocess.run(["sudo", "poweroff"])
                        close_app()
                info_text = info_font.render(f"Waiting for network. Retry in {str(i - 1)} seconds.", True, white)
                system_surface.fill(red)
                system_surface.blit(info_text, (4, 3))
                screen.blit(system_surface, (0, height - system_surface.get_height()))
                pygame.display.flip()
                pygame.time.wait(1000)

    # Retrieve wifi signal strength
    signal_strength = get_rssi()
    if signal_strength != "n/a":
        info_rssi = int(signal_strength)
    else:
        info_rssi = None

    # Retrieve battery info
    battery_color = magenta
    battery_info = get_battery_info(i2c_device)
    if battery_info["current"] != "n/a":
        if battery_info["current"].startswith("-"):
            battery_charging = False
        else:
            battery_charging = True
    else:
        battery_charging = False

    if battery_info["percentage"] != "n/a":
        battery_info_float = float(battery_info["percentage"].strip("%"))
        if battery_info_float >= 35:
            battery_color = magenta
        elif battery_info_float >= 30:
            battery_color = yellow
        elif battery_info_float >= 25:
            battery_color = orange
        elif battery_info_float < 25:
            battery_color = red
        if battery_info_float < 10 and not battery_charging:
            running = False
            subprocess.run(["sudo", "poweroff"])
            close_app()
    else:
        battery_color = system_surface_background
        battery_info_float = 0

    info_ext_ip = f"Ext IP: {ext_ip}"
    info_int_ip = f"Int IP: {int_ip}"
    info_text_ext_ip = info_font.render(info_ext_ip, True, magenta)
    info_text_int_ip = info_font.render(info_int_ip, True, magenta)

    x_offset, y_offset = 4, 3
    half_space = int((width + x_offset) / 2)
    int_ip_pos = half_space - (info_text_int_ip.get_width() / 2)

    # Render surface
    system_surface.fill(system_surface_background)

    # Draw the IP addresses
    system_surface.blit(info_text_ext_ip, (x_offset, y_offset))
    system_surface.blit(info_text_int_ip, (int_ip_pos, y_offset))

    # Battery terminal dimensions
    terminal_width = 5 # Width of the battery terminal
    terminal_height = 10 # Height of the battery terminal
    terminal_offset = 2 # Offset of the battery terminal

    # Battery icon dimensions
    battery_width = 50  # Width of the battery outline
    battery_height = 20  # Height of the battery outline
    battery_x = width - x_offset - battery_width - terminal_width - terminal_offset  # Position for the battery icon
    battery_y = y_offset  # Align with other text

    # Battery indicator
    fill_width = int((battery_info_float / 100) * (battery_width - 4))

    ### Wifi signal indicator (pie shape)
    # Define signal strength thresholds (one per pie segment, strongest first)
    thresholds = [-50, -60, -70, -80, -90]  # Strongest to weakest

    # Positioning (align next to battery indicator)
    wifi_x = width - x_offset - battery_width - terminal_width - 30  # Adjust positioning
    wifi_y = y_offset + 20  # Adjust vertical alignment

    # Pie icon parameters
    max_radius = 20  # Maximum radius of the pie shape
    min_radius = 5
    num_sections = len(thresholds)  # Number of signal levels
    angle_step = 90 / num_sections  # Angle for each section (90° divided into levels)

    # Draw pie base
    pie_color = grey
    for i in range(num_sections):
        # Calculate arc angles for each section
        start_angle = math.radians(45 + (i * angle_step))  # Start angle for segment
        end_angle = math.radians(45 + ((i + 1) * angle_step))  # End angle for segment

        # Define pie segment (triangular shape)
        pie_base_points = [
            (wifi_x, wifi_y),  # Center point (base of pie)
            (wifi_x + max_radius * math.cos(start_angle), wifi_y - max_radius * math.sin(start_angle)),  # Outer start
            (wifi_x + max_radius * math.cos(end_angle), wifi_y - max_radius * math.sin(end_angle)),  # Outer end
        ]

        # Draw pie base
        pygame.draw.polygon(system_surface, pie_color, pie_base_points)

    # Compute radius based on signal strength
    if info_rssi is not None:
        radius = min_radius + (max_radius - min_radius) * max(0, min(1, (info_rssi + 90) / 40))
    else:
        radius = min_radius  # Default to weakest size if no signal

    # Draw pie slices for signal strength
    pie_color = magenta
    for i in range(num_sections):
        # Calculate arc angles for each section
        start_angle = math.radians(45 + (i * angle_step))  # Start angle for segment
        end_angle = math.radians(45 + ((i + 1) * angle_step))  # End angle for segment

        # Define pie segment (triangular shape)
        points = [
            (wifi_x, wifi_y),  # Center point (base of pie)
            (wifi_x + radius * math.cos(start_angle), wifi_y - radius * math.sin(start_angle)),  # Outer start
            (wifi_x + radius * math.cos(end_angle), wifi_y - radius * math.sin(end_angle)),  # Outer end
        ]

        # Draw pie segment
        pygame.draw.polygon(system_surface, pie_color, points)

    # Draw the battery outline
    pygame.draw.rect(system_surface, grey, (battery_x, battery_y, battery_width, battery_height), 2)

    # Draw the battery filling
    pygame.draw.rect(
        system_surface, battery_color, (battery_x + 2, battery_y + 2, fill_width, battery_height - 4)
    )

    # Draw the battery terminal
    if battery_charging:
        battery_terminal_color = magenta
    else:
        battery_terminal_color = grey
    pygame.draw.rect(
        system_surface,
        battery_terminal_color,
        (battery_x + battery_width + terminal_offset, battery_y + (battery_height - terminal_height) // 2, terminal_width, terminal_height),
    )


def draw_button(surface, button_rect, text, color):
    pygame.draw.rect(surface, color, button_rect)
    text_render = font.render(text, True, white)
    surface.blit(text_render, text_render.get_rect(center=button_rect.center))


def system_action(action):
    global screen_index
    global dialog_open
    if action == "REBOOT":
        dialog_open = False
        subprocess.run(["sudo", "reboot"])
        print("Rebooting now ...")
        close_app()
    elif action == "POWEROFF":
        dialog_open = False
        subprocess.run(["sudo", "poweroff"])
        print("Shutting down now ...")
        close_app()
    elif action == "MODE":
        dialog_open = False
        screen_index = (screen_index + 1) % 2


def display_screens():
    global dialog_open
    global pause
    global event_display_interval
    # Draw standard overview
    if screen_index == 0:
        pause = 90 # Pause in milliseconds
        event_display_interval = 0.1
        screen.blit(background_surface, (0, 0))
        screen.blit(stats_surface, (0, 0))
        screen.blit(event_surface, (0, 35))
        screen.blit(chart_surface, (0, height - chart_surface.get_height() - system_surface.get_height()))
        screen.blit(system_surface, (0, height - system_surface.get_height()))
        if dialog_open:
            screen.blit(dialog_surface, (0, 0))
    # Draw map overview
    if screen_index == 1:
        pause = 1 # Pause in milliseconds
        event_display_interval = 0
        screen.blit(map_surface, (0, 0))
        screen.blit(map_event_surface, (0, 0))
        if dialog_open:
            screen.blit(dialog_surface, (0, 0))
        update_and_draw_pings()
    pygame.display.flip()


def update_honeypot_data():
    global stats_index
    global screen_index
    global dialog_open
    global event_display_interval
    dialog_open = False
    start_touch_y = None
    start_touch_valid = False  # Flag to track if the start of the touch is valid
    stats_index = 2
    screen_index = 0
    running = True # Main loop is actively running
    mydelta = 10
    time_last_request = datetime.utcnow() - timedelta(seconds=mydelta)
    events_interval = 0.5
    event_queue = deque()  # Buffer for honeypot events
    event_display_interval = 0.1  # Interval to display each event
    stats_interval = 5
    system_interval = 10
    pause = 100  # Pause in milliseconds
    now = time.time()
    events_start_time = now
    stats_start_time = now
    system_start_time = now
    last_event_display_time = now
    
    while running:
        now = time.time()

        #############################
        # Timed Updates for Actions #
        #############################

        # Get the honeypot stats every 5s (last 15m, 1h, 24h)
        if now - stats_start_time > stats_interval:
            honeypot_stats = get_honeypot_stats()
            draw_honeypot_stats(honeypot_stats)
            honeypot_histogram_data = get_honeypot_histogram(
                main_interval=timeframes[stats_index]["duration"],
                breakdown=timeframes[stats_index]["breakdown"],
            )
            draw_honeypot_bar_chart(
                honeypot_histogram_data,
                timeframes[stats_index]["duration"],
                timeframes[stats_index]["breakdown"],
                bar_space, bar_depth, height=chart_surface.get_height()
            )
            stats_start_time = now

        # Get system info every 10s
        if now - system_start_time > system_interval:
            draw_system_info()
            system_start_time = now

        # Get the last 100 new honeypot events every 0.5s
        if now - events_start_time > events_interval:
            mylast = str(time_last_request).split(" ")
            mynow = str(datetime.utcnow() - timedelta(seconds=mydelta)).split(" ")
            honeypot_data = get_honeypot_events(mylast, mynow)
            honeypot_events = honeypot_data['hits']

            if len(honeypot_events['hits']) != 0:
                time_last_request = datetime.utcnow() - timedelta(seconds=mydelta)
                for honeypot_event in honeypot_events['hits']:
                    event_queue.append(honeypot_event)  # Add events to the buffer
            events_start_time = now

        ############################
        # Display Buffered Events #
        ############################
        if event_queue and now - last_event_display_time > event_display_interval:
            honeypot_event = event_queue.popleft()
            try:
                processed_honeypot_event = process_honeypot_event(honeypot_event)
                if processed_honeypot_event is not None:
                    draw_honeypot_event(processed_honeypot_event)
                    draw_honeypot_event_on_map(processed_honeypot_event)
                    draw_honeypot_event_loc_on_map(processed_honeypot_event)
                    display_screens()
            except Exception as e:
                print(f"Error processing event: {e}")
            last_event_display_time = now

        ##########################
        # Main Pygame Event Loop #
        ##########################
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                close_app()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                    close_app()
            elif event.type == pygame.FINGERMOTION:
                if start_touch_y is None:
                    start_touch_y = event.y * height
                    if start_touch_y > (height * 0.75):
                        start_touch_valid = True
                else:
                    if start_touch_valid:
                        end_touch_y = event.y * height
                        if start_touch_y - end_touch_y > (height / 2):
                            dialog_open = True
            elif event.type == pygame.FINGERUP:
                if not dialog_open and not start_touch_valid:
                    stats_index = (stats_index + 1) % len(timeframes)
                    for i, timeframe in enumerate(timeframes):
                        timeframe["color"] = white if i == stats_index else magenta
                    honeypot_stats = get_honeypot_stats()
                    draw_honeypot_stats(honeypot_stats)
                    honeypot_histogram_data = get_honeypot_histogram(
                        main_interval=timeframes[stats_index]["duration"],
                        breakdown=timeframes[stats_index]["breakdown"],
                    )
                    draw_honeypot_bar_chart(
                        honeypot_histogram_data,
                        timeframes[stats_index]["duration"],
                        timeframes[stats_index]["breakdown"],
                        bar_space, bar_depth, height=chart_surface.get_height()
                    )
                start_touch_y = None
                start_touch_valid = False

            if dialog_open:
                mode_button_text = "Map" if screen_index == 0 else "Stats"
                draw_button(dialog_surface, cancel_button_rect, "Cancel", grey)
                draw_button(dialog_surface, mode_button_rect, mode_button_text, magenta)
                draw_button(dialog_surface, reboot_button_rect, "Reboot", dark_orange)
                draw_button(dialog_surface, poweroff_button_rect, "Power Off", dark_red)
                if event.type == pygame.FINGERDOWN:
                    finger_pos = (event.x * width, event.y * height)
                    if cancel_button_rect.collidepoint(finger_pos):
                        dialog_open = False
                    elif mode_button_rect.collidepoint(finger_pos):
                        system_action("MODE")
                    elif reboot_button_rect.collidepoint(finger_pos):
                        system_action("REBOOT")
                    elif poweroff_button_rect.collidepoint(finger_pos):
                        system_action("POWEROFF")
                    stats_index = (stats_index - 1) % len(timeframes)

        #######################
        # Manage Frame Update #
        #######################
        display_screens()
        pygame.time.wait(pause) # Keep cpu usage low
        clock.tick(fps)

if __name__ == '__main__':
    print(version)
    i2c_device = init_ina219()
    init_screen()
    try:
        while True:
            try:
                update_honeypot_data()
            except Exception as e:
                dialog_open = False
                start_touch_y = None
                start_touch_valid = False
                if "error" in str(e):
                    draw_system_info()
                    for i in range(31, 0, -1):
                        for event in pygame.event.get():
                            if event.type == pygame.QUIT:
                                close_app()
                            elif event.type == pygame.KEYDOWN:
                                if event.key == pygame.K_q:
                                    close_app()
                            elif event.type == pygame.FINGERMOTION:
                                if start_touch_y is None:  # Starting a new motion
                                    start_touch_y = event.y * height
                                    # Check if the touch starts at the bottom 25% of the screen
                                    if start_touch_y > (height * 0.75):
                                        start_touch_valid = True
                                else:
                                    # Only consider motion if it started in a valid area
                                    if start_touch_valid:
                                        end_touch_y = event.y * height
                                        # Check if the motion went upwards at least half the screen height
                                        if start_touch_y - end_touch_y > (height / 2):
                                            dialog_open = True
                            elif event.type == pygame.FINGERUP:
                                # Reset on finger lift
                                start_touch_y = None
                                start_touch_valid = False

                            if dialog_open:
                                draw_button(dialog_surface, cancel_button_rect, "Cancel", grey)
                                draw_button(dialog_surface, reboot_button_rect, "Reboot", dark_orange)
                                draw_button(dialog_surface, poweroff_button_rect, "Power Off", dark_red)
                                # Check for button presses if dialog is open
                                if event.type == pygame.FINGERDOWN:
                                    finger_pos = (event.x * width, event.y * height)
                                    if cancel_button_rect.collidepoint(finger_pos):
                                        dialog_open = False  # Close dialog
                                    elif reboot_button_rect.collidepoint(finger_pos):
                                        system_action("REBOOT")
                                    elif poweroff_button_rect.collidepoint(finger_pos):
                                        system_action("POWEROFF")
                        stats_text = info_font.render(f"Waiting for Elasticsearch. Retry in {str(i - 1)} seconds.",
                                                      True, white)
                        stats_surface.fill(red)
                        stats_surface.blit(stats_text, (4, 3))
                        display_screens()
                        pygame.display.flip()
                        pygame.time.wait(1000)
    except KeyboardInterrupt:
        close_app()
