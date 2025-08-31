#include<linux/kernel.h>
#include<linux/module.h>
#include<linux/init.h>
#include<linux/sched.h>
#include<linux/seq_file.h>
#include<linux/proc_fs.h>
#include<linux/rcupdate.h>

#define name "kernel_threads"
static struct proc_dir_entry *entry;

static int kernel_thread_show(struct seq_file *m,void *v){
	struct task_struct *p;
	int count =0;
	rcu_read_lock();
	for_each_process(p){
	if(p->flags & PF_KTHREAD){
		seq_printf(m, "pid=%d comm=%s state=%c\n",
           p->pid, p->comm,
           task_state_to_char(p));  
            count++;
        }
	}
	rcu_read_unlock();
	seq_printf(m,"\nTotal number of kernel threads found  = %d \n",count);
	return 0;
}

static int kt_open(struct inode *inode,struct file *file){
	return single_open(file,kernel_thread_show,NULL);
	}
	
static const struct proc_ops myops = {
	.proc_open = kt_open,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
};

static int __init kernel_init(void){
	entry = proc_create(name , 0, NULL,&myops);
	if(!entry){
		return -ENOMEM;
	}
	pr_info("Module loaded\n");
	pr_info("proc file loaded at proc/%s \n",name);
	return 0;
}

static void __exit kernel_exit(void){
	proc_remove(entry);
	pr_info("Module unloaded\n");
	}
	
MODULE_LICENSE("GPL");
module_init(kernel_init);
module_exit(kernel_exit);

