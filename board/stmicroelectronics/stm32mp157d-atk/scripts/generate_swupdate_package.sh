#!/bin/bash
# generate swupdate update pack and
# delete some files for compilation

BOARD_PATH=board/stmicroelectronics/stm32mp157d-atk

# remove old swupdate package
rm -rf ${BINARIES_DIR}/*.swu

# run python swupdate script use swupdate.json config and output image for output/images
./${BOARD_PATH}/swupdate/pswu.py ./${BOARD_PATH}/swupdate/swupdate.json -o ${BINARIES_DIR}
[ $? -ne 0 ] && exit 1

cd ${BINARIES_DIR}

# undisplay umount message
sudo umount /mnt &> /dev/null

# use sd update
cp atk_tf_*.swu atk_tf.swu

# eg: /dev/loop0 --> loop0
#free_loop=$(sudo losetup -f | cut -d / -f 3)
# create device maps from partition tables
free_loop=$(sudo kpartx -avf sdcard.img | head -n 1| cut -d ' ' -f3)
free_loop=${free_loop%p*}

[ $? -ne 0 ] && exit 1
# wait for kpart complete
sleep 2
sudo mount -t ext4 /dev/mapper/${free_loop}p9 /mnt
if [ $? -ne 0 ]; then
	echo "mount /dev/mapper/${free_loop}p9 /mnt error"
	exit 1
fi
# rsync sdcard update pack to /mnt
sudo rsync -arH atk_tf.swu /mnt
[ $? -ne 0 ] && exit 1
sudo umount /mnt
sudo kpartx -dv sdcard.img

rm -rf $(ls -I "tf-a*" -I "u-boot*" -I "zImage" -I "*.dtb" -I "*.ext*" -I "*.cpio" -I "*.squashfs" -I "*.swu" -I "*.img" -I "*.bin") 

cd -
