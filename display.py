from datetime import datetime, timedelta
import time
import os
import socket
import netifaces
import pytz
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"  # Suppress Pygame welcome message
import pygame
import subprocess
import math
import sys
from modules import myip
from elasticsearch import Elasticsearch
from tzlocal import get_localzone
from modules.ina219_module import INA219

es = Elasticsearch('http://127.0.0.1:64298')
# es = Elasticsearch('http://elasticsearch:9200')
es_index = "logstash-*"
version = 'T-Pot Mobile v0.6'
local_tz = get_localzone()

# Counter, indices, etc.
circle_counter = 0
active_pings = []
bar_space, bar_depth = 1, 4
last_three_events = []

# Pygame Settings
os.environ['SDL_AUDIODRIVER'] = 'dummy'  # Prevent sound support
# os.environ["SDL_VIDEODRIVER"] = "KMSDRM"
# os.environ["SDL_FBDEV"] = "/dev/fb0"
# os.environ["SDL_MOUSEDRV"] = "TSLIB"
# os.environ["SDL_MOUSEDEV"] = "/dev/input/event0"
# os.environ['TSLIB_FBDEVICE'] = '/dev/fb0'
# os.environ['TSLIB_TSDEVICE'] = '/dev/input/event0'
# os.environ['TSLIB_CONFFILE'] = '/etc/ts.conf'
# os.environ['TSLIB_CALIBFILE'] = '/etc/pointercal'
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
# Keeping this section in case other display resolutions need to be supported (touch motion support required)
if width == 800 and height == 480:
    background_image = "images/tpot_800480.png"
    map_image = "images/map_800477.png"
    font_size = 34
    button_font_size = 36
    info_font_size = 28
    axis_font_size = 22
    button_width, button_height = 120, 120
    button_spacing = 20
    circle_radius = 6
    chart_surface_height = 170
    event_surface_height = 195
    event_horizontal_offset = 175
    latrange_min = -60
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
    "Adbhoney", "Ciscoasa", "CitrixHoneypot", "ConPot", "Cowrie", "Ddospot", "Dicompot", "Dionaea",
    "ElasticPot", "Endlessh", "Glutton", "Hellpot", "Heralding", "Honeytrap", "Honeypots",
    "Log4pot", "Ipphoney", "Mailoney", "Medpot", "Redishoneypot", "Sentrypeer", "Tanner", "Wordpot"
]

