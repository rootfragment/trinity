#include<linux/module.h>
#include<linux/kernel.h>
#include<linux/init.h>
#include<linux/jiffies.h>
#include<linux/sched.h>
#include<linux/seq_file.h>
#include<linux/proc_fs.h>

#define NAME "custlog"

static unsigned long start_jiffies;
static struct proc_dir_entry *entry;

static int custlog_show(struct seq_file *m ,void *v){
	seq_printf(m, "hello , im alive\n");
	seq_printf(m, "System uptime = %lu\n",jiffies/HZ);
	seq_printf(m, "current process = %s\n",current->comm);
	seq_printf(m, "current pid = %d\n",current->pid);
	return 0;
}

static int custlog_open(struct inode *inode,struct file *file){
	return single_open(file,custlog_show,NULL);
}

static const struct proc_ops myops ={
	.proc_open = custlog_open,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
	};
	
static int __init custlog_init(void){
	start_jiffies = jiffies;
	entry =proc_create(NAME,0,NULL,&myops);
	if(!entry)
		return -ENOMEM;
	pr_info("Loaded module\n");
	pr_info("/proc/%s created\n",NAME);
	return 0;
}

static void __exit custlog_exit(void){
	proc_remove(entry);
	pr_info("bye cruel world\n");
	}
MODULE_LICENSE("GPL");
module_init(custlog_init);
module_exit(custlog_exit);
	

