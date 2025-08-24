#include<linux/module.h>
#include<linux/kernel.h>
#include<linux/init.h>
#include<linux/sched.h>
#include<linux/proc_fs.h>
#include<linux/seq_file.h>
#include<linux/rcupdate.h>

#define NAME "kernel_list"

static struct proc_dir_entry *entry;

static int show_task(struct seq_file *m ,void *v){
	struct task_struct *task;
	
	rcu_read_lock();
	for_each_process(task){
		seq_printf(m, "PID: %d | PPID: %d | COMM: %s | STATE: %u\n",
                   task->pid,
                   task->real_parent->pid,
                   task->comm,
                   task->__state);
    }
    rcu_read_unlock();

    return 0;
}

static int task_open(struct inode *inode, struct file *file){
	return single_open(file,show_task,NULL);
	}

static const struct proc_ops myops ={
	.proc_open = task_open,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
	};
	
static int __init log_init(void){
	entry = proc_create(NAME,0,NULL,&myops);
	if(!entry)
		return -ENOMEM;
	pr_info("MODULE LOADED\n");
	pr_info("at /proc/%s\n",NAME);
	return 0;
	}

static void __exit log_exit(void){
	proc_remove(entry);
	pr_info("MODULE UNLOADED\n");
	}

MODULE_LICENSE("GPL");
module_init(log_init);
module_exit(log_exit);
