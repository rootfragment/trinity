#include<linux/kernel.h>
#include<linux/module.h>
#include<linux/init.h>

MODULE_LICENSE("GPL");

static int number = 0;
static char *name = "DEFAULT_NAME";
static unsigned char letter = 'A';

module_param(name,charp,0660);
module_param(number,int,0660);
module_param(letter,byte,0660);

static int __init pass_args_init(void){
	pr_info("Module loaded\n");
	pr_info("The number is : %d\n",number);
	pr_info("The letter is : %c\n",letter);
	pr_info("The string is : %s\n",name);
	return 0;
	}

static void __exit pass_args_exit(void){
	pr_info("Module unloaded\n");
	}

module_init(pass_args_init);
module_exit(pass_args_exit);