# Color Codes for Attack Map
service_rgb = {
    'FTP': (255, 0, 0),
    'SSH': (255, 128, 0),
    'TELNET': (255, 255, 0),
    'EMAIL': (128, 255, 0),
    'SQL': (0, 255, 0),
    'DNS': (0, 255, 128),
    'HTTP': (0, 255, 255),
    'HTTPS': (0, 128, 255),
    'VNC': (0, 0, 255),
    'SNMP': (128, 0, 255),
    'SMB': (191, 0, 255),
    'MEDICAL': (255, 0, 255),
    'RDP': (255, 0, 96),
    'SIP': (255, 204, 255),
    'ADB': (255, 204, 204),
    'OTHER': (255, 255, 255)
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
    axis_font = pygame.font.Font(None, axis_font_size)
    pygame.mouse.set_visible(False)
    # Flags
    # Define new dimensions
    flag_height = info_font.get_height()
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
    map_event_surface = pygame.Surface((width, ((info_font.get_height() + 5) * 3) + 2), pygame.SRCALPHA)
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
            80: "HTTP", 81: "HTTP", 8080: "HTTP",
            161: "SNMP",
            443: "HTTPS", 8443: "HTTPS",
            445: "SMB",
            1433: "SQL", 1521: "SQL", 3306: "SQL",
            2575: "MEDICAL", 11112: "MEDICAL",
            5900: "VNC",
            3389: "RDP",
            5060: "SIP", 5061: "SIP",
            5555: "ADB"
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
                "must": [
                    {
                        "terms": {
                            "type.keyword": honeypot_types
                        }
                    }
                ],
                "filter": [
                    {
                        "range": {
                            "@timestamp": {
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
    event = {
        "honeypot": hit["_source"]["type"],
        "country": hit["_source"]["geoip"].get("country_name", ""),
        "country_code": hit["_source"]["geoip"].get("country_code2", ""),
        "city": hit["_source"]["geoip"].get("city_name", ""),
        "continent_code": hit["_source"]["geoip"].get("continent_code", ""),
        "as_org": hit["_source"]["geoip"].get("as_org"),
        "dst_lat": hit["_source"]["geoip_ext"]["latitude"],
        "dst_long": hit["_source"]["geoip_ext"]["longitude"],
        "dst_ip": hit["_source"]["geoip_ext"]["ip"],
        "dst_iso_code": hit["_source"]["geoip_ext"].get("country_code2", ""),
        "dst_country_name": hit["_source"]["geoip_ext"].get("country_name", ""),
        "tpot_hostname": hit["_source"]["t-pot_hostname"],
        "event_time": str(hit["_source"]["@timestamp"][0:10]) + " " + str(hit["_source"]["@timestamp"][11:19]),
        "iso_code": hit["_source"]["geoip"]["country_code2"],
        "latitude": hit["_source"]["geoip"]["latitude"],
        "longitude": hit["_source"]["geoip"]["longitude"],
        "dst_port": hit["_source"]["dest_port"],
        "protocol": port_to_type(hit["_source"]["dest_port"]),
        "src_ip": hit["_source"]["src_ip"]
    }

    try:
        event["src_port"] = hit["_source"]["src_port"]
    except:
        event["src_port"] = 0
    try:
        event["ip_rep"] = hit["_source"]["ip_rep"]
    except:
        event["ip_rep"] = "reputation unknown"
    if event["city"] == "":
        event["city"] = "Unknown"
    if not event["src_ip"] == "":
        try:
            event["color"] = service_rgb[event["protocol"].upper()]
        except:
            event["color"] = service_rgb["OTHER"]
        return event
    else:
        print("SRC IP EMPTY")


def calculate_max_widths():
    # Returns the maximum width for the flag and a list of maximum widths for each column across the last_three_events.
    max_flag_width = 0
    max_column_widths = [0] * 5  # Assuming 5 columns, adjust if needed

    for event in last_three_events:
        # Calculate maximum flag width
        flag_image = get_flag_image(event["country_code"])
        max_flag_width = max(max_flag_width, flag_image.get_width())

        table_data = [
            event["country"], event["src_ip"], event["protocol"].lower(),
            event["honeypot"], event["ip_rep"].title()
        ]
        for i, value in enumerate(table_data):
            max_column_widths[i] = max(max_column_widths[i], info_font.size(value)[0])

    return max_flag_width, max_column_widths


def draw_honeypot_event_on_map(event):
    # Update the list of last three events
    last_three_events.insert(0, event)
    if len(last_three_events) > 3:
        last_three_events.pop()

    # Clear the surface
    map_event_surface.fill(stats_surface_background)

    # Calculate maximum widths for the flag and each column
    max_flag_width, max_column_widths = calculate_max_widths()

    # Calculate the total width needed and then find out the extra space available
    total_width_needed = max_flag_width + sum(max_column_widths) + (len(max_column_widths) - 1) * 5  # 5 as a base gap
    extra_space = width - total_width_needed - 2 * 4  # subtracting the x_offset on both sides

    # Distribute the extra space evenly among the gaps
    gap = 5 + extra_space // (len(max_column_widths) - 1)

    # Iterate over the events in the list and render them
    for idx, event in enumerate(last_three_events):
        # Calculate the y position based on the event's index
        y = idx * (info_font.get_height() + 5) + 4
        render_event_on_map(event, y, max_flag_width, max_column_widths, gap)


def render_event_on_map(event, y, max_flag_width, max_column_widths, gap):
    x, x_offset = 0, 4

    # Render the flag image
    flag_image = get_flag_image(event["country_code"])
    # Align the flag in the center of the allocated space
    flag_x = x_offset + (max_flag_width - flag_image.get_width()) // 2
    map_event_surface.blit(flag_image, (flag_x, y))

    table_data = [
        event["country"], event["src_ip"], event["protocol"].lower(),
        event["honeypot"], event["ip_rep"].title()
    ]

    x = x_offset + max_flag_width + 2
    for i, value in enumerate(table_data):
        map_event_text = info_font.render(value, True, event['color'])
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

    # Descriptions for each column
    descriptions = [
        "Timestamp:", "Country:", "City:", "Source IP:", "AS Org:", "IP Reputation:", "Port:", "Honeypot:"
    ]

    # Build the honeypot event table data
    table_data = [
        local_event_time, event["country"], event["city"], event["src_ip"], event["as_org"].title(),
        event["ip_rep"].title(), event["protocol"], event["honeypot"]
    ]

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


def draw_system_info():
    global running
    touch_pressed_time = 0
    int_ip = "n/a"
    ext_ip = "n/a"

    while int_ip == "n/a":
        try:
            interface = netifaces.gateways()['default'][netifaces.AF_INET][1]
            int_ip = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
            ext_ip = myip.get_external_ip()
            # print(interface, int_ip)
        except Exception as e:
            int_ip = "n/a"
        if int_ip == "n/a":
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
                time.sleep(1)
    # hostname = socket.gethostname()
    # uptime = os.popen('uptime').read().strip().split(',')[0]
    battery_info = get_battery_info(i2c_device)
    battery_color = magenta
    if battery_info["percentage"] != "n/a":
        battery_info_float = float(battery_info["percentage"].strip("%"))
        if battery_info_float >= 66:
            battery_color = green
        elif battery_info_float >= 50:
            battery_color = yellow
        elif battery_info_float >= 25:
            battery_color = orange
        elif battery_info_float < 25:
            battery_color = red
        if battery_info_float < 10:
            running = False
            subprocess.run(["sudo", "poweroff"])
            close_app()
    # info_hostname = f"Hostname: {hostname}"
    info_ext_ip = f"Int IP: {int_ip}"
    info_int_ip = f"Ext IP: {ext_ip}"
    # info_uptime = f"Up: {uptime}"
    info_battery_percentage = f"Battery: {battery_info['percentage']}"
    # info_text_hostname = info_font.render(info_hostname, True, magenta)
    info_text_ext_ip = info_font.render(info_ext_ip, True, magenta)
    info_text_int_ip = info_font.render(info_int_ip, True, magenta)
    # info_text_uptime = info_font.render(info_uptime, True, magenta)
    info_text_battery = info_font.render(info_battery_percentage, True, battery_color)
    x_offset, y_offset = 4, 3
    total_space = width - info_text_ext_ip.get_width() - info_text_battery.get_width()
    half_space = int(total_space / 2)
    int_ip_pos = int(x_offset / 2 + info_text_ext_ip.get_width() + half_space - (info_text_int_ip.get_width() / 2))
    system_surface.fill(system_surface_background)
    system_surface.blit(info_text_ext_ip, (int_ip_pos, y_offset))
    system_surface.blit(info_text_int_ip, (x_offset, y_offset))
    system_surface.blit(info_text_battery, (width - x_offset - info_text_battery.get_width(), y_offset))


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
    # Draw standard overview
    if screen_index == 0:
        screen.blit(background_surface, (0, 0))
        screen.blit(stats_surface, (0, 0))
        screen.blit(event_surface, (0, 35))
        screen.blit(chart_surface, (0, height - chart_surface.get_height() - system_surface.get_height()))
        screen.blit(system_surface, (0, height - system_surface.get_height()))
        if dialog_open:
            screen.blit(dialog_surface, (0, 0))
    # Draw map overview
    if screen_index == 1:
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
    dialog_open = False
    start_touch_y = None
    start_touch_valid = False  # Flag to track if the start of the touch is valid
    stats_index = 2
    screen_index = 0
    running = True
    mydelta = 10
    time_last_request = datetime.utcnow() - timedelta(seconds=mydelta)
    events_interval = 0.5
    stats_interval = 5
    system_interval = 10
    events_start_time = time.time()
    stats_start_time = time.time()
    system_start_time = time.time()
    while running:
        #######################################################
        # Get the honeypot stats every 5s (last 15m, 1h, 24h) #
        #######################################################
        stats_elapsed = time.time() - stats_start_time
        if stats_elapsed > stats_interval:
            honeypot_stats = get_honeypot_stats()
            draw_honeypot_stats(honeypot_stats)

            honeypot_histogram_data = get_honeypot_histogram(main_interval=timeframes[stats_index]["duration"],
                                                             breakdown=timeframes[stats_index]["breakdown"])
            draw_honeypot_bar_chart(honeypot_histogram_data, timeframes[stats_index]["duration"],
                                    timeframes[stats_index]["breakdown"],
                                    bar_space, bar_depth, height=chart_surface.get_height())
            stats_start_time = time.time()

        #############################
        # Get system info every 10s #
        #############################
        system_elapsed = time.time() - system_start_time
        if system_elapsed > system_interval:
            draw_system_info()

            system_start_time = time.time()

        ###################################################
        # Get the last 100 new honeypot events every 0.5s #
        ###################################################
        events_elapsed = time.time() - events_start_time
        if events_elapsed > events_interval:
            mylast = str(time_last_request).split(" ")
            mynow = str(datetime.utcnow() - timedelta(seconds=mydelta)).split(" ")

            honeypot_data = get_honeypot_events(mylast, mynow)

            honeypot_events = honeypot_data['hits']
            if len(honeypot_events['hits']) != 0:
                time_last_request = datetime.utcnow() - timedelta(seconds=mydelta)
                for honeypot_event in honeypot_events['hits']:
                    try:
                        processed_honeypot_event = process_honeypot_event(honeypot_event)
                        if process_honeypot_event(honeypot_event) is not None:
                            draw_honeypot_event(processed_honeypot_event)
                            draw_honeypot_event_on_map(processed_honeypot_event)
                            draw_honeypot_event_loc_on_map(processed_honeypot_event)
                            display_screens()
                            clock.tick(fps)
                    except:
                        pass

        ##########################
        # Main Pygame event loop #
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
                if not dialog_open and not start_touch_valid:
                    stats_index = (stats_index + 1) % len(timeframes)
                    for i, timeframe in enumerate(timeframes):
                        if i == stats_index:
                            timeframe["color"] = white
                        else:
                            timeframe["color"] = magenta
                    honeypot_stats = get_honeypot_stats()
                    draw_honeypot_stats(honeypot_stats)
                    honeypot_histogram_data = get_honeypot_histogram(main_interval=timeframes[stats_index]["duration"],
                                                                     breakdown=timeframes[stats_index]["breakdown"])
                    draw_honeypot_bar_chart(honeypot_histogram_data, timeframes[stats_index]["duration"],
                                            timeframes[stats_index]["breakdown"],
                                            bar_space, bar_depth, height=chart_surface.get_height())
                # Reset on finger lift
                start_touch_y = None
                start_touch_valid = False

        if dialog_open:
            if screen_index == 0:
              mode_button_text = "Map"
            elif screen_index == 1:
              mode_button_text = "Stats"
            draw_button(dialog_surface, cancel_button_rect, "Cancel", grey)
            draw_button(dialog_surface, mode_button_rect, mode_button_text, magenta)
            draw_button(dialog_surface, reboot_button_rect, "Reboot", dark_orange)
            draw_button(dialog_surface, poweroff_button_rect, "Power Off", dark_red)
            # Check for button presses if dialog is open
            if event.type == pygame.FINGERDOWN:
                finger_pos = (event.x * width, event.y * height)
                if cancel_button_rect.collidepoint(finger_pos):
                    dialog_open = False  # Close dialog
                elif mode_button_rect.collidepoint(finger_pos):
                    system_action("MODE")
                elif reboot_button_rect.collidepoint(finger_pos):
                    system_action("REBOOT")
                elif poweroff_button_rect.collidepoint(finger_pos):
                    system_action("POWEROFF")
                stats_index = (stats_index - 1) % len(timeframes)

        display_screens()
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
                        time.sleep(1)
    except KeyboardInterrupt:
        close_app()
