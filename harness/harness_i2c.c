#include <stdio.h>
#include <stdint.h>
#include <dlfcn.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>

typedef void *DevHandle;

struct I2cMsg {
    uint16_t addr;
    uint16_t flags;
    uint8_t *buf;
    uint32_t len;
};

int main(int argc, char **argv)
{
    const char *lib = (argc > 1) ? argv[1] : "/system/lib64/libhdf_platform.z.so";
    int bus = (argc > 2) ? atoi(argv[2]) : 0;

    void *h = dlopen(lib, RTLD_NOW);
    if (h == NULL) {
        printf("[harness] dlopen FAILED: %s\n", dlerror());
        return 2;
    }
    printf("[harness] dlopen OK: %s\n", lib);

    DevHandle (*pOpen)(int16_t) = (DevHandle (*)(int16_t))dlsym(h, "I2cOpen");
    int32_t (*pClose)(DevHandle) = (int32_t (*)(DevHandle))dlsym(h, "I2cClose");
    int32_t (*pTransfer)(DevHandle, struct I2cMsg *, int16_t) =
        (int32_t (*)(DevHandle, struct I2cMsg *, int16_t))dlsym(h, "I2cTransfer");

    printf("[harness] I2cOpen=%p I2cTransfer=%p I2cClose=%p\n",
           (void *)pOpen, (void *)pTransfer, (void *)pClose);
    if (pOpen == NULL || pTransfer == NULL) {
        printf("[harness] dlsym FAILED: %s\n", dlerror());
        return 3;
    }

    errno = 0;
    DevHandle d = pOpen((int16_t)bus);
    int e = errno;
    printf("[harness] I2cOpen(%d) -> %p, errno=%d (%s)\n", bus, d, e, strerror(e));

    if (d != NULL) {
        uint8_t tx = 0xA5;
        struct I2cMsg msg = { .addr = 0x50, .flags = 0, .buf = &tx, .len = 1 };
        errno = 0;
        int32_t r = pTransfer(d, &msg, 1);
        printf("[harness] I2cTransfer(addr=0x50, len=1) -> %d, errno=%d (%s)\n",
               r, errno, strerror(errno));
        if (pClose != NULL) {
            pClose(d);
            printf("[harness] I2cClose done\n");
        }
        return 0;
    }
    return 1;
}
