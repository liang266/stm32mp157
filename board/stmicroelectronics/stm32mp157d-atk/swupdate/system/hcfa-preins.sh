#!/bin/sh
echo "killall progress hcq0"
killall -9 -w hcq0
sleep 2
echo "umount emmc partitions"
umount /dev/mmcblk1p*
sync
exit 0
