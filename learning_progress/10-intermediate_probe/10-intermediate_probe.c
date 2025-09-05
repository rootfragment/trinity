#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/init.h>
#include <linux/uaccess.h>
#include <linux/kprobes.h>
#include <linux/sched.h>

MODULE_LICENSE("GPL");

#define BUFF 256

static int handler_pre(struct kprobe *kp, struct pt_regs *regs)
{
    const char __user *filename_u;
    char pathname[BUFF];
    umode_t mode;


    filename_u = (const char __user *)regs->di;
    mode       = (umode_t)regs->si;

    if (filename_u) {
        long copied = strncpy_from_user(pathname, filename_u, BUFF);
        if (copied < 0)
            strscpy(pathname, "<FAULT>", BUFF);
        else if (copied >= BUFF)
            pathname[BUFF - 1] = '\0';
    } else {
        strscpy(pathname, "<NULL>", BUFF);
    }

    pr_info("[mkdir-probe] pid=%d comm=%s path=%s mode=%#o\n",
            current->pid, current->comm, pathname, mode);

    return 0;
}

static struct kprobe kp = {
    .symbol_name = "__x64_sys_mkdir",
    .pre_handler = handler_pre,
};

static int __init probe_entry(void)
{
    int ret = register_kprobe(&kp);
    if (ret < 0) {
        pr_info("Probe registration failed %d\n", ret);
        return ret;
    }
    pr_info("Probe registered\n");
    return 0;
}

static void __exit probe_exit(void)
{
    unregister_kprobe(&kp);
    pr_info("Probe removed.\n");
}

module_init(probe_entry);
module_exit(probe_exit);

