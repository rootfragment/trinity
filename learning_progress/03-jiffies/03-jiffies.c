#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/jiffies.h>
#include <linux/init.h>

MODULE_LICENSE("GPL");

static unsigned long start_jiffies;

static int __init jiffies_start(void) {
    start_jiffies = jiffies;
    printk(KERN_INFO "Module loaded\n");
    printk(KERN_INFO "System jiffies since boot = %lu\n", jiffies);
    printk(KERN_INFO "System uptime in seconds  = %lu\n", jiffies / HZ);
    return 0;
}

static void __exit jiffies_exit(void) {
    unsigned long end_jiffies = jiffies;
    printk(KERN_INFO "Module was online for %lu seconds\n",
           (end_jiffies - start_jiffies) / HZ);
    printk(KERN_INFO "Module unloading\n");
}

module_init(jiffies_start);
module_exit(jiffies_exit);

