#!/bin/sh
echo "umount emmc partitions"
umount /dev/mmcblk1p*
echo "Disable readonly flag on eMMC"
echo 0 > /sys/class/block/mmcblk1boot0/force_ro
echo 0 > /sys/class/block/mmcblk1boot1/force_ro
sync
exit 0
