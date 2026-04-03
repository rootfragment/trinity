#include <linux/module.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
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
static unsigned long kaslr_offset_result = 0;
static int kaslr_verified =0;

static struct proc_dir_entry *proc_entry;

static int kaslr_proc_show(struct seq_file *m, void *v){
        if (kaslr_verified == 1){
                seq_printf(m,"0x%lx\n", kaslr_offset_result);
        }
        else if (kaslr_verified == -1){
                seq_printf(m,"Mismatch of offsets.");
        }
        else if (kaslr_verified == -2){
                seq_printf(m,"Couldnt resolve anchor at runtime.");
        }
        else{
                seq_printf(m,"Unkown error occoured.");
             }
        return 0;
}


static int kaslr_proc_open(struct inode *inode, struct file *file){
        return single_open(file, kaslr_proc_show,NULL);
}

static const struct proc_ops kaslr_proc_ops = {
        .proc_open = kaslr_proc_open,
        .proc_read = seq_read,
        .proc_lseek = seq_lseek,
        .proc_release = single_release,
};


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

    for (i = 0; i < ARRAY_SIZE(anchors); i++) {
        runtime_addr = (unsigned long)kallsyms_lookup_name_ptr(anchors[i].name);
        if (!runtime_addr) {
            kaslr_verified = -2;
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
                kaslr_verified = -1;
            }
        }
    }

    if (kaslr_verified == 0 && matches == ARRAY_SIZE(anchors) && matches > 0) {
        kaslr_offset_result = first_offset;
        kaslr_verified = 1;
    } else {
        pr_err("KASLR Finder: KASLR Offset calculation is inconsistent or incomplete! A rootkit might be present.\n");
    }
    proc_entry = proc_create("kaslr_offset", 0444, NULL, &kaslr_proc_ops);
    if (!proc_entry) {
        pr_err("KASLR Finder: Failed to create /proc/kaslr_offset\n");
        return -ENOMEM;
    }

    pr_info("KASLR Finder: /proc/kaslr_offset created\n");

    return 0;
}

static void __exit kaslr_finder_exit(void)
{
    
    if (proc_entry)
        proc_remove(proc_entry);
    pr_info("KASLR Finder: unloaded\n");
}

module_init(kaslr_finder_init);
module_exit(kaslr_finder_exit);
