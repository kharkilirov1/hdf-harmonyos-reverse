#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include <ctype.h>
#include <sys/stat.h>

static int read_file(const char *p, char *buf, size_t n) {
    FILE *f = fopen(p, "r");
    if (!f) return -1;
    size_t r = fread(buf, 1, n - 1, f);
    buf[r] = 0;
    fclose(f);
    return 0;
}

static void dump_one(FILE *out, const char *pid) {
    char path[256], comm[128] = "?", cmdline[1024] = "", status[4096] = "";
    snprintf(path, sizeof path, "/proc/%s/comm", pid);
    read_file(path, comm, sizeof comm);
    comm[strcspn(comm, "\n")] = 0;
    snprintf(path, sizeof path, "/proc/%s/cmdline", pid);
    if (read_file(path, cmdline, sizeof cmdline) == 0) {
        for (size_t i = 0; i + 1 < sizeof cmdline; i++) if (cmdline[i] == 0) cmdline[i] = ' ';
    }
    snprintf(path, sizeof path, "/proc/%s/status", pid);
    read_file(path, status, sizeof status);
    char uid[32] = "?", ppid[16] = "?";
    char *s = strstr(status, "Uid:");
    if (s) { sscanf(s, "Uid:\t%31s", uid); }
    s = strstr(status, "PPid:");
    if (s) { sscanf(s, "PPid:\t%15s", ppid); }
    fprintf(out, "%s\tppid=%s\tuid=%s\tcomm=%s\tcmd=%s\n", pid, ppid, uid, comm, cmdline);
}

int main(int argc, char **argv) {
    int sec = argc > 1 ? atoi(argv[1]) : 300;
    sleep(sec);
    mkdir("/data/diag", 0777);
    char outp[64];
    snprintf(outp, sizeof outp, "/data/diag/ps_%d.txt", sec);
    FILE *out = fopen(outp, "w");
    if (!out) return 1;
    DIR *d = opendir("/proc");
    if (!d) { fclose(out); return 1; }
    struct dirent *e;
    while ((e = readdir(d))) {
        if (!isdigit((unsigned char)e->d_name[0])) continue;
        dump_one(out, e->d_name);
    }
    closedir(d);
    fclose(out);
    return 0;
}
