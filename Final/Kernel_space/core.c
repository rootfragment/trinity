#include <linux/init.h>
#include <linux/module.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/kprobes.h>
#include <linux/slab.h>
#include <linux/unistd.h>

#include "process.h"
#include "modules.h"
#include "socket.h"
#include "syscall.h"
#include "fs.h"

MODULE_LICENSE("GPL");

unsigned long *sys_call_table;
unsigned long *golden_sys_call_table;

static struct proc_dir_entry *proc_ps;
static struct proc_dir_entry *proc_mods;
static struct proc_dir_entry *proc_sockets;
static struct proc_dir_entry *proc_syscalls;
static struct proc_dir_entry *proc_fs;

static unsigned long (*kallsyms_lookup_name_ptr)(const char *name);

static int resolve_kallsyms(void)
{
    struct kprobe kp = {
        .symbol_name = "kallsyms_lookup_name"
    };

    int ret = register_kprobe(&kp);
    if (ret < 0) {
		pr_err("Failed to register kprobe for kallsyms_lookup_name\n");
        return ret;
	}

    kallsyms_lookup_name_ptr = (void *)kp.addr;
    unregister_kprobe(&kp);

    if (!kallsyms_lookup_name_ptr) {
		pr_err("Failed to resolve kallsyms_lookup_name\n");
        return -ENOENT;
	}

    return 0;
}


static int show_ps(struct seq_file *m, void *v)
{
	process_list(m);
	return 0;
}

static int open_ps(struct inode *inode, struct file *file)
{
	return single_open(file, show_ps, NULL);
}

static const struct proc_ops ps_fops = {
	.proc_open = open_ps,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
};


static int show_mods(struct seq_file *m, void *v)
{
	module_list(m);
	return 0;
}

static int open_mods(struct inode *inode, struct file *file)
{
	return single_open(file, show_mods, NULL);
}

static const struct proc_ops mods_fops = {
	.proc_open = open_mods,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
};

static int show_sockets(struct seq_file *m, void *v)
{
	socket_list(m);
	return 0;
}

static int open_sockets(struct inode *inode, struct file *file)
{
	return single_open(file, show_sockets, NULL);
}

static const struct proc_ops sockets_fops = {
	.proc_open = open_sockets,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
};

static int show_syscalls(struct seq_file *m, void *v)
{
	syscall_list(m);
	return 0;
}

static int open_syscalls(struct inode *inode, struct file *file)
{
	return single_open(file, show_syscalls, NULL);
}

static const struct proc_ops syscalls_fops = {
	.proc_open = open_syscalls,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
};

static int show_fs(struct seq_file *m, void *v)
{
	fs_list(m);
	return 0;
}

static int open_fs(struct inode *inode, struct file *file)
{
	return single_open(file, show_fs, NULL);
}

static const struct proc_ops fs_fops = {
	.proc_open = open_fs,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
	.proc_write = fs_write,
};

static void cleanup_proc_entries(void)
{
	if (proc_ps)
		proc_remove(proc_ps);
	if (proc_mods)
		proc_remove(proc_mods);
	if (proc_sockets)
		proc_remove(proc_sockets);
	if (proc_syscalls)
		proc_remove(proc_syscalls);
	if (proc_fs)
		proc_remove(proc_fs);
}

static int __init rk_init(void)
{
	int ret;
	pr_info("Argus: Initializing.\n");

	ret = resolve_kallsyms();
	if (ret)
		return ret;

	sys_call_table = (unsigned long *)kallsyms_lookup_name_ptr("sys_call_table");
	if (!sys_call_table) {
		pr_err("Failed to get sys_call_table address\n");
		return -ENOENT;
	}

	golden_sys_call_table = kmalloc_array(NR_syscalls, sizeof(unsigned long), GFP_KERNEL);
	if (!golden_sys_call_table) {
		pr_err("Failed to allocate memory for golden_sys_call_table\n");
		return -ENOMEM;
	}
	memcpy(golden_sys_call_table, sys_call_table, NR_syscalls * sizeof(unsigned long));

	proc_ps = proc_create("rk_ps", 0444, NULL, &ps_fops);
	if (!proc_ps) {
		pr_err("Failed to create /proc/rk_ps\n");
		kfree(golden_sys_call_table);
		return -ENOMEM;
	}

	proc_mods = proc_create("rk_mods", 0444, NULL, &mods_fops);
	if (!proc_mods) {
		pr_err("Failed to create /proc/rk_mods\n");
		cleanup_proc_entries();
		kfree(golden_sys_call_table);
		return -ENOMEM;
	}

	proc_sockets = proc_create("rk_sockets", 0444, NULL, &sockets_fops);
	if (!proc_sockets) {
		pr_err("Failed to create /proc/rk_sockets\n");
		cleanup_proc_entries();
		kfree(golden_sys_call_table);
		return -ENOMEM;
	}

	proc_syscalls = proc_create("rk_syscalls", 0444, NULL, &syscalls_fops);
	if(!proc_syscalls) {
		pr_err("Failed to create /proc/rk_syscalls\n");
		cleanup_proc_entries();
		kfree(golden_sys_call_table);
		return -ENOMEM;
	}

	proc_fs = proc_create("rk_fs", 0666, NULL, &fs_fops);
	if (!proc_fs) {
		pr_err("Failed to create /proc/rk_fs\n");
		cleanup_proc_entries();
		kfree(golden_sys_call_table);
		return -ENOMEM;
	}

	pr_info("Argus: Proc files created.\n");
	return 0;
}

static void __exit rk_exit(void)
{
	cleanup_proc_entries();
	if (golden_sys_call_table)
		kfree(golden_sys_call_table);
	pr_info("Argus: Exiting and cleaning up proc files.\n");
}

module_init(rk_init);
module_exit(rk_exit);
