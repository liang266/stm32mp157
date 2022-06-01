# alientek #



### How to build ###

```shell
$ make stm32mp1_atk_defconfig
$ make
```



### How to deploy to sd ###

1. insert sd to pc, be sure sd device on pc

2. deploy to sd
   
   
   ```shell
   $ sudo dd if=output/images/sdcard.img of=/dev/sdx bs=10M conv=fdatasync,notrunc status=progress
   ```

