#include <stdio.h>
#include <dlfcn.h>
#include <errno.h>
#include <string.h>

int main(int argc, char **argv)
{
    const char *lib = (argc > 1) ? argv[1] : "libark_jsruntime.so";
    printf("[ark] target: %s\n", lib);

    errno = 0;
    void *h1 = dlopen(lib, RTLD_LAZY);
    printf("[ark] dlopen(RTLD_LAZY) = %p, errno=%d (%s)\n", h1, errno, strerror(errno));
    if (h1 == NULL) {
        const char *e = dlerror();
        printf("[ark] LAZY dlerror: %s\n", e ? e : "(null)");
        return 1;
    }
    const char *e1 = dlerror();
    if (e1) printf("[ark] LAZY pending: %s\n", e1);

    void *h2 = dlopen(lib, RTLD_NOW);
    printf("[ark] dlopen(RTLD_NOW) = %p\n", h2);
    if (h2 == NULL) {
        const char *e = dlerror();
        printf("[ark] NOW dlerror: %s\n", e ? e : "(null)");
    } else {
        printf("[ark] NOW OK — все символы разрешены\n");
    }

    /* пробуем найти типовые точки входа */
    const char *names[] = {
        "_ZN4OHOS2JSRuntimeC1EPNSt3__h10shared_ptrINS_8JSPandaVMEE",
        "_ZN4OHOS2JSRuntimeC2EPNSt3__h10shared_ptrINS_8JSPandaVMEE",
        "_ZN4OHOS4EcmaVMC1EPNS_11JSRuntimeAPIE",
        "napi_create_ark_runtime",
        "OHOS_JS_Init",
        NULL
    };
    for (int i = 0; names[i]; i++) {
        void *p = dlsym(h1, names[i]);
        printf("[ark] dlsym(%s) = %p\n", names[i], p);
    }
    return 0;
}
