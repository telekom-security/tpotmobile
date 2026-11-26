The idea for T-Pot Mobile started a couple of years back when T-Pot started to support the ARM64 architecture. Raspberry Pi hardware was hard to come by at reasonable prices so the journey took a little longer than anticipated. Started as a one-day-a-month project at work, it fastly turned into a weekend / evening project (winter was coming) and the first version was done in [December 2023](https://www.linkedin.com/posts/mochse_telekomsecurity-cyberdefense-raspberrypi-activity-7138560366661300224-Ccra).<br><br>
While already being an eye catcher the display was not bright enough, the resistive touchpanel and the resolution really did limit the possibilities. In consequence a new display had to be found that helped overcome the drawbacks. The Waveshare 4.3" capacitive display was a great choice with a higher resolution.<br><br>
**Bigger is better** - and in this case (pun intended) it is really true. T-Pot Mobile now supports an 8" display to make it an even bigger eye catcher!<br><br> To support the 8" display alongside the 4.3" a new case had to to be created while adjusting the code to make use of the added screen estate. <br><br>
We are very happy to share this project continiously as open source, with a huge thanks to [Telekom Security](https://geschaeftskunden.telekom.de/digitale-loesungen/cyber-security) to make this possible.<br><br>
**Create yours today, all files for 3d printing included!**

![T-Pot 8 inch 1](screenshots/tpot_8_inch_1.jpg)

![T-Pot 8 inch 2](screenshots/tpot_8_inch_2.jpg)

![T-Pot 4.3 inch 1](screenshots/tpot_43_inch_1.jpg)

![T-Pot 4.3 inch 2](screenshots/tpot_43_inch_2.jpg)

# T-Pot Mobile

<!-- vscode-markdown-toc -->
* 1. [Hardware requirements](#Hardwarerequirements)
	* 1.1. [8 inch](#inch)
	* 1.2. [4.3 inch](#inch-1)
* 2. [Requirements](#Requirements)
* 3. [Installation](#Installation)
	* 3.1. [Obtain the checkout](#Onelinerinstallation)
	* 3.2. [Manual installation](#Manualinstallation)
* 4. [LTE Stick settings](#LTESticksettings)
* 5. [Usage](#Usage)
	* 5.1. [Turn on](#Turnon)
	* 5.2. [Turn off](#Turnoff)
* 6. [T-Pot Mobile UI](#T-PotMobileUI)
	* 6.1. [Waiting for Elasticsearch](#WaitingforElasticsearch)
	* 6.2. [Stats Mode](#StatsMode)
	* 6.3. [Map Mode](#MapMode)
	* 6.4. [Touch controls and details](#OpenDialogBox)
		* 6.4.1. [Cancel](#Cancel)
		* 6.4.2. [Presentation and system status](#MapStats)
		* 6.4.3. [Reboot](#Reboot)
		* 6.4.4. [Power Off](#PowerOff)
* 7. [Maintenance and Troubleshooting](#MaintenanceandTroubleshooting)
	* 7.1. [Connect a keyboard](#Connectakeyboard)
	* 7.2. [Exit the GUI](#ExittheGUI)
	* 7.3. [Starting / Stopping T-Pot services](#StartingStoppingT-Potservices)
	* 7.4. [Cronjob](#Cronjob)
	* 7.5. [Updates](#Updates)
	* 7.6. [Network Settings](#NetworkSettings)
* 8. [3d Print Settings](#dPrintSettings)
* 9. [Assembling the parts - 8 inch](#Assemblingtheparts-8inch)
* 10. [Assembling the parts - 4.3 inch](#Assemblingtheparts-4.3inch)
* 11. [Credits](#Credits)
* 12. [Licenses](#Licenses)

<!-- vscode-markdown-toc-config
	numbering=true
	autoSave=true
	/vscode-markdown-toc-config -->
<!-- /vscode-markdown-toc -->

##  1. <a name='Hardwarerequirements'></a>Hardware requirements

T-Pot Mobile is developed specifically to make T-Pot a tangible, fully wireless honeypot using hardware components for:
<details>

<summary>

###  1.1. <a name='inch'></a>8 inch

</summary>

- [Raspberry Pi 4 model B](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/) with 8GB of RAM, 64GB microSD card
- [Waveshare 8" touch display](https://www.waveshare.com/8inch-dsi-lcd-c.htm)
- [Waveshare UPS HAT](https://www.waveshare.com/wiki/UPS_HAT) with 2 * 18650 batteries
- [ZTE MF79U Wingle CAT4-4G](https://www.amazon.de/gp/product/B08WPXRTRL) with the USB plug removed
- Nuts and standoff assortment for [M2.5](https://www.amazon.de/gp/product/B08M3BVC9Q) and [M3](https://www.amazon.de/gp/product/B08M3BVC9Q?th=1)

</details>

<details>

<summary>

###  1.2. <a name='inch-1'></a>4.3 inch

</summary>

- [Raspberry Pi 4 model B](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/) with 8GB of RAM, 64GB microSD card
- [Waveshare 4.3" touch display](https://www.waveshare.com/wiki/4.3inch_DSI_LCD), make sure to order the version including the [case](https://www.amazon.de/dp/B08LH5MFVS)
- [Waveshare UPS HAT](https://www.waveshare.com/wiki/UPS_HAT) with 2 * 18650 batteries
- [ZTE MF79U Wingle CAT4-4G](https://www.amazon.de/gp/product/B08WPXRTRL) with the USB plug removed
- [Nuts and standoff assortment](https://www.amazon.de/gp/product/B08M3BVC9Q) 

</details>

Regarding the hardware limits of the Raspberry Pi4 platform (mainly RAM and storage) T-Pot Mobile will use a `docker-compose.yml` specifically adjusted for this use case.

##  2. <a name='Requirements'></a>Requirements

- Raspberry Pi OS **Lite, Trixie (Debian 13), ARM64**. Bookworm and in-place OS upgrades are not supported.
- Qt 6 Quick/QML (including Shapes and SVG image plugins) from system packages, Mesa and a minimal Weston Wayland kiosk. No desktop, browser or XWayland is installed.
- T-Pot `dev-24.04.2`, pinned to [39d7f375](https://github.com/telekom-security/tpotce/commit/39d7f375253b446305d7941ad2f09d66a6968c96), installed with the upstream Mobile edition. This baseline builds Elasticsearch 9.5.4; the Python client remains pinned to 9.5.1.
- Prepare the microSD Card with a user i.e. `tsec` and the WiFi settings for your local network (adjustments of the Wifi settings are described [here](#network-settings))

##  3. <a name='Installation'></a>Installation

###  3.1. <a name='Onelinerinstallation'></a>Obtain the checkout
Use a complete checkout of the revision containing the Qt UI, rather than piping a moving remote installer into a shell. During development the new branch must be published or copied to the Pi before installation.

###  3.2. <a name='Manualinstallation'></a>Manual installation
Boot a fresh Trixie Lite ARM64 installation, SSH in on `tcp/22`, obtain this checkout and run as your normal login user:
```
cd tpotmobile
bash install.sh
```

Select the 4.3-inch or 8-inch display. The installer checks kernel overlays, backs up the original boot config to `config.txt.tpotmobile.bak`, and applies the profile idempotently. Conflicting custom overlays are rejected. The upstream installer receives the explicit Mobile type and pinned commit; follow its terminal prompts.

An existing `~/tpotce` is never overwritten by the fresh-install path. T-Pot generates `.env` from `env.example` and stamps `docker-compose.yml` from its Mobile edition. The mobile installer keeps both source fingerprints and sets `TPOT_TYPE=MOBILE` and `TPOT_PULL_POLICY=missing`. Initial image downloads are intentional and fail if required ARM64 images are unavailable. Subsequent starts do not refresh existing images.

The application and virtual environment are installed root-owned under `/opt/tpotmobile`. A dedicated `tpotui` account runs the compositor and UI without Docker group membership. A root-owned helper in `/usr/local/libexec` permits only container status, bounded DSI brightness, reboot and power-off through a restricted sudo policy.

Then `sudo reboot`; after T-Pot installation SSH uses `tcp/64295`. The UI starts independently of Internet and Elasticsearch readiness; T-Pot retains its network startup wait. Package versions and initial image information are recorded in `/var/lib/tpotmobile/`. Pinning a Git commit does not make registry tags immutable; retain image IDs for reproducibility.

For subsequent updates of **this Qt installation**, run `bash install.sh --ui-only` from the updated checkout. This restarts only the UI/compositor; it does not reinstall, pull images for, or stop T-Pot. It does not automatically migrate a legacy Pygame installation.

**Physical Pi acceptance is still open:** DSI touch mapping, the GPU path, UPS charging direction, brightness, whole-device RAM and battery savings require hardware validation. Software tests and synthetic screenshots do not certify these outcomes.

##  4. <a name='LTESticksettings'></a>LTE Stick settings
- Login: Factory default, adjust after setup
- SSID: Factory default, adjust after setup
- PSK: Factory default, adjust after setup
- For Telekom in Germany: Setup the LTE stick to use [APN with NAT Type 2](https://telekomhilft.telekom.de/t5/Mobilfunk/NAT-Typ-amp-APN-Einstellungen/td-p/3295081): `internet.t-d1.de`.
- Use NAT forwarding only for ports 1-64000 to avoid exposing T-Pot management ports, such as SSH.
- For DHCP / MAC settings ensure that the same IP will always be assigned to the T-Pot Wifi Adapter or NAT will break once a new IP lease starts.

##  5. <a name='Usage'></a>Usage
###  5.1. <a name='Turnon'></a>Turn on
- After turning the device on (UPS HAT power switch in on-position) the device will automatically boot and wait for the mobile network / WiFi to be fully enabled.
- The touchscreen remains usable while services start. Actual startup time depends on the SD card, network and container load.
###  5.2. <a name='Turnoff'></a>Turn off
- After [Shutting Down](#power-off) the device can be turned off (UPS HAT power switch in off-position). Always shutdown the device first to avoid damaging the elasticsearch index and / or filesystem.

##  6. <a name='T-PotMobileUI'></a>T-Pot Mobile UI
The frontend implements the approved Qt 6 Quick/QML design: a dark honeycomb/SOC theme, Telekom magenta `RGB 226/0/116`, the supplied Telekom SVG in the header, and stable honeypot colours shared by events, donuts and map markers. All interface text is English. Elasticsearch, DNS, I2C and subprocess work run in background workers, not touch handlers. Only the current page is loaded; models, animations and history are bounded.

![Qt UI, 4.3-inch synthetic development fixture](screenshots/ui_qt_43.png)
![Qt UI, 8-inch synthetic development fixture](screenshots/ui_qt_8.png)

###  6.1. <a name='WaitingforElasticsearch'></a>Waiting for Elasticsearch
- A size-adapted canonical T-Pot ANSI splash is shown during startup. It switches to Overview after a displayed splash frame and a successful event poll, without a fixed countdown. **Open UI** allows immediate access even while Elasticsearch is unavailable. The offline boot logo is generated from the same pinned upstream pixel data as the approved mockup.
- The compact header shows the clock, Wi-Fi arcs, battery icon and data/follow indicators. The 8-inch header also labels Public IP and the development baseline. Tap Wi-Fi/battery icons for numeric values and errors; charging uses an upward arrow inside the battery. Tap the data indicator for stale/connection information.
- Status indicators share a vector drawing grid and centered 46x46px touch areas, rather than mixing font glyphs with drawn icons.
- Errors and stale data are labelled. Last valid data is retained; an unavailable count is `--`, not a fabricated zero.
###  6.2. <a name='StatsMode'></a>Stats Mode
- Tap a timeframe card to select Last 1m, 15m, 1h or 24h. Cached information stays visible while the selected chart refreshes asynchronously.
- The 8-inch Overview has a full-height Alarm Intelligence panel on the left and three complete Attack Stream cards above Activity on the right. The compact view prioritizes country, IP, service, reputation and credentials with a one-line command preview; tap it for larger, complete details.
- Service includes the destination port; coordinates use degrees and compass directions. The Overview timestamp is local and compact, and AS organization text wraps between words.
- Tap Activity to open a fullscreen histogram with count/time grid. Its four timeframe buttons and **Back** are all 64x52px, with a vertical divider before Back. A warning mark indicates unavailable/refreshing statistics; cached chart timestamps stay associated with the displayed data.
- All four counts, the selected histogram, top country names/codes, honeypots and target services use one aggregation request about every 5 seconds. Donut legends include country flags; the same count formatter is used throughout: English thousands separators on 8 inches, K/M notation on 4.3 inches.
###  6.3. <a name='MapMode'></a>Map Mode
- Tap **Map** for a fullscreen map with recent event cards and 18px timestamps. Its bounded pool contains three native QML attack effects, combining ping rings and correctly projected quadratic Bezier paths. Each effect ends after 1.35 seconds. Flight paths use the event's destination geolocation; missing destination coordinates produce source-only pings, not an invented sensor location.
- Hidden/resized maps cancel effects. **System / Effects on/off** or the `--no-animations` option disables them. No animation runs in idle periods without new events.
- Map labels are kept clear of the header/event overlays and connected to their original marker positions with leader lines. Label layout does not change geographic coordinates.
- Missing location data does not discard events from the feed.
###  6.4. <a name='OpenDialogBox'></a>Touch controls and details
- Use the visible bottom navigation: **Overview**, **Map**, **Events**, **Tops**, **System**. Explicit touch controls replace the legacy swipe-to-open menu.
- Tap an event for scrollable details. Commands, credentials and requests are displayed as plain text, never executed or interpreted as markup.
- Overview initially follows the latest event. A manual selection holds its data, even if it leaves the recent-event buffer; **Follow live** resumes. Events uses two columns on 8 inches and full-width compact rows on 4.3 inches, with at least three complete fixture event cards visible. Events and Tops omit the Overview count cards.
- Event cards have subtle rounded honeypot-colour outlines; selection uses a stronger continuous outline. Distribution legends form compact right-anchored blocks, vertically centered beside the donuts, with left-aligned names and right-aligned values.
- Legend names and values have 32px spacing on 8 inches and 16px on 4.3 inches. Flags align to the text's capital height above the baseline, ignoring descenders, rather than its line box. Subtle flag outlines keep dark bands distinguishable from the panel background. Port rows share fixed label/value column widths so all bar tracks stay equal in width; fill lengths remain proportional to event counts.
- The live feed retains 200 events. Approximately once per second, acquisition uses a **fresh** point-in-time snapshot, sorted pagination, a 10-second overlap and ID deduplication. Polls are capped at 1,000 hits, with an overload notice. Snapshot open/close calls are additional to search calls.
- This is a recent-event visualization, not a lossless archive. Delayed indexing beyond the overlap, long outages and bursts can exceed its catch-up window; stored honeypot data is unaffected. Source-IP events are included without a fixed honeypot-name whitelist; Suricata, P0f and Fatt telemetry are excluded.
####  6.4.1. <a name='Cancel'></a>Cancel
- **Back** dismisses alarm details/histogram; **Close** dismisses status popovers; **Cancel** dismisses a power confirmation.
####  6.4.2. <a name='MapStats'></a>Presentation and system status
- **System / Enable demo** enables presentation mode, off by default. It rotates the five **live** views every 20 seconds. Touch pauses rotation; **System / Resume** continues it and **Disable demo** turns it off. Open details, popovers and fullscreen histograms pause rotation. No synthetic attacks are introduced.
- **System** shows CPU, RAM, temperature, Mobile container state, network information, UPS readings and a bounded 10-minute power history. System/UPS sampling is about every 5 seconds; network/container status about every 30 seconds.
- Valid discharge measurements cap brightness at 60%, respecting lower manual choices. A manual change overrides the cap until the next observed power-source transition. Unknown charging state does not change brightness. The display and honeypots stay on; screen blanking is disabled.
- Battery percentage is a voltage-based **estimate**, not a calibrated fuel gauge. Three consecutive valid discharge readings below 10% request shutdown. Missing or invalid readings never trigger power-off.
####  6.4.3. <a name='Reboot'></a>Reboot
- **System / Reboot** requires confirmation and stops honeypot operation while rebooting.
####  6.4.4. <a name='PowerOff'></a>Power Off
- **System / Power off** requires confirmation. Use it before switching off the UPS to protect the filesystem and Elasticsearch data.

##  7. <a name='MaintenanceandTroubleshooting'></a>Maintenance and Troubleshooting
###  7.1. <a name='Connectakeyboard'></a>Connect a keyboard
- For troubleshooting you can connect a keyboard.
###  7.2. <a name='ExittheGUI'></a>Exit the GUI
- Press `q` to exit the GUI.
- Use SSH or another console (for example Ctrl+Alt+F2) to log in. The kiosk owns tty1; quitting its UI does not restore the legacy tty1 login prompt.
###  7.3. <a name='StartingStoppingT-Potservices'></a>Starting / Stopping T-Pot services
- In `/etc/systemd/system` are the T-Pot systemd service files `tpot.service` and `tpotdisplay.service` located. While `tpot.service` does control the T-Pot services `tpotdisplay.service` controls the T-Pot Mobile GUI.
- Start T-Pot: `sudo systemctl start tpot.service`
- Start T-Pot Mobile GUI: `sudo systemctl start tpotdisplay.service`
- Stop T-Pot: `sudo systemctl stop tpot.service`
- Stop T-Pot Mobile GUI: `sudo systemctl stop tpotdisplay.service`
###  7.4. <a name='Cronjob'></a>Cronjob
- T-Pot Mobile will restart the device by default every day. You can change the cronjob settings with `sudo crontab -e`.
###  7.5. <a name='Updates'></a>Updates
- On Debian, T-Pot manages weekly security and Docker Engine updates (`TPOT_AUTO_UPDATES` in `~/tpotce/.env`). This is separate from container image downloads: keep `TPOT_PULL_POLICY=missing` on metered LTE and use LAN or WiFi for manual pulls.
- The T-Pot checkout is pinned (detached HEAD); do not use `git pull` to upgrade it. To deploy a newer tested baseline, use its matching tpotmobile installer on a fresh card. A UI-only update does not migrate T-Pot.
- Update tpotmobile: update the checkout, then `bash install.sh --ui-only`. Installed code is a root-owned copy; `git pull` alone does not change the running UI.
- Update docker images: `cd tpotce && docker compose -f docker-compose.yml pull`
###  7.6. <a name='NetworkSettings'></a>Network Settings
- Raspbian uses Network Manager by default.
- You can find and adjust network connections in `/etc/NetworkManager/system-connections`.
- By default you will find `preconfigured.nmconnection` which contains the settings provided by Raspberry Pi Imager.

### Development and validation

The [interactive design laboratory](tools/design/index.html) retains the
approved browser design at both display sizes. The production QML frontend
now implements it; map effects were rebuilt natively instead of reusing the
mockup's animation code.

Install the Qt/QML runtime packages listed in `install.sh`, then:
```
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python display.py --fixture --size 800x480
.venv/bin/python display.py --fixture --size 1280x800 --scenario burst
.venv/bin/python display.py --fixture --size 800x480 --view Events
.venv/bin/python display.py --fixture --size 1280x800 --view Map
.venv/bin/python display.py --fixture --size 800x480 --scenario charging
.venv/bin/python display.py --fixture --size 800x480 --boot
```
For macOS development only, install `PyQt6` into that environment; deployment uses Trixie system packages.

The separate `--fixture` mode is labelled by the amber status indicator and status/boot popovers, and never creates an Elasticsearch client, reads real hardware, or executes power/brightness commands. Scenarios: `normal`, `empty`, `burst`, `offline`, `partial`, `low-battery`, `charging`. It is not the live presentation mode. The fixture uses clearly synthetic IPs, credentials and destination coordinates.
```
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python display.py --fixture --snapshot /tmp/tpot-preview.png --size 1280x800
```
`--snapshot`, `--quit-after`, `--view` and `--boot` are fixture-only controls. `--no-animations` also works in live mode. Tests cover pagination, real SDK serialization, bounded models, both layouts, exact event visibility/control dimensions, projection, actual Bezier beam positions, effect termination/limits, held selection, presentation pausing, fixture isolation and power policies. Run `python3 tools/build_splash.py` to regenerate the offline PNGs from the pinned, already extracted ANSI data; no Internet is needed.

On a physical Pi, check touch coordinates, scrolling, confirmations, I2C charging direction and brightness across mains/battery transitions. Check `journalctl -u tpotweston -u tpotdisplay` for graphics/helper errors and inspect Qt/Mesa renderer logs to establish GPU acceleration rather than assuming it.

Compare old and new UI with identical warmed-up T-Pot, traffic, network, brightness and power source. Record process **PSS**, whole-system available RAM, CPU load, temperature/throttling, touch latency, transition frame times and UPS watts/runtime. GPU/kernel allocations are not all captured by PSS. Measure renderer savings at equal brightness separately from brightness reduction; dark LCD colours alone do not reduce backlight load. Do not publish battery/FPS improvements until measured.

For recovery, stop/restart the UI services over SSH. Review subsequent changes before restoring `config.txt.tpotmobile.bak`. Keep an SD/data backup and the original Git revision for returning to a legacy installation. `--ui-only` does not change stored honeypot data.

##  8. <a name='dPrintSettings'></a>3d Print Settings
For 3d printing we were using PLA+ filament with the following settings, depending on your usage other filament types need to be considered i.e. PETG, ABS or ASA (those remain untested regarding the case).
- #### Layers and perimeters
  - Layer height 0,2mm
  - 5 solid base and top layers with monotonic lines
  - 6 walls
- #### Infill
  - 25%
- #### Speed
  - Initial layer: 50mm/s
  - Outer wall: 60mm/s
- #### Supports enabled
    - Style: Grid
    - Top / bottom contact Z distance: 0.2 (reduce top to 0.1 may increase quality)
    - Base Pattern: Rectilinear grid
    - Pattern angle: 90°
    - Top / bottom interface layers: 2
    - Interface Pattern: Rectilinear

<details>

<summary>

##  9. <a name='Assemblingtheparts-8inch'></a>Assembling the parts - 8 inch

</summary>

####
Overview of all the parts you will need to assemble T-Pot Mobile.
![Build 1](screenshots/8inch/build1.jpg)

#### 
Insert the microSD card into the Pi4, **after** installing Raspbian. It will be harder to reach the microSD card later in the process.
![Build 2](screenshots/8inch/build2.jpg)
![Build 3](screenshots/8inch/build3.jpg)

#### 
Place the screen in front of you, face down.
![Build 4](screenshots/8inch/build4.jpg)

#### 
Align the Raspberry Pi on the standoffs and use the nuts (4 x M2.5) and standoffs (4 x M2.5x15 + 6) from the assortment to secure it. Also check the pogo pins align properly between the Pi and the display.
![Build 5](screenshots/8inch/build5.jpg)
![Build 6](screenshots/8inch/build6.jpg)

#### 
Insert the flex DSI cable and ensure the cable and socket connectors align and the pins face each other.
![Build 7](screenshots/8inch/build7.jpg)
![Build 8](screenshots/8inch/build8.jpg)
![Build 9](screenshots/8inch/build9.jpg)
![Build 10](screenshots/8inch/build10.jpg)

#### 
Install the UPS HAT on top of the Pi4.
![Build 11](screenshots/8inch/build11.jpg)
![Build 12](screenshots/8inch/build12.jpg)
![Build 13](screenshots/8inch/build13.jpg)

####
Now secure it with the standoffs (M2.5x12+6 + M2.5x10+6) as shown.
![Build 14](screenshots/8inch/build14.jpg)
![Build 15](screenshots/8inch/build15.jpg)
![Build 16](screenshots/8inch/build16.jpg)

#### 
If you are using the LTE stick you have probably soldered the power connectors to a stacking HAT. You can now place it on top of the UPS HAT.
![Build 17](screenshots/8inch/build17.jpg)
![Build 18](screenshots/8inch/build18.jpg)

####
Now is a good time to test everything before putting it into the case. Connect the power supply to the UPS HAT and switch the UPS HAT on.

#### 
Now attach the top side of the case to the display to the 3d printed case.
![Build 19](screenshots/8inch/build19.jpg)
![Build 20](screenshots/8inch/build20.jpg)
![Build 21](screenshots/8inch/build21.jpg)

###
Now screw the M3x15 standoffs (as shown) into place. In both cases (heated inserts or not) make sure to not overtighten them, as the display standoffs have the tendency to snap off (do not ask how I know that). You can also use standoffs with a shorter end.

If you use heated inserts:
- Make sure the standoffs align properly in a 90° angle, otherwise the heated inserts need re-alignment.
- While screwing the standoffs into place slightly put pressure on the same position on the front of the display, so the standoffs get a grip on the display.

![Build 22](screenshots/8inch/build22.jpg)

###
Now take the bottom of the 3d printed case and slide the LTE stick into its casket.
![Build 23](screenshots/8inch/build23.jpg)
![Build 24](screenshots/8inch/build24.jpg)
![Build 25](screenshots/8inch/build25.jpg)
![Build 26](screenshots/8inch/build26.jpg)

#### 
Hold the bottom of the case in place and screw the Phillips-head screws in. Start with the four M2.5 screws for the four inner holes and then use the four M3 for the outer holes.
Never overtighten the screws. Should they not line up properly gently take the bottom case off and do a fitting or adjustment of the holes.
![Build 27](screenshots/8inch/build27.jpg)
![Build 30](screenshots/8inch/build30.jpg)

#### 
Done. Now connect the power supply (barrel connector) and turn the UPS HAT on. Depending on your usage the UPS HAT will not fully charge the batteries if the Pi4 is in use.
![Build 31](screenshots/8inch/build31.jpg)
![Build 32](screenshots/8inch/build32.jpg)

</details>


<details>

<summary>

##  10. <a name='Assemblingtheparts-4.3inch'></a>Assembling the parts - 4.3 inch

</summary>

#### 
Make sure you ordered the display including the case, this will provide you with most of the required assembly parts, otherwise the case will not fit.

#### 
Place the display face down
![Build 1](screenshots/4.3inch/build1.jpg)

#### 
Insert the microSD card into the Pi4, **after** installing Raspbian. It will be harder to reach the microSD card later in the process.
![Build 2](screenshots/4.3inch/build2.jpg)

#### 
Screw the smallest standoffs in (included in the display / case package).
![Build 3](screenshots/4.3inch/build3.jpg)

#### 
Align the Raspberry Pi on the standoffs and use the nuts (4 x M2.5) and standoffs (4 x M2.5 + 6) from the assortment to secure it.
![Build 4](screenshots/4.3inch/build4.jpg)
![Build 5](screenshots/4.3inch/build5.jpg)

#### 
Insert the flex DSI cable and ensure the cable and socket connectors align and the pins face each other.
![Build 6](screenshots/4.3inch/build6.jpg)

####
Now screw the standoffs with the short end into the remaining four threads of the display backplate.
![Build 7](screenshots/4.3inch/build7.jpg)
![Build 8](screenshots/4.3inch/build8.jpg)

#### 
Install the UPS HAT on top of the Pi4 and secure it with the four phillips-head screws.
![Build 9](screenshots/4.3inch/build9.jpg)
![Build 10](screenshots/4.3inch/build10.jpg)

####
Add the remaining standoffs.
![Build 11](screenshots/4.3inch/build11.jpg)

####
Insert the batteries and be careful about polarity.
![Build 12](screenshots/4.3inch/build12.jpg)
![Build 13](screenshots/4.3inch/build13.jpg)
![Build 14](screenshots/4.3inch/build14.jpg)

#### 
If you are using the LTE stick you have probably soldered the power connectors to a stacking HAT. You can now place it on top of the UPS HAT.
![Build 15](screenshots/4.3inch/build15.jpg)

####
Now is a good time to test everything before putting it into the case. Connect the power supply to the UPS HAT and switch the UPS HAT on.
![Build 16](screenshots/4.3inch/build16.jpg)

#### 
Now put the LTE stick back into its case, insert the SIM card (which at this point should be setup not to require a PIN) and slide the LTE stick into its casket of the 3d printed case.

####
Slide the components carefully into the case and make sure not to damage the ribbon cable of the display.
![Build 17](screenshots/4.3inch/build17.jpg)
![Build 18](screenshots/4.3inch/build18.jpg)

#### 
Hold the display in place and turn the case upside down to secure the standoffs in the case using the Phillips-head screws.
![Build 19](screenshots/4.3inch/build19.jpg)

#### 
Done. Now connect the power supply (barrel connector) and turn the UPS HAT on. Depending on your usage the UPS HAT will only fully charge the batteries if the USB-C power supply for the Pi4 is connected as well.
![Build 20](screenshots/4.3inch/build20.jpg)

</details>

##  11. <a name='Credits'></a>Credits
- Thanks to everyone who gave their feedback and thus leading the project to v3!
- Thanks to [Thomas Tschersich](https://www.linkedin.com/in/thomas-tschersich/) and [Thomas Breitbach](https://www.linkedin.com/in/dr-thomas-breitbach-34a519159/) who have T-Pot Mobile always readily available for our customers at [Telekom-Security](https://geschaeftskunden.telekom.de/digitale-loesungen/cyber-security).

##  12. <a name='Licenses'></a>Licenses
- Flags are provided by [Flagpedia](https://flagpedia.net).
- Display dtbo and ina219 module are provided by [Waveshare](https://www.waveshare.com), all copyrights apply.
- DTS overlays are provided by [RaspberryPi](https://github.com/raspberrypi/linux?tab=License-1-ov-file#readme).
