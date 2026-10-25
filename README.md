# HDF / HarmonyOS reverse engineering — рабочие материалы

Репозиторий содержит **артефакты и код исследования**, а не образы прошивок:
как устроен транспорт HDF (HarmonyOS Driver Foundation), как он проверен на живых
вызовах, и насколько HarmonyOS-юзерспейс переносим на обычное Linux-ядро.

Дата фиксации результатов: **2026-10-25**.

---

## Что здесь есть

```
docs/           отчёты и доказательства (00…07), сводка ABI, таблица cmdId
harness/        исходники harness'ов и LD_PRELOAD-шима (x86_64-linux-ohos)
stand/          kernel-модуль стенда (misc_register + ioctl 0x6201)
vm/             скрипты подъёма QEMU-VM и прогонов
kernel-notes/   kernel.config, kallsyms-парсер, восстановленные символы
```

## Ключевой результат 1 — контракт HDF доказан

Транспорт между юзерспейсом и ядром:

```
libhdf_platform.z.so
  -> HdfIoServiceBind("HDF_PLATFORM_I2C_MANAGER")
  -> open("/dev/HDF_PLATFORM_I2C_MANAGER")
  -> ioctl(fd, HDF_WRITE_READ = _IO('b',1) = 0x6201, &HdfWriteReadBuf)
  -> kernel: HdfVNodeAdapterIoctl -> HdfVNodeAdapterServCall
  -> Dispatch(cmdId, data, reply)   // cmdId: I2C_IO_TRANSFER=0, OPEN=1, CLOSE=2
```

`struct HdfWriteReadBuf { u32 writeSize; u32 writeConsumed; u64 writeBuffer;
u32 readSize; u32 readConsumed; u64 readBuffer; i32 cmdCode; }` — совпал поле в поле
с дизассемблером телефона и с исходниками OpenHarmony (`drivers_hdf_core`).

**Доказательства:**
- `docs/02_userspace_proof.txt` — реальная `libhdf_platform.z.so` (x86_64 musl) под
  LD_PRELOAD-шимом: три `ioctl(0x6201)` с `cmdCode=1/0/2` и одинаковыми пейлоадами.
- `docs/03_e2e_proof.txt` — та же библиотека + реальный chardev + собственный
  kernel-модуль: в `dmesg` `DISPATCH cmdId=1/0/2`, sbuf совпал байт в байт.

## Ключевой результат 2 — Linux-compat карта

Прогоны на Ubuntu 24.04 (QEMU/KVM, kernel 6.8.0-147), библиотеки из образа 7.0.0-B1,
musl-лоадер и sysroot образа:

| библиотека | результат |
|---|---|
| `libhdf_platform.z.so` | 3 ioctl(0x6201), e2e до ядра |
| `libark_jsruntime.so` (11.5 МБ, 670 undefined) | `dlopen` LAZY и NOW — OK (3/3) |
| `libsamgr_proxy.z.so` | `dlopen` LAZY и NOW — OK |
| `libability_manager.z.so` | `dlopen` LAZY и NOW — OK |
| `libipc_single.z.so` | `dlopen` OK, `IPCSkeleton::GetInstance` + `SetMaxWorkThreadNum(1) → 0` |

Барьеры, в порядке появления: hilog-сокет (`/dev/unix/socket/hilogInput`), binder
(`/dev/binder`; в mainline драйвер есть, расширение `CONFIG_BINDER_SENDER_INFO` — патч
OHOS), отсутствие samgr-сервера. ELF- и символьных барьеров нет.

Подробности: `docs/06_arkruntime_smoke.txt`, `docs/07_samgr_ability_smoke.txt`,
`docs/05_ipc_single_transport.txt`, раздел «Linux-compat map» в `docs/PORT_ABI_README.md`.

## Ключевой результат 3 — архитектура HDF на устройстве

- Ядро эмулятора DevEco: `# CONFIG_DRIVERS_HDF is not set` — platform-узлов нет by design.
- Реальное устройство: platform-слой статически в ядре (khdf), узлы `/dev/HDF_PLATFORM_*`
  видны в SELinux `file_contexts`; периферия — 41 userspace-хост через `hdf_devhost`.
- Первый шаг порта на другое железо — собрать ядро с `CONFIG_DRIVERS_HDF=y` и проверить
  компиляцию `drivers/hdf_core`, а не писать драйверы заново.

Подробности: `docs/00_emulator_recon.txt`, `docs/PORT_ABI_README.md`,
`docs/service_cmdid_table.csv`.

## Чего в репозитории нет и почему

- **Образов прошивок и OTA-пакетов** (гигабайты) — не хранятся в git.
- **Проприетарных .so из образов Huawei** (`libhdf_platform.z.so` и др.) — не
  распространяются; в отчётах указано, из какого образа они извлечены.
- **`vmlinux` / `bzImage`** — восстанавливаются из образа штатными средствами,
  в репозитории только `kernel.config` и парсер kallsyms.

## Как воспроизвести

### 1. HDF ABI (userspace)

```bash
clang --target=x86_64-linux-ohos --sysroot=<DevEco native/sysroot> \
      -O0 -o harness_i2c harness/harness_i2c.c -ldl
# запуск с реальной библиотекой образа:
LD_LIBRARY_PATH=<каталог с .so образа> \
  <образ>/system/lib/ld-musl-x86_64.so.1 ./harness_i2c ./libhdf_platform.z.so
```

### 2. Kernel-половина (QEMU-VM)

```bash
bash vm/vm_ssh.sh       # поднять Ubuntu cloud-image (KVM)
# внутри VM:
sudo apt-get install -y gcc make linux-headers-$(uname -r)
make -f <(…)            # собрать stand/module_hdfstub.c против ядра VM
sudo insmod module_hdfstub.ko
```

### 3. dlopen-тесты юзерспейса

Собрать замыкание NEEDED из образа (скрипт-подход описан в `docs/`), запускать
через musl-лоадер образа с `LD_LIBRARY_PATH`, как в `docs/06_*`, `docs/07_*`.

## Правила отчётности

В документах три уровня утверждений и никаких «вероятно»:
**доказано эмпирически** / **проверено статически** / **не проверено**.
Каждое утверждение снабжено ссылкой на файл-артефакт или команду.

## Лицензия

Код в `harness/`, `stand/`, `vm/` — MIT. Отчёты в `docs/` — CC BY 4.0.
Исходники OpenHarmony, на которые ссылаются отчёты, распространяются под их
собственными лицензиями (HDF — GPL/BSD dual).
