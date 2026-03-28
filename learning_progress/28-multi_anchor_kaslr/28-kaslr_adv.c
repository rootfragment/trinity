#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/kprobes.h>

MODULE_LICENSE("GPL");

struct syscall_anchor {
    const char *name;
    unsigned long static_addr;
};

static struct syscall_anchor anchors[] = {
#ifdef SYSCALL1_NAME
    {SYSCALL1_NAME, STATIC_ADDR1},
#endif
#ifdef SYSCALL2_NAME
    {SYSCALL2_NAME, STATIC_ADDR2},
#endif
#ifdef SYSCALL3_NAME
    {SYSCALL3_NAME, STATIC_ADDR3},
#endif
};

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
    unsigned long kaslr_offset = 0;
    unsigned long first_offset = 0;
    int i;
    int matches = 0;

    if (resolve_kallsyms()) {
        pr_err("KASLR Finder: Failed to resolve kallsyms_lookup_name\n");
        return -1;
    }

    if (ARRAY_SIZE(anchors) == 0) {
        pr_err("KASLR Finder: No syscall anchors defined. Check Makefile/System.map.\n");
        return -EINVAL;
    }

    pr_info("KASLR Finder: Verifying across %zu symbols\n", ARRAY_SIZE(anchors));

    for (i = 0; i < ARRAY_SIZE(anchors); i++) {
        runtime_addr = (unsigned long)kallsyms_lookup_name_ptr(anchors[i].name);
        if (!runtime_addr) {
            pr_err("KASLR Finder: Could not find %s at runtime\n", anchors[i].name);
            continue;
        }

        kaslr_offset = runtime_addr - anchors[i].static_addr;
        
        if (matches == 0) {
            first_offset = kaslr_offset;
            matches++;
        } else {
            if (kaslr_offset == first_offset) {
                matches++;
            } else {
                pr_warn("KASLR Finder: Mismatch for %s! Offset: 0x%lx (expected 0x%lx)\n", 
                        anchors[i].name, kaslr_offset, first_offset);
            }
        }

        pr_info("KASLR Finder: [Symbol: %s] [Static: 0x%lx] [Runtime: 0x%lx] [Offset: 0x%lx]\n", 
                anchors[i].name, anchors[i].static_addr, runtime_addr, kaslr_offset);
    }

    if (matches == ARRAY_SIZE(anchors) && matches > 0) {
        pr_info("KASLR Finder: Verified! KASLR Offset is consistently 0x%lx\n", first_offset);
    } else {
        pr_err("KASLR Finder: KASLR Offset calculation is inconsistent or incomplete! A rootkit might be present.\n");
    }

    return 0;
}

static void __exit kaslr_finder_exit(void)
{
    pr_info("KASLR Finder: Phase 1 module unloaded\n");
}

module_init(kaslr_finder_init);
module_exit(kaslr_finder_exit);
