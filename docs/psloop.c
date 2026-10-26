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

int main(int argc, char **argv) {
    int total = argc > 1 ? atoi(argv[1]) : 400;
    int step = argc > 2 ? atoi(argv[2]) : 2;
    mkdir("/data/diag", 0777);
    FILE *out = fopen("/data/diag/psloop.txt", "w");
    if (!out) return 1;
    for (int t = 0; t < total; t += step) {
        sleep(step);
        char up[64] = "";
        read_file("/proc/uptime", up, sizeof up);
        up[strcspn(up, " ")] = 0;
        fprintf(out, "T %s", up);
        DIR *d = opendir("/proc");
        if (!d) break;
        struct dirent *e;
        while ((e = readdir(d))) {
            if (!isdigit((unsigned char)e->d_name[0])) continue;
            char cp[128], comm[64] = "?";
            snprintf(cp, sizeof cp, "/proc/%s/comm", e->d_name);
            read_file(cp, comm, sizeof comm);
            comm[strcspn(comm, "\n")] = 0;
            fprintf(out, " %s:%s", e->d_name, comm);
        }
        closedir(d);
        fprintf(out, "\n");
        fflush(out);
    }
    fclose(out);
    return 0;
}
