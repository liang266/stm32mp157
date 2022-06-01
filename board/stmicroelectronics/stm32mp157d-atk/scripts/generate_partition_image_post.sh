#!/bin/bash

# As genimage only supports vfat uses key "files".
# The ext4 image should uses key "mountpoint" to copy files to ext4 image.
# As a result, buildroot rootfs and ext4 image both contain the same files.
#
# A possible solution is:
# - patch support/scripts/genimage.sh to allow other rootpaths to be used
# - support/scripts/genimage.sh default uses buildroot "${TARGET_DIR}" as rootpaths
#
# After build has finished and before buildroot starts packing the files into selected filesystem images
# Run generate_image_file_pre.sh run
# - generate all used image from ${TARGET_DIR} to "${BINARIES_DIR}"
# - avoid buildroot rootfs contains the same files, remove these files on rootfs
#
# After the build has finished and after Buildroot has packed the files into selected filesystem images:
# First run script generate_partition_image_post.sh
# - generate new mountpoints and copy files to mountpoints
# - the default new mountpoints locate "${BINARIES_DIR}" usually directory "output/images"
#
# Then run support/scripts/genimage.sh

new_mount_points="boot vendor userapp userdata"
new_mount_points_path="${BINARIES_DIR}"

# generate boot.src.uimg from boot.scr.cmd
mkimage -C none -A arm -T script -d ${BINARIES_DIR}/boot.src.cmd ${BINARIES_DIR}/boot.scr.uimg

# copy sw-version issue to output/images directory and generate swupdate pack wiil be use
verisons_path="board/stmicroelectronics/stm32mp157d-atk/overlay/boot"
sed "s/VERSION_NUMBER-//g; s/VERSION_CODE/`support/scripts/getver.sh`/g" ${verisons_path}/issue > "${BINARIES_DIR}"/issue
[ $? -ne 0 ] && exit 1
# 20 bytes [0-9] random
sed "s/random/`head /dev/urandom | tr -dc 0-9 | head -c 20`/g" ${verisons_path}/sw-versions > "${BINARIES_DIR}"/sw-versions
[ $? -ne 0 ] && exit 1

# partitions files, note the prefix should same to ${new_mount_points} list
boot_files="stm32mp157d-atk.dtb zImage rootfs.cpio.gz mmc0_stm32mp157d-atk_extlinux mmc1_stm32mp157d-atk_extlinux boot.scr.uimg sw-versions ko issue"
vendor_files=""
userapp_files=""
userdata_files=""

cd ${new_mount_points_path}

# clean and mkdir again
rm -rf ${new_mount_points}
mkdir -p ${new_mount_points}

# only support cp from ${BINARIES_DIR}
for point in ${new_mount_points}; do
	if ! eval rsync -arH \${${point}_files} ${point}; then
		exit 1
	fi
done

