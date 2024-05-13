#!/usr/bin/env bash
dtc -@ -I dts -O dtb -o piscreen.dtbo piscreen.dts
sudo cp piscreen.dtbo ../../settings
