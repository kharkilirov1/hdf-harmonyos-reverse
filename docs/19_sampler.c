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
    size_t r = fread(buf, 1, n-1, f); buf[r]=0; fclose(f); return 0;
}

static void dump_proc(FILE *out, const char *pid) {
    char path[256], buf[8192], comm[64]="?";
    snprintf(path, sizeof path, "/proc/%s/comm", pid);
    read_file(path, comm, sizeof comm);
    comm[strcspn(comm, "\n")] = 0;
    fprintf(out, "== PID %s comm=%s ==\n", pid, comm);
    snprintf(path, sizeof path, "/proc/%s/status", pid);
    if (read_file(path, buf, sizeof buf)==0) {
        char *save=NULL, *line=strtok_r(buf,"\n",&save);
        while (line) { if (!strncmp(line,"State:",6)||!strncmp(line,"Tgid:",5)||!strncmp(line,"Threads:",8)) fprintf(out,"%s\n",line); line=strtok_r(NULL,"\n",&save); }
    }
    char tdir[256]; snprintf(tdir,sizeof tdir,"/proc/%s/task",pid);
    DIR *d=opendir(tdir); if(!d){fprintf(out,"  (no task dir)\n");return;}
    struct dirent *e;
    while ((e=readdir(d))) {
        if (!isdigit((unsigned char)e->d_name[0])) continue;
        char tp[300]; snprintf(tp,sizeof tp,"%s/%s/stat",tdir,e->d_name);
        char st[2048]="";
        read_file(tp, st, sizeof st);
        /* stat: pid (comm) state ... wchan is field 35; easier read /wchan separately */
        char wch[256]=""; snprintf(tp,sizeof tp,"%s/%s/wchan",tdir,e->d_name);
        read_file(tp, wch, sizeof wch); wch[strcspn(wch,"\n")]=0;
        fprintf(out,"  tid %s state=%s wchan=%s\n", e->d_name, st, wch);
    }
    closedir(d);
    snprintf(path,sizeof path,"/proc/%s/stack",pid);
    if (read_file(path, buf, sizeof buf)==0) fprintf(out,"  -- STACK --\n%s\n", buf);
    else fprintf(out,"  (stack unavailable)\n");
}

int main(int argc, char **argv) {
    int sec = argc>1 ? atoi(argv[1]) : 300;
    sleep(sec);
    mkdir("/data/diag", 0777);
    char outp[64]; snprintf(outp,sizeof outp,"/data/diag/stack_%d.txt", sec);
    FILE *out = fopen(outp, "w");
    if (!out) return 1;
    DIR *d=opendir("/proc"); if(!d){fclose(out);return 1;}
    struct dirent *e;
    while ((e=readdir(d))) {
        if (!isdigit((unsigned char)e->d_name[0])) continue;
        char cp[128]; snprintf(cp,sizeof cp,"/proc/%s/comm",e->d_name);
        char comm[64]=""; read_file(cp, comm, sizeof comm);
        if (strstr(comm,"foundation")||strstr(comm,"sa_main")||strstr(comm,"bms")||strstr(comm,"samgr"))
            dump_proc(out, e->d_name);
    }
    closedir(d);
    fclose(out);
    return 0;
}
