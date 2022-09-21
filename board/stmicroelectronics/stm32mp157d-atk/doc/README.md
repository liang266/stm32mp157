# SWUpdate Introdution

## swupdate attribute

|  name  |  Applies to   |  description  |
|:-------------------:|:----------------------:|:-------------------:|
| installed-directly  | images files |flag to indicate that image is streamed into the target without any temporary copy |
| install-if-different | images files | check image version and name with update pack |
|description |    | user-friendly description of the swupdate archive (any string)|
|hardware-compatibility |    | check board /etc/hwrevision file hardware version whether compatibility |
|create-destination | files | swupdate doesn’t copy out a file if the destination path doesn’t exists. This behavior could be changed this |

## sw-description use

### 1. when use hardware-compatibility attribute

we must have /etc/hwrevision file whether swupdate will failed

### 2. when not use hardware-compatibility attribute

this /etc/hwrevision file does not work

