/* wait_exec: delayed run with exit-code logging and timeout.
 * usage: wait_exec <sec> <logfile> <timeout_sec> <cmd> [args...]
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <signal.h>

int main(int argc, char **argv)
{
	if (argc < 5) {
		fprintf(stderr, "usage: wait_exec sec logfile timeout cmd args...\n");
		return 2;
	}
	int delay = atoi(argv[1]);
	int tmo = atoi(argv[3]);
	mkdir("/data/diag", 0777);
	chmod("/data/diag", 0777);
	sleep(delay);
	pid_t pid = fork();
	if (pid == 0) {
		int fd = open(argv[2], O_WRONLY | O_CREAT | O_TRUNC, 0644);
		if (fd >= 0) {
			dup2(fd, 1);
			dup2(fd, 2);
			close(fd);
		}
		execv(argv[4], &argv[4]);
		_exit(127);
	}
	if (pid < 0)
		return 1;
	int st = 0, waited = 0;
	for (;;) {
		pid_t r = waitpid(pid, &st, WNOHANG);
		if (r == pid)
			break;
		if (waited >= tmo) {
			kill(pid, SIGKILL);
			waitpid(pid, &st, 0);
			FILE *f = fopen(argv[2], "a");
			if (f) { fprintf(f, "\n[TIMEOUT after %ds]\n", tmo); fclose(f); }
			return 0;
		}
		sleep(1);
		waited++;
	}
	FILE *f = fopen(argv[2], "a");
	if (f) {
		if (WIFEXITED(st))
			fprintf(f, "\n[RC=%d]\n", WEXITSTATUS(st));
		else if (WIFSIGNALED(st))
			fprintf(f, "\n[SIGNAL=%d]\n", WTERMSIG(st));
		fclose(f);
	}
	return 0;
}
