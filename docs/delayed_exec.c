#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s <sec> <logfile> <cmd> [args...]\n", argv[0]);
        return 2;
    }
    int sec = atoi(argv[1]);
    const char *logf = argv[2];
    sleep(sec);
    mkdir("/data/diag", 0777);
    int fd = open(logf, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd >= 0) {
        dup2(fd, 1);
        dup2(fd, 2);
        close(fd);
    }
    execv(argv[3], &argv[3]);
    int rc = 1;
    dprintf(1, "execv failed for %s: rc=%d\n", argv[3], rc);
    return rc;
}
