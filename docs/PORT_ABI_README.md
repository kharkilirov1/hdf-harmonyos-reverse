# HDF platform ABI — порт на cepheus (SM8150)

## 1. Strategic finding (определяет порядок работ)

```
CONFIG_DRIVERS_HDF=n   — ядро эмулятора HarmonyOS 6.1.1
CONFIG_DRIVERS_HDF=y   — ядро реального телефона (khdf, узлы /dev/HDF_PLATFORM_* в SELinux file_contexts)
```

Следствия:

- Эмулятор содержит только **uhdf** (`hdf_devmgr` работает как samgr-сервис), но без kernel-backend.
  Любой `I2cOpen` на эмуляторе возвращает ошибку — это **by design**, а не баг.
- На телефоне platform-слой (I2C/SPI/GPIO/Clock/PWM/UART/RTC/ADC/Timer) **статически в ядре** (khdf).
- Периферийные драйверы (power/audio/sensor/wifi/nfc/lcd/tp/fingerprint…) — **userspace-хосты**
  (`/vendor/bin/hdf_devhost <id> <host>`), 41 хост в `chip_prod/etc/init/hdf_devhost.cfg`.

**Первый шаг порта на cepheus — не «написать драйверы», а собрать mainline SM8150 с
`CONFIG_DRIVERS_HDF=y` и проверить, что `drivers/hdf_core` компилируется против современного ядра.**
Далее переносятся только platform-контроллеры SM8150 (это `device_soc_xiaomi`), верхние
драйверы переиспользуются как uhdf-хосты почти без изменений.

## 2. Платформенный ABI

Транспорт (подтверждён дизассемблером телефона + исходниками + живым вызовом):

```
I2cOpen/I2cTransfer/I2cClose (libhdf_platform.z.so, aarch64)
  -> HdfIoServiceBind("HDF_PLATFORM_I2C_MANAGER")
  -> HdfIoServiceAdapterObtain: access("/dev/hdf/") ? "/dev/hdf/<svc>" : "/dev/<svc>"
     realpath() + open(O_RDWR), fd -> adapter+0x38
  -> HdfSyscallAdapterDispatch:
       struct HdfWriteReadBuf {
           uint32 writeSize; uint32 writeConsumed; uint64 writeBuffer;
           uint32 readSize;  uint32 readConsumed;  uint64 readBuffer;
           int32  cmdCode;
       };
       ioctl(fd, HDF_WRITE_READ = _IO('b',1) = 0x6201, &wrBuf)
  -> kernel: HdfVNodeAdapterIoctl -> HdfVNodeAdapterServCall
       CopyFromUser(&bwr); if (writeSize|readSize > MAX_RW_SIZE(1024*1204)) -EINVAL;
       data = HdfSbufCopyFromUser(writeBuffer, writeSize);
       dispatcher->Dispatch(target, cmdCode, data, reply);
       HdfSbufCopyToUser(reply, readBuffer, readSize);
  -> HdfKIoServiceDispatch -> device->service->Dispatch(client, cmdId, data, reply)  [ABI драйвера]
```

Сервис-имена в бинаре телефона (`vendor/lib64/libhdf_platform.z.so`):
`HDF_PLATFORM_{ADC,CLOCK,GPIO,I2C}_MANAGER`, `HDF_PLATFORM_{PWM,SPI,UART}_%u`,
`HDF_PLATFORM_RTC`, `HDF_PLATFORM_TIMER_MANAGER`, `HDF_PLATFORM_WATCHDOG_%d`.

Полная таблица: `service_cmdid_table.csv`.

## 3. Статус доказательств

| Половина | Метод | Статус | Артефакт |
|---|---|---|---|
| Userspace (.so реально зовёт ioctl 0x6201) | LD_PRELOAD-шим на реальной `libhdf_platform.z.so` | **ПОДТВЕРЖДЕНО** | `02_userspace_proof.txt` |
| Kernel (ядро по ioctl 0x6201 вызывает Dispatch) | QEMU + Linux-модуль `misc_register` + ioctl | в работе | — |
| Step 0: узла на эмуляторе нет | hdc-разведка + kernel config | **ПОДТВЕРЖДЕНО** | `00_emulator_recon.txt` |

### Userspace proof — что именно видно

```
[shim] open(/dev/HDF_PLATFORM_I2C_MANAGER) -> FAKE_FD 1000
[shim] ioctl(FAKE_FD, 0x6201 /*HDF_WRITE_READ*/, arg=..)
[shim]   HdfWriteReadBuf: writeSize=4  readSize=128 cmdCode=1   <-- I2C_IO_OPEN
[shim]   sbuf payload: 00000000                                 <-- bus 0
[shim] ioctl(FAKE_FD, 0x6201, ..)
[shim]   HdfWriteReadBuf: writeSize=28 readSize=128 cmdCode=0   <-- I2C_IO_TRANSFER
[shim]   sbuf payload: 31433249 01000000 06000000 5000 0100 00000000 01000000 a5000000
                                 ^handle      ^count   ^addr flags len      data
[shim] ioctl(FAKE_FD, 0x6201, ..)
[shim]   HdfWriteReadBuf: writeSize=4  readSize=0   cmdCode=2   <-- I2C_IO_CLOSE
[shim]   sbuf payload: 31433249
```

