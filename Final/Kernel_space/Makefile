
obj-m += argus_lkm.o


argus_lkm-objs := core.o process.o modules.o socket.o syscall.o fs.o


all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
