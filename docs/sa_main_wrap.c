/* static launcher: exec real sa_main with LD_PRELOAD hook */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
	char **env = calloc(64, sizeof(char *));
	int n = 0;
	env[n++] = "LD_PRELOAD=/system/lib64/libsa_pub_hook.so";
	env[n++] = "PATH=/system/bin:/vendor/bin";
	env[n++] = "HOME=/";
	env[n++] = "TMPDIR=/data/local/tmp";
	env[n] = NULL;
	execve("/system/bin/sa_main.real", argv, env);
	perror("execve sa_main.real");
	return 127;
}
