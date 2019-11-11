#!/bin/bash
# Raspberry Pi SPI device installation script.
# (C) Mark Blakeney, blakeney.mark@gmail.com, 2013.

USER="${SUDO_USER:-pi}"
BLFILE="/etc/modprobe.d/raspi-blacklist.conf"
BOFILE="/boot/config.txt"
RLFILE="/etc/udev/rules.d/50-spi.rules"

usage() {
    echo "Usage: $(basename $0) [-options]"
    echo "Options:"
    echo "-r <remove/uninstall>"
    exit 1
}

SPIRULE='KERNEL=="spidev*", GROUP="spi", MODE="0660"'

REMOVE=0
while getopts r c; do
    case $c in
    r) REMOVE=1;;
    ?) usage;;
    esac
done

shift $((OPTIND - 1))

if [ $# -ne 0 ]; then
    usage
fi

if [ "$(id -un)" != "root" ]; then
    echo "Must be root, e.g. run using sudo" >&2
    exit 1
fi

if [ $REMOVE -eq 0 ]; then
    echo "Adding $USER to spi group .."
    groupadd spi
    gpasswd -a $USER spi
    echo
    echo "Creating udev spi rules file .."
    echo "$SPIRULE" >$RLFILE
    echo
    if [ -f $BLFILE ]; then
	echo "Removing blacklist for spi-bcm2708 .."
	sed -i "/^blacklist *spi-bcm2708/s/^/#/" $BLFILE
    fi
    if [ -f $BOFILE ]; then
	if ! grep -q "^dtparam=spi=on" $BOFILE; then
	    echo "Adding SPI to device tree"
	    echo "dtparam=spi=on" >>$BOFILE
	else
	    echo "SPI already added to device tree"
	fi
    fi
    modprobe spi-bcm2708 2>/dev/null
else
    if [ -f $BLFILE ]; then
	echo "Restoring blacklist for spi-bcm2708 .."
	sed -i "/^#blacklist *spi-bcm2708/s/^#//" $BLFILE
    fi
    modprobe -r spi-bcm2708
    if [ -f $BOFILE ]; then
	if grep -q "^dtparam=spi=on" $BOFILE; then
	    echo "Removing SPI from device tree"
	    sed -i "/^dtparam=spi=on$/d" $BOFILE
	else
	    echo "SPI already removed from device tree"
	fi
    fi
    echo
    echo "Removing udev spi rules file .."
    rm -f $RLFILE
    echo
    echo "Removing $USER from spi group .."
    gpasswd -d $USER spi
    groupdel spi
fi

echo
echo "Reloading udev rules .."
udevadm control --reload-rules
echo "You need to reboot this host."
exit 0
