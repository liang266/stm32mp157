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

rootfs_mount_points="boot stm32/vendor stm32/userapp stm32/userdata root usr/local"

for point in ${rootfs_mount_points}; do
	echo "points: ${TARGET_DIR}/${point}"
	if ! rsync -arH ${TARGET_DIR}/${point}/ "${BINARIES_DIR}"; then
		exit 1
	fi
	rm -rf ${TARGET_DIR}/${point}/*
done

if [ -d board/stmicroelectronics/stm32mp157d-atk/extra_images ]; then
	echo -n "install extra images to ${BINARIES_DIR}"
	if ! rsync -arHL board/stmicroelectronics/stm32mp157d-atk/extra_images/ "${BINARIES_DIR}"; then
		echo " failed"
		exit 1
	fi
	echo " success"
fi
