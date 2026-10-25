#include <stdio.h>
#include <dlfcn.h>
#include <errno.h>
#include <string.h>

int main(int argc, char **argv)
{
    const char *lib = (argc > 1) ? argv[1] : "libark_jsruntime.so";
    printf("[ark] target: %s\n", lib);

    void *h = dlopen(lib, RTLD_NOW);
    if (h == NULL) {
        printf("[ark] dlopen NOW FAILED: %s\n", dlerror());
        return 1;
    }
    printf("[ark] dlopen NOW OK\n");

    const char *ver = (const char *)dlsym(h, "GetAOTVersion");
    printf("[ark] dlsym(GetAOTVersion) = %p\n", (void *)ver);
    if (ver) {
        const char *(*fn)(void) = (const char *(*)(void))(void *)ver;
        const char *r = fn();
        printf("[ark] GetAOTVersion() -> %s\n", r ? r : "(null)");
    }

    void *init0 = dlsym(h, "_ZN6common11BaseRuntime15InitFromDynamicEv");
    void *hasinit = dlsym(h, "_ZN6common11BaseRuntime18HasBeenInitializedEv");
    printf("[ark] dlsym(BaseRuntime::InitFromDynamic) = %p, HasBeenInitialized = %p\n", init0, hasinit);

    printf("[ark] done\n");
    return 0;
}
