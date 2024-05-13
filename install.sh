#!/usr/bin/env bash

# one liner install:
# env bash -c "$(curl -sL https://github.com/telekom-security/tpotmobile/raw/main/install.sh)"

echo "##########################"
echo "# T-Pot Mobile Installer #"
echo "##########################"
echo

CONFIG_FILE="/boot/config.txt"

######
# Go to home folder, install updates and clone repositories
######

cd $HOME
sudo apt update
sudo apt dist-upgrade -y
sudo apt install git exa mesa-utils micro python3 python3-pygame python3-pip unattended-upgrades -y
#sudo rpi-update
git clone https://github.com/telekom-security/tpotmobile
git clone https://github.com/telekom-security/tpotce

######
# Setup configs
######

# Function to set dtoverlay for DSI display
set_dsi_display() {
    sudo sed --follow-symlinks -i 's/^dtoverlay=.*/dtoverlay=vc4-kms-v3d/' $CONFIG_FILE
    sudo raspi-config nonint do_spi 1 # 0 is enable, 1 is disable
}

echo "# Setting up Waveshare 4.3inch capacitive display ..."
set_dsi_display

echo
echo "# Now setting up T-Pot Mobile. Please be patient ..."
sudo raspi-config nonint do_i2c 0 # 0 is enable, 1 is disable - for UPS HAT
python3 -m venv --system-site-packages tpotmobile/
cd tpotmobile
source bin/activate
pip3 install -r requirements.txt
deactivate
cd $HOME
sudo cp tpotmobile/settings/20auto-upgrades /etc/apt/apt.conf.d/20auto-upgrades
sudo bash -c "sed s/'\$LOGNAME'/${LOGNAME}/g tpotmobile/settings/tpotdisplay.service > /etc/systemd/system/tpotdisplay.service"
sudo chmod 644 /etc/systemd/system/tpot* /etc/apt/apt.conf.d/20auto-upgrades
sudo chown root /etc/systemd/system/tpot* /etc/apt/apt.conf.d/20auto-upgrades
sudo systemctl enable tpotdisplay.service
echo
echo "# Now setting up T-Pot. Please be patient ..."
cd tpotce
bash install.sh

cd $HOME
# We do not want T-Pot to update automatically
sed -i s/TPOT_PULL_POLICY=always/TPOT_PULL_POLICY=missing/g tpotce/.env
sed -i '/^TPOT_TYPE=/c\TPOT_TYPE=MOBILE' tpotce/.env
# We need to adjust the T-Pot service
sudo bash -c "sed s/'\$LOGNAME'/${LOGNAME}/g tpotmobile/settings/tpot.service > /etc/systemd/system/tpot.service"
sudo systemctl daemon-reload
sudo systemctl enable tpot.service
# We always want T-Pot Mobile
cp tpotce/compose/mobile.yml tpotce/docker-compose.yml

echo
echo "# Done. You can reboot now."
