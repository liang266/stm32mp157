#!/bin/sh
mmc bootpart enable 1 1 /dev/mmcblk1
sync
exit 0
