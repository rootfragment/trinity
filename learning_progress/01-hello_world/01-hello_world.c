#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>

MODULE_LICENSE("GPL");

static int __init hello(void) {
    printk(KERN_INFO "HELLO WORLD\n");
    return 0;
}

static void __exit hello_exit(void) {
    printk(KERN_INFO "BYE WORLD\n");
}

module_init(hello);
module_exit(hello_exit);
