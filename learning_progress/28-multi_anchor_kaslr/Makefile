obj-m += 27-kaslr_offset.o

SYSCALL1 := __x64_sys_getpid
SYSCALL2 := __x64_sys_getuid
SYSCALL3 := __x64_sys_getgid

STATIC_ADDR1 := 0x$(shell sudo grep " T $(SYSCALL1)$$" /boot/System.map-$(shell uname -r) | awk '{print $$1}')
STATIC_ADDR2 := 0x$(shell sudo grep " T $(SYSCALL2)$$" /boot/System.map-$(shell uname -r) | awk '{print $$1}')
STATIC_ADDR3 := 0x$(shell sudo grep " T $(SYSCALL3)$$" /boot/System.map-$(shell uname -r) | awk '{print $$1}')

ccflags-y := -DSTATIC_ADDR1=$(STATIC_ADDR1) -DSYSCALL1_NAME='"$(SYSCALL1)"' \
             -DSTATIC_ADDR2=$(STATIC_ADDR2) -DSYSCALL2_NAME='"$(SYSCALL2)"' \
             -DSTATIC_ADDR3=$(STATIC_ADDR3) -DSYSCALL3_NAME='"$(SYSCALL3)"'

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
