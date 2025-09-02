#include<linux/kernel.h>
#include<linux/sched.h>
#include<linux/init.h>
#include<linux/kprobes.h>

MODULE_LICENSE("GPL");

static int handler_pre(struct kprobe *kp , struct pt_regs *reg){
	pr_info("[mkdir-trace] pid=%d comm=%s called mkdir\n",
            current->pid, current->comm);
    return 0;
}

static struct kprobe kp = {
	.symbol_name = "__x64_sys_mkdir",
	.pre_handler = handler_pre,
};

static int __init probe_init(void){
	pr_info("MODULE LOADED\n");
	int ret = register_kprobe(&kp);
	if (ret < 0){
	pr_info("Registering module failed error code %d\n",ret);
	return ret;
	}
	pr_info("Probe registered successfully\n");
	return 0;
}

static void __exit probe_exit(void){
	unregister_kprobe(&kp);
	pr_info("Probe removed , Unloading module \n");
}

module_init(probe_init);
module_exit(probe_exit);
