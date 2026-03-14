obj-m += 27-kaslr_offset.o


SYSCALL_SYMBOL := __x64_sys_getpid

STATIC_ADDR := 0x$(shell sudo grep " T $(SYSCALL_SYMBOL)$$" /boot/System.map-$(shell uname -r) | awk '{print $$1}')

EXTRA_CFLAGS_kaslr_offset_finder.o := -DSTATIC_SYSCALL_ADDR=$(STATIC_ADDR) -DSYSCALL_SYMBOL_NAME='"$(SYSCALL_SYMBOL)"'

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
