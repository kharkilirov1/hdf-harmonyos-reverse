#include <stdarg.h>
/* Stub libhilog: minimal exports needed by libhdf_platform/libhdf_utils.
   Реальный hilog бесполезен в тестовой VM (нет hilog-сервиса), поэтому
   подменяем логирование на no-op, чтобы не тянуть всю цепочку libbegetutil. */

int HiLogPrintDictNew(int type, int level, unsigned int domain, const char *tag,
                      unsigned int msgId, ...)
{
    (void)type; (void)level; (void)domain; (void)tag; (void)msgId;
    return 0;
}

int HiLogPrintDict(int type, int level, unsigned int domain, const char *tag,
                   const char *fmt, ...)
{
    (void)type; (void)level; (void)domain; (void)tag; (void)fmt;
    return 0;
}

int HiLogPrint(int type, int level, unsigned int domain, const char *tag,
               const char *fmt, ...)
{
    (void)type; (void)level; (void)domain; (void)tag; (void)fmt;
    return 0;
}
