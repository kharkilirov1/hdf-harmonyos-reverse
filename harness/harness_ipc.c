#include <stdio.h>
#include <dlfcn.h>

int main(int argc, char **argv)
{
    const char *lib = (argc > 1) ? argv[1] : "libipc_single.z.so";
    printf("[ipc] target: %s\n", lib);
    void *h = dlopen(lib, RTLD_LAZY);
    if (!h) { printf("[ipc] dlopen FAILED: %s\n", dlerror()); return 1; }
    printf("[ipc] dlopen OK\n");

    void *(*getinst)(void) = (void *(*)(void))dlsym(h, "_ZN4OHOS11IPCSkeleton11GetInstanceEv");
    printf("[ipc] IPCSkeleton::GetInstance = %p\n", (void *)getinst);
    if (getinst) {
        void *r = getinst();
        printf("[ipc] GetInstance() -> %p\n", r);
    }

    int (*getpid_)(void) = (int (*)(void))dlsym(h, "_ZN4OHOS11IPCSkeleton13GetCallingPidEv");
    printf("[ipc] GetCallingPid = %p\n", (void *)getpid_);

    /* пытаемся инициализировать работу IPC-потока */
    int (*setmax)(int) = (int (*)(int))dlsym(h, "_ZN4OHOS11IPCSkeleton19SetMaxWorkThreadNumEi");
    printf("[ipc] SetMaxWorkThreadNum = %p\n", (void *)setmax);
    if (setmax) {
        int r = setmax(1);
        printf("[ipc] SetMaxWorkThreadNum(1) -> %d\n", r);
    }
    printf("[ipc] done\n");
    return 0;
}
