#include<linux/kernel.h>
#include<linux/init.h>
#include<linux/module.h>
#include<linux/sched.h>
#include<linux/proc_fs.h>
#include<linux/seq_file.h>
#include<linux/uaccess.h>

MODULE_LICENSE("GPL");

static struct proc_dir_entry *entry;

#define name "p1"

static int kernel_show(struct seq_file *m,void *v){
	struct task_struct *task;
	
	rcu_read_lock();
	
	for_each_process(task){
		seq_printf(m,"%d %s\n",task->pid,task->comm);
	}
	rcu_read_unlock();
	return 0;
}

static int kernel_task_open(struct inode *inode , struct file *file){
	return single_open(file, kernel_show , NULL);
}

static struct proc_ops myops = {
	.proc_open = kernel_task_open,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
};

static int __init kernel_entry(void){
	pr_info("Module Loaded\n");
	entry = proc_create(name,0444,NULL,&myops);
	if(!entry)
		return -ENOMEM;
	pr_info("created proc file at proc/%s\n",name);
	return 0;
}

static void __exit kernel_exit(void){
	proc_remove(entry);
	pr_info("Module Removed\n");
}

module_init(kernel_entry);
module_exit(kernel_exit);
