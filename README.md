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
	* 3.1. [One liner installation](#Onelinerinstallation)
	* 3.2. [Manual installation](#Manualinstallation)
* 4. [LTE Stick settings](#LTESticksettings)
* 5. [Usage](#Usage)
	* 5.1. [Turn on](#Turnon)
	* 5.2. [Turn off](#Turnoff)
* 6. [T-Pot Mobile UI](#T-PotMobileUI)
	* 6.1. [Waiting for Elasticsearch](#WaitingforElasticsearch)
	* 6.2. [Stats Mode](#StatsMode)
	* 6.3. [Map Mode](#MapMode)
	* 6.4. [Open Dialog Box](#OpenDialogBox)
		* 6.4.1. [Cancel](#Cancel)
		* 6.4.2. [Map / Stats](#MapStats)
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

- Raspbian Lite, 64bit based on Raspbian / Debian Bookworm
- At least T-Pot 24.04.0 which will be installed by the T-Pot Mobile installer
- Prepare the microSD Card with a user i.e. `tsec` and the WiFi settings for your local network (adjustments of the Wifi settings are described [here](#network-settings))

##  3. <a name='Installation'></a>Installation

###  3.1. <a name='Onelinerinstallation'></a>One liner installation
`env bash -c "$(curl -sL https://github.com/telekom-security/tpotmobile/raw/main/install.sh)"`

###  3.2. <a name='Manualinstallation'></a>Manual installation
Boot the machine, SSH into Raspbian on `tcp/22`, run the following commands and follow the installer:
```
sudo apt install git
git clone https://github.com/telekom-security/tpotmobile
cd tpotmobile
bash install.sh
```

The `install.sh` script will also install T-Pot. When the installer asks for a T-Pot type, please choose `(M)obile` in order to download the correct docker images.

Then `sudo reboot` the machine, please notice after the reboot SSH will only be available via `tcp/64295`.

It takes about 8 minutes until all services are started successfully after installation.

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
- It takes roughly 8-10 minutes until all services have been started, then the first events should trickle in.
###  5.2. <a name='Turnoff'></a>Turn off
- After [Shutting Down](#power-off) the device can be turned off (UPS HAT power switch in off-position). Always shutdown the device first to avoid damaging the elasticsearch index and / or filesystem.

##  6. <a name='T-PotMobileUI'></a>T-Pot Mobile UI
The UI has been developed using Pygame (Raspbian / Debian Bookworm is fully supported and required).<br>
###  6.1. <a name='WaitingforElasticsearch'></a>Waiting for Elasticsearch
- Once the device has started the UI will wait for Elasticsearch to be available, afterwards the UI will switch into stats mode (default: Last 1h). The UI can be fully utilized once events have been written to the Elasticsearch index.
###  6.2. <a name='StatsMode'></a>Stats Mode
- A single touch will switch between the available timeframes (Last 1m, 15m, 1h, 24h).
![T-Pot 8 inch 1](screenshots/ui1.png)
###  6.3. <a name='MapMode'></a>Map Mode
- In Map Mode the UI will display the events on a map utilizing some animations.
![T-Pot 8 inch 1](screenshots/ui3.png)
###  6.4. <a name='OpenDialogBox'></a>Open Dialog Box
- Swiping up from the bottom of the screen towards the top of the screen (at least half the height of the screen) will open the dialog box.
![T-Pot 8 inch 1](screenshots/ui2.png)<br>
![T-Pot 8 inch 1](screenshots/ui4.png)<br>
####  6.4.1. <a name='Cancel'></a>Cancel
- Will exit the dialog box. 
####  6.4.2. <a name='MapStats'></a>Map / Stats
- While in Stats mode the button will be called "Map" and when pressed will open the Map mode.
- While in Map mode the button will be called "Stats" and when pressed will open the Stats mode.
####  6.4.3. <a name='Reboot'></a>Reboot
- The Reboot button will reboot the system. 
####  6.4.4. <a name='PowerOff'></a>Power Off
- The Power Off button will shut down the system. The system is designed for 24/7 operation, however it needs to be turned off using the Power Off function to avoid damaging the file system or elastic search indices.

##  7. <a name='MaintenanceandTroubleshooting'></a>Maintenance and Troubleshooting
###  7.1. <a name='Connectakeyboard'></a>Connect a keyboard
- For troubleshooting you can connect a keyboard.
###  7.2. <a name='ExittheGUI'></a>Exit the GUI
- Press `q` to exit the GUI.
- Login to the system with your username, i.e. `tsec` and the password you chose.
- You now have access to the console as with any other Raspbian / Debian installation.
###  7.3. <a name='StartingStoppingT-Potservices'></a>Starting / Stopping T-Pot services
- In `/etc/systemd/system` are the T-Pot systemd service files `tpot.service` and `tpotdisplay.service` located. While `tpot.service` does control the T-Pot services `tpotdisplay.service` controls the T-Pot Mobile GUI.
- Start T-Pot: `sudo systemctl start tpot.service`
- Start T-Pot Mobile GUI: `sudo systemctl start tpotdisplay.service`
- Stop T-Pot: `sudo systemctl stop tpot.service`
- Stop T-Pot Mobile GUI: `sudo systemctl stop tpotdisplay.service`
###  7.4. <a name='Cronjob'></a>Cronjob
- T-Pot Mobile will restart the device by default every day. You can change the cronjob settings with `sudo crontab -e`.
###  7.5. <a name='Updates'></a>Updates
- While OS updates will be installed automatically the docker image pull policy is set to `missing`. This means even if newer image versions are available `docker compose` will not pull them. If your mobile connection is perfectly fine with downloading large docker image files then you can adjust `TPOT_PULL_POLICY` in `tpotce/.env` to `always`. Otherwise install updates using a different network connection i.e. LAN / WiFi.
- Update tpotce: `cd tpotce && sudo systemctl stop tpot && git pull`
- Update tpotmobile: `cd tpotmobile && sudo systemctl stop tpotdisplay && git pull`
- Update docker images: `cd tpotce && docker compose -f docker-compose.yml pull`
###  7.6. <a name='NetworkSettings'></a>Network Settings
- Raspbian uses Network Manager by default.
- You can find and adjust network connections in `/etc/NetworkManager/system-connections`.
- By default you will find `preconfigured.nmconnection` which contains the settings provided by Raspberry Pi Imager.

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
Align the Raspberry Pi on the standoffs and use the nuts (4 x M3) and standoffs (4 x M3 + 6) from the assortment to secure it. Also check the pogo pins align properly between the Pi and the display.
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
Now secure it with the standoffs as shown.
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
Now screw the four M3 standoffs (as shown) into place. In both cases (heated inserts or not) make sure to not overtighten them, as the display standoffs have the tendency to snap off (do not ask how I know that). You can also use standoffs with a shorter end.

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
