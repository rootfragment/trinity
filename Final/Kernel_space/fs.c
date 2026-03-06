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
#include "fs.h"

#define MAX_PATH_LEN 256

static char target_path[MAX_PATH_LEN];
static DEFINE_MUTEX(target_path_lock);

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


void fs_list(struct seq_file *m)
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
        return;
    }
    
    ctx.base_path = kstrdup(target_path, GFP_KERNEL);
    mutex_unlock(&target_path_lock);

    if (!ctx.base_path)
        return;

    err = kern_path(ctx.base_path,
                    LOOKUP_FOLLOW | LOOKUP_DIRECTORY,
                    &path);
    if (err) {
        kfree(ctx.base_path);
        return;
    }

    dir = dentry_open(&path, O_RDONLY | O_DIRECTORY, current_cred());
    if (IS_ERR(dir)) {
        path_put(&path);
        kfree(ctx.base_path);
        return;
    }


    inode_lock_shared(file_inode(dir));
    iterate_dir(dir, &ctx.ctx);
    inode_unlock_shared(file_inode(dir));

    fput(dir);
    path_put(&path);
    kfree(ctx.base_path);
}

ssize_t fs_write(struct file *file, const char __user *buffer, size_t count, loff_t *pos)
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
