#include<linux/init.h>
#include<linux/kernel.h>
#include<linux/module.h>
#include<linux/proc_fs.h>
#include<linux/seq_file.h>
#include<linux/string.h>
#include<linux/uaccess.h>

#define MAX_PREFIX_LEN 64

static char *prefix = "default";
module_param(prefix, charp,0444);
MODULE_PARM_DESC(prefix, "Prefix for proc entries.");

static struct proc_dir_entry *proc_dir;
static struct proc_dir_entry *proc_file;

static int mods_show(struct seq_file *m, void *v){
        seq_printf(m,"Module loaded with prefix : %s\n",prefix);
        return 0;
}

static int mods_open(struct inode *inode, struct file *file){
        return single_open(file, mods_show, NULL);
}

static const struct proc_ops myops = {
        .proc_open = mods_open,
        .proc_read = seq_read,
        .proc_lseek = seq_lseek,
        .proc_release = single_release,
};

static int __init stealth_init(void){
        char file_name[MAX_PREFIX_LEN +16];
        size_t len;
        if(!prefix)
                return -EINVAL;
        len = strlen(prefix);
        if(len == 0 || len >= MAX_PREFIX_LEN)
                return -EINVAL;
        proc_dir = proc_mkdir(prefix,NULL);
        if(!proc_dir){
                pr_err("Unable to create /proc/%s\n",prefix);
                return -ENOMEM;
        }
        snprintf(file_name,sizeof(file_name),"%s_mods",prefix);
        
        proc_file = proc_create(file_name , 0444 , proc_dir, &myops);
        if(!proc_file){
                pr_err("Failed to create proc_file.");
                remove_proc_entry(prefix,NULL);
                return -ENOMEM;
                }
        pr_info("loaded and good to go.");
        return 0;    
}

static void __exit stealth_exit(void){
        char file_name[MAX_PREFIX_LEN +16];
        snprintf(file_name,sizeof(file_name),"%s_mods",prefix);
        remove_proc_entry(file_name,proc_dir);
        remove_proc_entry(prefix,NULL);
        pr_info("Unloaded module\n");
}
module_init(stealth_init);
module_exit(stealth_exit);

MODULE_LICENSE("GPL");

