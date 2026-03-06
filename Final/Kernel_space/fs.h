#ifndef FS_H
#define FS_H

#include <linux/seq_file.h>
#include <linux/fs.h>

void fs_list(struct seq_file *m);
ssize_t fs_write(struct file *file, const char __user *buffer, size_t count, loff_t *pos);

#endif
