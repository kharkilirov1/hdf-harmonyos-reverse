#include <stdio.h>
#include <dlfcn.h>
#include <errno.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc < 2) { printf("usage: %s <lib>\n", argv[0]); return 2; }
    printf("[dl] target: %s\n", argv[1]);

    void *h = dlopen(argv[1], RTLD_LAZY);
    printf("[dl] LAZY: %s\n", h ? "OK" : dlerror());
    if (!h) return 1;
    void *h2 = dlopen(argv[1], RTLD_NOW);
    printf("[dl] NOW: %s\n", h2 ? "OK" : dlerror());
    printf("[dl] done\n");
    return 0;
}
