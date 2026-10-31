# Interactive design laboratory

Open [index.html](./index.html) directly in a browser. No server or package
installation is required. This is a disposable design surface, not the
production frontend and not a change from Qt to a browser kiosk.

The current iteration refines layout C at 800x480 and 1280x800. On 8 inches,
Alarm Intelligence spans the left column; Activity sits directly below Attack
Stream in the right column. Reputation is above credentials and commands,
visible without scrolling at both sizes. Short sample events fit completely
on 8 inches. The compact overview prioritizes readable country, IP, service,
reputation and credentials. A short command preview opens the full details;
region/city, ASN, coordinates and complete requests remain in that enlarged,
scrollable detail view instead of shrinking all text to fit.

Select alarms, hold/resume live following, expand Activity, inspect its time
grid and try System/presentation and boot. Wi-Fi uses concentric circular
arcs, not cellular bars; charging now uses an upward arrow inside the battery,
not a lightning or plug glyph. Tap battery/Wi-Fi icons for numeric details and
an explicit Charging/Discharging label; the compact
header moves version/IP information out of the visible status bar.
The large header explicitly labels Public IP. The amber diamond explains
the fixture indicator.

Map is fullscreen with the real local map asset, projected event markers,
minimal event cards and a Back control. Marker labels avoid overlapping and
use larger text on the compact display. Entering Map previews three synthetic
attack arcs/ping pairs; **New example alarm** triggers another, rotating
between fixture origins. Effects stop within 1.35 seconds, do not run while
idle, are cancelled on navigation and respect reduced-motion preferences.
The destination is a clearly labelled synthetic sensor location, not a
claim about the actual device location.

Events and Tops omit the overview counter cards. The 8-inch event list uses
two columns; the compact list uses full-width rows with metadata spread
across the available width. Browser geometry checks confirm three complete
event cards on 4.3 inches, six on 8 inches, and three complete cards in the
8-inch Attack Stream for the supplied fixtures. This is not a certification
of physical readability or arbitrary long event contents.
Tops shows enlarged country/honeypot donuts, country flags and
service bars. Honeypot colours come from the same palette as event cards
and map markers. All interface text, accessibility labels and tooltips are
English. Counts consistently use English thousands separators on
8 inches and compact K/M notation on 4.3 inches; exact values are available
in numeric tooltips and donut accessibility labels. Expanded Activity puts
timeframe controls next to Back in a single header row, giving the histogram
more vertical space. All expanded-histogram controls, including Back, are
64x52 pixels with a vertical divider before Back. Map event timestamps use
18px text on both sizes; 8-inch overview Attack Stream timestamps also use
18px text.
All alarms, credentials and telemetry are synthetic. No hardware or
production data is accessed.

Deep links: `index.html?size=800`, `?size=1280&page=Map`,
`?size=800&page=Tops`, `?size=800&boot=1`.
Fit mode changes preview scale, not internal layout. This replaces the A/B/C
selector after the user selected C; the older comparison screenshots remain
session artifacts, not the current design.

The header uses the user-supplied Telekom SVG under `images/`.
The boot pixel data is generated from the canonical, GPL-3.0 T-Pot ANSI
template at upstream commit `0df39a8752df8d2849359998ad7b14f59ce66e1c`.
Regenerate with `python3 tools/design/build_splash.py` (requires authenticated
`gh` and Internet). The extractor parses literal data and never executes
upstream Python code.

The approved design is now implemented in the production QML frontend.
This browser prototype remains a design reference; its animation code was
not reused. Native map trajectories and completion are tested separately.
