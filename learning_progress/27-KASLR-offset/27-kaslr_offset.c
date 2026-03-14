#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/kprobes.h>

MODULE_LICENSE("GPL");



#ifndef STATIC_SYSCALL_ADDR
#define STATIC_SYSCALL_ADDR 0
#endif

#define TARGET_SYMBOL "__x64_sys_getpid"

static unsigned long static_anchor_addr = STATIC_SYSCALL_ADDR;

static unsigned long (*kallsyms_lookup_name_ptr)(const char *name);

static int resolve_kallsyms(void)
{
    struct kprobe kp = {
        .symbol_name = "kallsyms_lookup_name"
    };

    int ret = register_kprobe(&kp);
    if (ret < 0) {
        return ret;
    }
    
    kallsyms_lookup_name_ptr = (void *)kp.addr;
    unregister_kprobe(&kp);
    
    return kallsyms_lookup_name_ptr ? 0 : -ENOENT;
}

static int __init kaslr_finder_init(void)
{
    unsigned long runtime_addr;
    unsigned long kaslr_offset;

    if (resolve_kallsyms()) {
        pr_err("KASLR Finder: Failed to resolve kallsyms_lookup_name\n");
        return -1;
    }

    runtime_addr = (unsigned long)kallsyms_lookup_name_ptr(TARGET_SYMBOL);
    if (!runtime_addr) {
        pr_err("KASLR Finder: Could not find %s at runtime\n", TARGET_SYMBOL);
        return -ENOENT;
    }

    kaslr_offset = runtime_addr - static_anchor_addr;

    pr_info("KASLR Finder Results: [Symbol: %s] [Static: 0x%lx] [Runtime: 0x%lx] [Offset: 0x%lx]\n", 
            TARGET_SYMBOL, static_anchor_addr, runtime_addr, kaslr_offset);

    return 0;
}

static void __exit kaslr_finder_exit(void)
{
    pr_info("KASLR Finder: Phase 1 module unloaded\n");
}

module_init(kaslr_finder_init);
module_exit(kaslr_finder_exit);
