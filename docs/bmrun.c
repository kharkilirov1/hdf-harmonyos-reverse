/* bmrun: run a command with timeout, log status to stderr (console) and file.
 * usage: bmrun <sec> <logfile> <timeout_sec> <cmd> [args...]
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
		fprintf(stderr, "BMRUN usage: bmrun sec log timeout cmd args...\n");
		return 2;
	}
	int delay = atoi(argv[1]);
	int tmo = atoi(argv[3]);
	mkdir("/data/diag", 0777);
	chmod("/data/diag", 0777);
	sleep(delay);

	char rcpath[256];
	snprintf(rcpath, sizeof rcpath, "%s.rc", argv[2]);
	FILE *rc = fopen(rcpath, "w");
	pid_t pid = fork();
	if (pid == 0) {
		int fd = open(argv[2], O_WRONLY | O_CREAT | O_TRUNC, 0644);
		if (fd >= 0) {
			dup2(fd, 1);
			dup2(fd, 2);
			close(fd);
		}
		execv(argv[4], &argv[4]);
		fprintf(stderr, "BMRUN exec-failed errno\n");
		_exit(127);
	}
	if (pid < 0) {
		fprintf(stderr, "BMRUN fork-failed\n");
		if (rc) { fprintf(rc, "fork-failed\n"); fclose(rc); }
		return 1;
	}
	int st = 0, waited = 0;
	for (;;) {
		pid_t r = waitpid(pid, &st, WNOHANG);
		if (r == pid)
			break;
		if (waited >= tmo) {
			kill(pid, SIGKILL);
			waitpid(pid, &st, 0);
			fprintf(stderr, "BMRUN cmd=%s TIMEOUT after %ds\n", argv[4], tmo);
			if (rc) { fprintf(rc, "TIMEOUT %ds\n", tmo); fclose(rc); }
			return 0;
		}
		sleep(1);
		waited++;
	}
	if (WIFEXITED(st)) {
		fprintf(stderr, "BMRUN cmd=%s RC=%d after %ds\n", argv[4], WEXITSTATUS(st), waited);
		if (rc) { fprintf(rc, "RC=%d %ds\n", WEXITSTATUS(st), waited); fclose(rc); }
	} else if (WIFSIGNALED(st)) {
		fprintf(stderr, "BMRUN cmd=%s SIGNAL=%d after %ds\n", argv[4], WTERMSIG(st), waited);
		if (rc) { fprintf(rc, "SIGNAL=%d %ds\n", WTERMSIG(st), waited); fclose(rc); }
	}
	return 0;
}
