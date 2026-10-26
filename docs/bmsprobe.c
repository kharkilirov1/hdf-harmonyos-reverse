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

static int file_contains(const char *p, const char *needle) {
    FILE *f = fopen(p, "r");
    if (!f) return 0;
    char line[1024];
    int found = 0;
    while (fgets(line, sizeof line, f)) {
        if (strstr(line, needle)) { found = 1; break; }
    }
    fclose(f);
    return found;
}

int main(int argc, char **argv) {
    int sec = argc > 1 ? atoi(argv[1]) : 400;
    sleep(sec);
    mkdir("/data/diag", 0777);
    chmod("/data/diag", 0777);
    char outp[64];
    snprintf(outp, sizeof outp, "/data/diag/bms_%d.txt", sec);
    FILE *out = fopen(outp, "w");
    if (!out) return 1;
    DIR *d = opendir("/proc");
    if (!d) { fclose(out); return 1; }
    struct dirent *e;
    while ((e = readdir(d))) {
        if (!isdigit((unsigned char)e->d_name[0])) continue;
        char path[256], comm[128] = "?", cmdline[512] = "", status[4096] = "";
        snprintf(path, sizeof path, "/proc/%s/comm", e->d_name);
        read_file(path, comm, sizeof comm);
        comm[strcspn(comm, "\n")] = 0;
        snprintf(path, sizeof path, "/proc/%s/cmdline", e->d_name);
        if (read_file(path, cmdline, sizeof cmdline) == 0)
            for (size_t i = 0; i + 1 < sizeof cmdline; i++) if (cmdline[i] == 0) cmdline[i] = ' ';
        snprintf(path, sizeof path, "/proc/%s/status", e->d_name);
        read_file(path, status, sizeof status);
        char uid[32] = "?", ppid[16] = "?", state[8] = "?";
        char *s = strstr(status, "Uid:"); if (s) sscanf(s, "Uid:\t%31s", uid);
        s = strstr(status, "PPid:"); if (s) sscanf(s, "PPid:\t%15s", ppid);
        s = strstr(status, "State:"); if (s) sscanf(s, "State:\t%7s", state);
        snprintf(path, sizeof path, "/proc/%s/maps", e->d_name);
        int has_bms = file_contains(path, "libbms.z.so");
        int has_found = file_contains(path, "libfoundation.z.so");
        fprintf(out, "%s\tppid=%s\tuid=%s\tstate=%s\tcomm=%s\tbms=%d\tfound=%d\tcmd=%s\n",
                e->d_name, ppid, uid, state, comm, has_bms, has_found, cmdline);
        if (has_bms) {
            char st[4096] = "";
            snprintf(path, sizeof path, "/proc/%s/stack", e->d_name);
            if (read_file(path, st, sizeof st) == 0) fprintf(out, "   STACK: %s\n", st);
            else fprintf(out, "   (stack unavailable)\n");
            char tdir[128];
            snprintf(tdir, sizeof tdir, "/proc/%s/task", e->d_name);
            DIR *td = opendir(tdir);
            if (td) {
                struct dirent *te;
                while ((te = readdir(td))) {
                    if (!isdigit((unsigned char)te->d_name[0])) continue;
                    char wch[256] = "", tcomm[64] = "";
                    snprintf(path, sizeof path, "%s/%s/wchan", tdir, te->d_name);
                    read_file(path, wch, sizeof wch); wch[strcspn(wch, "\n")] = 0;
                    snprintf(path, sizeof path, "%s/%s/comm", tdir, te->d_name);
                    read_file(path, tcomm, sizeof tcomm); tcomm[strcspn(tcomm, "\n")] = 0;
                    fprintf(out, "   tid %s [%s] wchan=%s\n", te->d_name, tcomm, wch);
                }
                closedir(td);
            }
        }
    }
    closedir(d);
    fclose(out);
    return 0;
}
