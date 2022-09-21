#!/bin/sh
echo "Enable readonly flag on eMMC"
echo 1 > /sys/class/block/mmcblk1boot0/force_ro
echo 1 > /sys/class/block/mmcblk1boot1/force_ro
mmc bootpart enable 1 1 /dev/mmcblk1
sync
exit 0