Три вызова = три cmdId из `I2C_IO_TRANSFER=0 / I2C_IO_OPEN=1 / I2C_IO_CLOSE=2`. Структура,
номер ioctl, раскладка sbuf — совпали с исходниками буквально.

## 4. Sysroot для harness

`needed_sysroot_checklist.txt`. Ключевое:
- `libhdf_platform.z.so` -> `libhdf_utils.z.so`, `libutils.z.so`, `libhilog.so`, `libc.so` (musl)
- `libhdf_host.z.so` -> `libhdf_ipc_adapter.z.so` (IPC-ветка, HdfRemoteService)
- сборка: DevEco clang 15.0.4, `--target=x86_64-linux-ohos` (или `aarch64-linux-ohos`), sysroot
  `sdk/default/openharmony/native/sysroot`, **не** host gcc/glibc

## 5. FINAL STATUS (2026-10-25)

| Половина | Метод | Статус | Артефакт |
|---|---|---|---|
| Userspace | LD_PRELOAD-шим на реальной libhdf_platform.z.so (musl, x86_64) | ПОДТВЕРЖДЕНО | 02_userspace_proof.txt |
| Kernel | Ubuntu 24.04 + QEMU/KVM, свой .ko: misc_register + ioctl(_IO('b',1)) + Dispatch | ПОДТВЕРЖДЕНО | 03_e2e_proof.txt (dmesg) |
| End-to-end | реальная .so -> реальный chardev -> модуль -> Dispatch(cmdId, sbuf) | ПОДТВЕРЖДЕНО | 03_e2e_proof.txt |

Кросс-проверка: payload'ы в dmesg end-to-end совпадают байт-в-байт с логом LD_PRELOAD-шима
(cmdId=1: 00000000; cmdId=0: 31433249 01000000 06000000 5000 0100 00000000 01000000 a5000000;
cmdId=2: 31433249). Два независимых метода дали одинаковые данные.

Окружение kernel-half: kernel 6.8.0-147-generic (headers подставлены под uname -r, без apt upgrade),
модуль собран in-VM, VM = noble-server-cloudimg-amd64 (KVM, 4 vCPU / 4G).

---

## Linux-compat map (2026-10-25, эмпирика на QEMU/KVM, kernel 6.8.0-147)

### Доказано: грузится на Linux (musl-лоадер + библиотеки образа 7.0.0-B1)

| библиотека | метод | результат | артефакт |
|---|---|---|---|
| libhdf_platform.z.so | dlopen + вызовы I2cOpen/Transfer/Close | 3 ioctl(0x6201), cmdId 1/0/2; e2e до ядра | 02_userspace_proof.txt, 03_e2e_proof.txt |
| libark_jsruntime.so (11.5 МБ) | dlopen RTLD_LAZY и RTLD_NOW, 29 libs из образа | NOW OK 3/3; все 670 undefined разрешены | 06_arkruntime_smoke.txt |
| libsamgr_proxy.z.so | dlopen LAZY+NOW, 124 libs | LAZY OK, NOW OK | 07_samgr_ability_smoke.txt |
| libability_manager.z.so | dlopen LAZY+NOW, 124 libs | LAZY OK, NOW OK | 07_samgr_ability_smoke.txt |
| libipc_single.z.so | dlopen + IPCSkeleton::GetInstance + SetMaxWorkThreadNum(1) | dlopen OK, init -> 0 | 05_ipc_single_transport.txt |
| libace_engine_pa_ark / libace_ndk / libace_napi | статика NEEDED | все зависимости присутствуют в образе (missing=0), сами не запускались | 04_ace_needed.txt |

### Барьеры (в порядке появления)

1. hilog: AF_UNIX SOCK_DGRAM -> /dev/unix/socket/hilogInput -> ENOENT. Не блокирует загрузку, спамит.
2. binder: /dev/binder + ioctl; в mainline драйвер есть (CONFIG_ANDROID_BINDER_IPC),
   расширение CONFIG_BINDER_SENDER_INFO — патч OHOS. В наших прогонах binder не открывался
   (ленивое открытие при первом межпроцессном вызове).
3. samgr: системный сервис отсутствует; libsamgr_proxy грузится, но сервер не запущен.
4. прикладные сервисы (ability manager, ArkUI) требуют samgr/ability-серверов.

### Вывод по главному вопросу

План «адаптировать Linux под HarmonyOS-юзерспейс» жизнеспособен на ELF-уровне:
ArkRuntime (11.5 МБ, 670 undefined), samgr-клиент, ability manager и IPC-скелет грузятся и
инициализируются на обычном Linux 6.8 без единой отсутствующей библиотеки и без правок ядра.
Оставшаяся работа — не порт символов, а эмуляция системных сервисов (hilog-сервер, samgr,
binder-канал) и включение binder-драйвера с OHOS-расширениями.
