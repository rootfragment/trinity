#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/module.h>
#include <linux/sched.h>

static int __init current_process_init(void)
{
    printk(KERN_INFO "MODULE LOADED\n");
    printk(KERN_INFO "Current process = %s [PID = %d]\n",
           current->comm, current->pid);
    return 0;
}

static void __exit current_process_exit(void)
{
    printk(KERN_INFO "MODULE UNLOADED\n");
}

MODULE_LICENSE("GPL");

module_init(current_process_init);
module_exit(current_process_exit);

