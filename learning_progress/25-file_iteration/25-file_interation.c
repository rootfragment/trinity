#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/uaccess.h>
#include <linux/fs.h>
#include <linux/namei.h>
#include <linux/file.h>
#include <linux/slab.h>
#include <linux/mutex.h>

#define PROC_NAME "argus_fs"
#define MAX_PATH_LEN 256

static char target_path[MAX_PATH_LEN];
static DEFINE_MUTEX(target_path_lock);
static struct proc_dir_entry *proc_entry;

struct argus_ctx {
    struct dir_context ctx;
    struct seq_file *m;
    const char *base_path;
};

static int argus_filldir(struct dir_context *ctx,
                         const char *name,
                         int namelen,
                         loff_t offset,
                         u64 ino,
                         unsigned int d_type)
{
    struct argus_ctx *actx =
        container_of(ctx, struct argus_ctx, ctx);

    struct path path;
    struct kstat stat;
    char *fullpath;
    int ret;


    if (namelen == 1 && name[0] == '.')
        return 0;
    if (namelen == 2 && name[0] == '.' && name[1] == '.')
        return 0;


    fullpath = kasprintf(GFP_KERNEL, "%s/%*s", 
                         actx->base_path, namelen, name);
    if (!fullpath)
        return -ENOMEM;

    ret = kern_path(fullpath, LOOKUP_FOLLOW, &path);
    if (ret == 0) {
        ret = vfs_getattr(&path, &stat,
                          STATX_BASIC_STATS,
                          AT_STATX_SYNC_AS_STAT);

        if (ret == 0) {
            seq_printf(actx->m, "%s | inode=%llu | size=%lld | mode=%o | uid=%u | gid=%u\n",
                       fullpath,
                       stat.ino,
                       stat.size,
                       stat.mode,
                       from_kuid(&init_user_ns, stat.uid),
                       from_kgid(&init_user_ns, stat.gid));
        }
        path_put(&path);
    }

    kfree(fullpath);
    return 0;
}


static int argus_proc_show(struct seq_file *m, void *v)
{
    struct path path;
    struct file *dir;
    struct argus_ctx ctx = {
        .ctx.actor = argus_filldir,
        .m = m,
    };
    int err;

    mutex_lock(&target_path_lock);
    if (target_path[0] == '\0') {
        mutex_unlock(&target_path_lock);
        return 0;
    }
    
    ctx.base_path = kstrdup(target_path, GFP_KERNEL);
    mutex_unlock(&target_path_lock);

    if (!ctx.base_path)
        return -ENOMEM;

    err = kern_path(ctx.base_path,
                    LOOKUP_FOLLOW | LOOKUP_DIRECTORY,
                    &path);
    if (err) {
        kfree(ctx.base_path);
        return 0;
    }

    dir = dentry_open(&path, O_RDONLY | O_DIRECTORY, current_cred());
    if (IS_ERR(dir)) {
        path_put(&path);
        kfree(ctx.base_path);
        return 0;
    }


    inode_lock_shared(file_inode(dir));
    iterate_dir(dir, &ctx.ctx);
    inode_unlock_shared(file_inode(dir));

    fput(dir);
    path_put(&path);
    kfree(ctx.base_path);
    return 0;
}

static int argus_proc_open(struct inode *inode, struct file *file)
{
    return single_open(file, argus_proc_show, NULL);
}

static ssize_t argus_proc_write(struct file *file,
                                const char __user *buffer,
                                size_t count,
                                loff_t *pos)
{
    size_t len = min_t(size_t, count, MAX_PATH_LEN - 1);

    mutex_lock(&target_path_lock);
    if (copy_from_user(target_path, buffer, len)) {
        mutex_unlock(&target_path_lock);
        return -EFAULT;
    }

    target_path[len] = '\0';

    if (len > 0 && target_path[len - 1] == '\n')
        target_path[len - 1] = '\0';

    mutex_unlock(&target_path_lock);

    return count;
}

static const struct proc_ops argus_proc_ops = {
    .proc_open = argus_proc_open,
    .proc_read = seq_read,
    .proc_lseek = seq_lseek,
    .proc_release = single_release,
    .proc_write = argus_proc_write,
};



static int __init argus_init(void)
{
    proc_entry = proc_create(PROC_NAME, 0666, NULL, &argus_proc_ops);
    if (!proc_entry)
        return -ENOMEM;

    pr_info("Argus FS module loaded\n");
    return 0;
}

static void __exit argus_exit(void)
{
    proc_remove(proc_entry);
    pr_info("Argus FS module unloaded\n");
}

MODULE_LICENSE("GPL");

module_init(argus_init);
module_exit(argus_exit);
