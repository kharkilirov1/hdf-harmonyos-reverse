#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
#include <dlfcn.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#define HDF_IOCTL_WRITE_READ 0x6201
#define FAKE_FD 1000

struct hdf_write_read_buf {
    uint32_t write_size;
    uint32_t write_consumed;
    uint64_t write_buffer;
    uint32_t read_size;
    uint32_t read_consumed;
    uint64_t read_buffer;
    int32_t  cmd_code;
};

static int fake_fd_open = -1;
static FILE *logfp;

static void logline(const char *fmt, ...)
{
    if (logfp == NULL) {
        logfp = fopen("/tmp/hdf_shim.log", "a");
    }
    va_list ap;
    va_start(ap, fmt);
    if (logfp != NULL) {
        vfprintf(logfp, fmt, ap);
        fflush(logfp);
    }
    va_end(ap);
}

static int is_platform_node(const char *path)
{
    if (path == NULL) return 0;
    return strstr(path, "HDF_PLATFORM_") != NULL;
}

int open(const char *path, int flags, ...)
{
    static int (*real_open)(const char *, int, ...) = NULL;
    if (real_open == NULL) real_open = dlsym(RTLD_NEXT, "open");

    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap);
    }

    if (is_platform_node(path)) {
        fake_fd_open = FAKE_FD;
        logline("[shim] open(%s) -> FAKE_FD %d (kernel-side stand-in)\n", path, FAKE_FD);
        return FAKE_FD;
    }
    if (flags & O_CREAT) return real_open(path, flags, mode);
    return real_open(path, flags);
}

int openat(int dirfd, const char *path, int flags, ...)
{
    static int (*real_openat)(int, const char *, int, ...) = NULL;
    if (real_openat == NULL) real_openat = dlsym(RTLD_NEXT, "openat");

    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap);
    }
    if (is_platform_node(path)) {
        fake_fd_open = FAKE_FD;
        logline("[shim] openat(%s) -> FAKE_FD %d\n", path, FAKE_FD);
        return FAKE_FD;
    }
    if (flags & O_CREAT) return real_openat(dirfd, path, flags, mode);
    return real_openat(dirfd, path, flags);
}

int close(int fd)
{
    static int (*real_close)(int) = NULL;
    if (real_close == NULL) real_close = dlsym(RTLD_NEXT, "close");
    if (fd == FAKE_FD) {
        logline("[shim] close(FAKE_FD)\n");
        return 0;
    }
    return real_close(fd);
}

int ioctl(int fd, int request, ...)
{
    static int (*real_ioctl)(int, int, ...) = NULL;
    if (real_ioctl == NULL) real_ioctl = dlsym(RTLD_NEXT, "ioctl");

    va_list ap; va_start(ap, request);
    void *arg = va_arg(ap, void *);
    va_end(ap);

    if (fd == FAKE_FD && (unsigned long)request == HDF_IOCTL_WRITE_READ) {
        struct hdf_write_read_buf *b = (struct hdf_write_read_buf *)arg;
        logline("[shim] ioctl(FAKE_FD, 0x%lx /*HDF_WRITE_READ*/, arg=%p)\n",
                request, arg);
        if (b != NULL) {
            logline("[shim]   HdfWriteReadBuf: writeSize=%u writeConsumed=%u writeBuffer=0x%llx "
                    "readSize=%u readConsumed=%u readBuffer=0x%llx cmdCode=%d\n",
                    b->write_size, b->write_consumed,
                    (unsigned long long)b->write_buffer,
                    b->read_size, b->read_consumed,
                    (unsigned long long)b->read_buffer, b->cmd_code);
            if (b->write_buffer != 0 && b->write_size > 0 && b->write_size < 4096) {
                unsigned char *p = (unsigned char *)(uintptr_t)b->write_buffer;
                logline("[shim]   sbuf payload (%u bytes, first 32): ", b->write_size);
                for (uint32_t i = 0; i < b->write_size && i < 32; i++)
                    logline("%02x", p[i]);
                logline("\n");
            }
            /* стаб-драйвер:
               cmdCode==1 (I2C_IO_OPEN)  -> кладём в reply handle (uint64),
               остальные (0 = TRANSFER, 2 = CLOSE) -> пустой reply. */
            if (b->read_buffer != 0 && b->read_size >= 8) {
                uint64_t handle = 0x4844465f49324331ULL; /* "HDF_I2C1" */
                memcpy((void *)(uintptr_t)b->read_buffer, &handle, sizeof(handle));
                b->read_consumed = 8;
            } else {
                b->read_consumed = 0;
            }
        }
        return 0;
    }
    return real_ioctl(fd, request, arg);
}
