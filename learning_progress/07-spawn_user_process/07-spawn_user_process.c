#include<linux/kernel.h>
#include<linux/init.h>
#include<linux/module.h>
#include<linux/kmod.h>

#define path "/home/kernel/cprog/hello"

MODULE_LICENSE("GPL");

static int __init process_init(void){
	char *argv[] = {path, NULL};
	char *envp[] = {"HOME=/","PATH=/sbin:/bin:/usr/sbin:/usr/bin",NULL};
	int ret;
	
	pr_info("USER_SPACE_CALL MODULE LOADED\n");
	ret = call_usermodehelper(argv[0],argv,envp,UMH_WAIT_EXEC);
	if (ret)
    		pr_info("Program exec failed, return code = %d\n", ret);
	else
    		pr_info("Program executed successfully\n");

	return 0;
	}

static void __exit process_exit(void){
	pr_info("UNLOADED THE MODULE\n");
	}

module_init(process_init);
module_exit(process_exit);
	
