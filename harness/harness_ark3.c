#include <stdio.h>
#include <dlfcn.h>

int main(int argc, char **argv)
{
    const char *lib = (argc > 1) ? argv[1] : "./libark_jsruntime.so";
    printf("[ark3] target: %s\n", lib);
    void *h = dlopen(lib, RTLD_LAZY);
    if (!h) { printf("[ark3] dlopen FAILED: %s\n", dlerror()); return 1; }
    printf("[ark3] dlopen LAZY OK\n");

    const char *(*getver)(void) = (const char *(*)(void))dlsym(h, "GetAOTVersion");
    printf("[ark3] GetAOTVersion = %p\n", (void *)getver);
    if (getver) {
        const char *v = getver();
        printf("[ark3] GetAOTVersion() -> %s\n", v ? v : "(null)");
    }

    void *(*createlocal)(void) = (void *(*)(void))dlsym(h, "ark_create_local");
    printf("[ark3] ark_create_local = %p\n", createlocal);

    void *h2 = dlopen(lib, RTLD_NOW);
    printf("[ark3] dlopen NOW: %s\n", h2 ? "OK" : dlerror());
    printf("[ark3] done\n");
    return 0;
}
