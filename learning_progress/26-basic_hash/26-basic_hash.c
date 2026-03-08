#include<linux/kernel.h>
#include<linux/module.h>
#include<linux/init.h>
#include<linux/crypto.h>
#include<linux/scatterlist.h>
#include<crypto/hash.h>

static int __init hash_basic_entry(void)
{
        struct crypto_shash *tfm;
        struct shash_desc *shash;
        char *input = "HELLO";
        unsigned char hash[32];
        int i, ret, hash_len =32;
        
        tfm = crypto_alloc_shash("sha256",0,0);
        if(IS_ERR(tfm)){
                pr_err("Failed to load sha256.\n");
                return PTR_ERR(tfm);
                }
        shash = kmalloc(sizeof(*shash) + crypto_shash_descsize(tfm), GFP_KERNEL);
        if (!shash){
                crypto_free_shash(tfm);
                return -ENOMEM;
                }
        shash->tfm = tfm;
        
        ret = crypto_shash_init(shash);
        if(ret){
                pr_info("Failed to initiate hash.\n");
                goto out_free;           
        } 
        
        ret = crypto_shash_update(shash,input,strlen(input));
        if(ret){
                pr_info("Hash update failed.\n");
                goto out_free;
        }
        ret = crypto_shash_final(shash,hash);
        if(ret){
                pr_info("Hash final failed.\n");
                goto out_free;
        }
        pr_info("sha256 of %s: ",input);
        for(i=0 ; i < hash_len ; i++){
                pr_cont("%02x",hash[i]);
                }
        pr_cont("\n");
out_free:
        kfree(shash);
        crypto_free_shash(tfm);
        return ret;           
}


static void __exit hash_exit(void){
        pr_info("Unloading hashing module");
}

MODULE_LICENSE("GPL");
module_init(hash_basic_entry);
module_exit(hash_exit);
