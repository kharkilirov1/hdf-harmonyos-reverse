# HDF / HarmonyOS reverse-engineering — контекст проекта

Дата фиксации: 2026-10-25. Правило: только доказано / проверено статически / не проверено.

---

## 1. Артефакты

| путь | что это | откуда взято | что доказывает / содержит | статус |
|---|---|---|---|---|
| `C:\Users\Kharki\Desktop\hdf_contract\00_emulator_recon.txt` | recon эмулятора + архитектурная находка | `hdc shell` на DevEco-эмуляторе 6.1.1 + `bzImage` IKCONFIG | `/dev/HDF_PLATFORM_*` отсутствуют; `CONFIG_DRIVERS_HDF=n`; `hdf_devmgr` в юзерспейсе работает | готово |
| `...\01_sanity_emulator.txt` | sanity-вызов `I2cOpen` на эмуляторе | harness (x86_64-linux-ohos) + `hdc` | dlopen/dlsym работают; `I2cOpen` → `errno=13 EACCES` (SELinux shell-домен) | готово |
| `...\02_userspace_proof.txt` | userspace-половина доказательства | LD_PRELOAD-шим + реальная `libhdf_platform.z.so` (x86_64, образ 6.1.1) | 3 вызова `ioctl(0x6201)` с `cmdCode=1/0/2` и sbuf-пейлоадами | готово |
| `...\03_e2e_proof.txt` | kernel-половина + сквозной прогон | Ubuntu 24.04 в QEMU/KVM (6.8.0-147) + `.ko` `misc_register` | dmesg: `DISPATCH cmdId=1/0/2`, sbuf совпал с userspace-логом | готово |
| `...\PORT_ABI_README.md` | сводка ABI + strategic finding | — | цепочка `.so → ioctl → Dispatch`, порядок работ для cepheus | готово |
| `...\service_cmdid_table.csv` | таблица «сервис → узел → cmdId → обёртки» | `*_if.h` + strings телефона | 10 platform-сервисов | готово |
| `...\needed_sysroot_checklist.txt` | NEEDED + требования к musl-sysroot | `readelf -d` | зависимости и требования сборки harness | готово |
| `...\harness_i2c.c` / `.exe` | harness (dlopen + I2cOpen/Transfer/Close) | DevEco clang 15.0.4, `--target=x86_64-linux-ohos` | рабочий x86_64 musl-бинар | готово |
| `...\shim_ioctl.c` / `.so` | LD_PRELOAD-шим ядра (open/openat/ioctl/close) | DevEco clang | пользовательская половина доказательства | готово |
| `...\stub_hilog.c` / `libhilog_stub.so` | заглушка hilog | DevEco clang | позволяет грузить `libhdf_platform` без `libbegetutil`-цепочки | заглушка |
| `...\module_hdfstub.c` | kernel-модуль стенда | написан для стенда | `misc_register("HDF_PLATFORM_I2C_MANAGER")` + `_IO('b',1)` + `Dispatch` | готово |
| `...\vm_*.sh` | скрипты подъёма VM и e2e | — | воспроизведение kernel-половины за ~5 мин | готово |
| `C:\Users\Kharki\Desktop\harmony_phone\re\` | бинарники телефона/эмулятора для RE | образы 5.x/6.x | `libhdf_platform.z.so` (5.x и 6.x), `libhdf_host.z.so`, `libhdf_utils.z.so` (5.x/6.x), `hdf_devhost`, `hdf_devmgr` | готово |
| `C:\Users\Kharki\Desktop\harmony_phone\*_mate60pro.zip`, `update_full_base.zip` | полные OTA настоящих телефонов | `update.dbankcdn.com` (CDN Huawei) | 5.x `ALN-LGRP1-CHN 205.0.0.66(SP6log)`; 6.x `ALN-LGRP1-CHN 206.0.0.108(SP6)` | готово |
| `C:\Users\Kharki\Desktop\harmony_kernel_re\` | x86-ядро 7.0.0-B1 | SDK `HarmonyOS-7.0.0-B1/phone_all_x86` | `vmlinux` (Linux 5.10.210, ELF64), `kernel.config` (5441 стр.), `symbols.tsv` (117 586 символов kallsyms) | готово |
| `~/hp6/` | 53 образа 6.0.0.108 (ALN= Mate 60 Pro) | распакован `update.bin` (SimomYung/unpack_huawei_package) | `boot.img` 48 234 496 Б (secimg, payload entropy 7.998); `system.img` 3.9G EROFS | готово |
| `~/hp6/sys6/` | распакованный system 6.0.0.108 | `fsck.erofs --extract` | `/system/lib64/...` (arm64), `/system/etc/param/ohos.para` | готово |
| `~/hp6/vendor6/` | распакованный vendor 6.0.0.108 | `fsck.erofs --extract` | `libhdf_platform.z.so` (83 328), `libhdf_host.z.so` (69 720) | готово |
| `~/b7`, `~/b7v`, `~/b7sp` | смонтированные 7.0.0-B1 system/vendor/sys_prod (ext4) | SDK | x86_64-бинарники для Linux-тестов | готово |
| `~/hdfcore/` | исходники `drivers_hdf_core` (OpenHarmony) | gitee | `HDF_WRITE_READ _IO('b',1)`, `HdfWriteReadBuf`, `HdfVNodeAdapterServCall`, `HdfKIoServiceDispatch`, cmdId-enum'ы | готово |
| `~/k510/` | `kernel_linux_5.10` (OpenHarmony) | gitee | подтверждено: это чистый Linux без HDF | готово |
| `~/noble.img`, `~/module_hdfstub.c` (в VM) | стенд kernel-половины | Ubuntu cloud image + собранный модуль | QEMU/KVM, ядро 6.8.0-147-generic | готово (VM остановлена) |

---

## 2. Инвентаризация бинарников (6.0.0.108 = arm64, 7.0.0-B1 = x86_64)

Формат NEEDED — полный список из `readelf -d`. «Тест на Linux» = реальный `dlopen`/исполнение.

| .so | размер | class/machine | NEEDED | откуда | тест на Linux | результат |
|---|---|---|---|---|---|---|
| `libability_manager.z.so` | 1 139 712 | ELF64/AArch64 | base, want, zuri, appexecfwk_base, native_dataability, native_rdb, ability_start_setting, mission_info, app_manager, freeze_util, wantagent_manager, app_util, hitrace_chain_util, session_info, utils, eventhandler, hilog, hitrace_meter, samgr_proxy, wsutils, session_manager_lite, image_native, dlpparse, c, c++ | `6.0.0.108/system/lib64/platformsdk` | нет | — |
| `libabilitykit_native.z.so` | 1 436 144 | ELF64/AArch64 | abilitykit_utils, extensionkit_native, napi_common, uv, ace_napi, form_manager, dm, continuation_ipc, ui_service_extension_connection, ability_manager, ability_start_options, ability_start_setting, mission_info, dataobs_manager, ability_deps_wrapper, runtime, wantagent_innerkits, ability_context_native, ability_business_error, app_context, app_context_utils, appkit_delegator, freeze_util, app_util, event_report, process_options, base, configuration, session_info, want, zuri, accesstoken_sdk, tokenid_sdk, appexecfwk_base, utils, eventhandler, hilog, hitrace_meter, ipc_napi, native_rdb, global_resmgr, samgr_proxy, wsutils, cj_bind_native, bgtaskmgr_innerkits, hmicuuc, image_napi, mmi-client, wm, windowstage_kit, ability_connect_callback_stub, c, c++, ipc_single | `6.0.0.108/system/lib64/platformsdk` | нет | — |
| `libsamgr_proxy.z.so` | 194 704 | ELF64/AArch64 | utils, hilog, begetutil, ipc_single, c, c++ | `6.0.0.108/system/lib64/platformsdk` | нет | — |
| `libsamgr_common.z.so` | 172 224 | ELF64/AArch64 | utils, hilog, hisysevent, hitrace_meter, hicollie, c, c++, clang_rt.ubsan_minimal | `6.0.0.108/system/lib64/platformsdk` | нет | — |
| `libark_jsruntime.so` | 11 790 920 | ELF64/AArch64 | hmicui18n, hmicuuc, sec_shared, faultloggerd, begetutil, unwinder, hitrace_meter, hitracechain, hilog, hisysevent, ucollection_client, dfx_signalhandler, qos, uv, ffrt, jit_code_sign, utils, shared_libz, c, c++, clang_rt.ubsan_minimal | `6.0.0.108/system/lib64/platformsdk` | нет | — |
| `libark_interop.z.so` | 154 168 | ELF64/AArch64 | ace_napi, ark_jsruntime, hilog, uv, eventhandler, hitrace_meter, c, c++ | `6.0.0.108/system/lib64/platformsdk` | нет | — |
| `libipc_single.z.so` | 526 864 | ELF64/AArch64 | ipc_common, utils, backtrace_local, ffrt, hilog, hitracechain, selinux.z, hisysevent, c, c++, clang_rt.ubsan_minimal | `6.0.0.108/system/lib64/platformsdk` | нет | — |
| `libipc_core.z.so` | 526 864 | ELF64/AArch64 | ipc_common, utils, backtrace_local, ffrt, hilog, hitracechain, selinux.z, hisysevent, c, c++, clang_rt.ubsan_minimal | `6.0.0.108/system/lib64/platformsdk` | нет | — |
| `libipc_common.z.so` | 64 392 | ELF64/AArch64 | utils, hilog, c, c++, clang_rt.ubsan_minimal | `6.0.0.108/system/lib64/platformsdk` | нет | — |
| `libhdf_platform.z.so` | 83 328 | ELF64/AArch64 | hdf_utils, utils, hilog, c | `6.0.0.108/vendor/lib64` | нет (arm64) | — |
| `libhdf_host.z.so` | 69 720 | ELF64/AArch64 | hdf_ipc_adapter, hdf_utils, utils, hilog, c | `6.0.0.108/vendor/lib64` | нет (arm64) | — |
| `libhdf_utils.z.so` | 101 928 | ELF64/AArch64 | utils, hilog, c | `6.0.0.108/system/lib64/chipset-sdk` | нет (arm64) | — |
| `libhdf_ipc_adapter.z.so` | 109 440 | ELF64/AArch64 | pub_utils, utils, hilog, ipc_single, samgr_proxy, c, c++ | `6.0.0.108/system/lib64/platformsdk` | нет | — |
| `libhilog.so` | 285 368 | ELF64/AArch64 | sec_shared, cjson, configpolicy_util, begetutil, c, c++, hilog_encode | `6.0.0.108/system/lib64/platformsdk` | нет (заменялся stub'ом) | в VM использована заглушка |
| `libbegetutil.z.so` | 156 416 | ELF64/AArch64 | c, c++ | `6.0.0.108/system/lib64/platformsdk` | нет | — |
| `libace.z.so` | — | — | — | — | — | **не найден в образе**; ACE представлен `libace_engine_pa_ark.z.so` (413 160), `libace_ndk.z.so` (887 680), `libace_napi.z.so` (608 632), AArch64 |
| `libbinder*.z.so` | — | — | — | — | — | **не найден в образе** (ни `libbinder.so`, ни `libbinder_ndk.z.so`) |
| `libhdf_platform.z.so` (7.0.0-B1) | 77 240 | ELF64/x86-64 | hdf_utils, sec_shared, hilog, c | `7.0.0-B1/system/lib64` | **да** (dlopen+вызов на Linux: LD_PRELOAD и VM-e2e) | 3 ioctl с cmdId 1/0/2, dmesg `DISPATCH` |
| `libhdf_utils.z.so` (7.0.0-B1) | 96 992 | ELF64/x86-64 | sec_shared, utils, hilog, c | `7.0.0-B1/system/lib64/chipset-sdk` | да (в составе e2e) | загружена, резолвится |
| `libhdf_host.z.so` (7.0.0-B1) | 69 080 | ELF64/x86-64 | hdf_ipc_adapter, hdf_utils, sec_shared, hilog, c | `7.0.0-B1/system/lib64/chipset-sdk-sp` | нет | — |
| `libhdf_ipc_adapter.z.so` (7.0.0-B1) | 127 280 | ELF64/x86-64 | pub_utils, utils, hilog, ipc_single, samgr_proxy, c, c++ | `7.0.0-B1/system/lib64/platformsdk` | нет | — |
| `libability_manager.z.so` (7.0.0-B1) | 1 473 400 | ELF64/x86-64 | base, want, zuri, appexecfwk_base, native_dataability, native_rdb, ability_start_options, ability_start_setting, mission_info, app_manager, freeze_util, wantagent_manager, app_util, session_info, utils, eventhandler, hilog, hitrace_meter, samgr_proxy, wsutils, session_manager_lite, image_native, dlpparse, c, c++, ipc_single | `7.0.0-B1/system/lib64/platformsdk` | нет | — |
| `libark_jsruntime.so` (7.0.0-B1) | 11 560 984 | ELF64/x86-64 | hmicui18n, hmicuuc, sec_shared, faultloggerd, begetutil, hitrace_meter, hitracechain, hilog, hisysevent, ucollection_client, dfx_signalhandler, qos, uv, ffrt, shared_libz, c, c++, clang_rt.ubsan_minimal | `7.0.0-B1/system/lib64/platformsdk` | нет | — |
| `libipc_single.z.so` (7.0.0-B1) | 568 472 | ELF64/x86-64 | ipc_common, sec_shared, utils, backtrace_local, ffrt, hilog, hitracechain, selinux.z, hisysevent, c, c++, clang_rt.ubsan_minimal | `7.0.0-B1/system/lib64/platformsdk` | нет | — |
| `libhilog.so` (7.0.0-B1) | 187 560 | ELF64/x86-64 | sec_shared, begetutil, c, c++ | `7.0.0-B1/system/lib64/chipset-sdk` | нет (заменялась stub'ом) | в e2e — заглушка |
| `libbegetutil.z.so` (7.0.0-B1) | 164 680 | ELF64/x86-64 | configpolicy_util, c, c++ | `7.0.0-B1/system/lib64/platformsdk` | нет | — |

Не найдены в 7.0.0-B1/vendor: все перечисленные (`libhdf_platform`, `libability_manager`, `libace*`, `libbinder*` и т.д.) — эмулятор держит их в `/system`.

---

## 3. Статус проверок

### 3.1 Доказано эмпирически

1. **`ioctl(fd, 0x6201, &HdfWriteReadBuf)` вызывается реальной `libhdf_platform.z.so`** — LD_PRELOAD-шим, `cmdCode=1/0/2`, sbuf: `00000000` / `31433249 01000000 06000000 5000 0100 00000000 01000000 a5000000` / `31433249`. → `02_userspace_proof.txt`
2. **Ядро по `ioctl(0x6201)` вызывает `Dispatch(cmdId, sbuf)`** — собственный `.ko` + dmesg: `DISPATCH cmdId=1/0/2`, те же payload'ы. → `03_e2e_proof.txt`
3. **Сквозной прогон**: реальная `.so` → реальный chardev `/dev/HDF_PLATFORM_I2C_MANAGER` → модуль → `Dispatch`. → `03_e2e_proof.txt`
4. **На эмуляторе platform-узлов нет**: `/dev/HDF_PLATFORM_I2C_MANAGER` отсутствует, `CONFIG_DRIVERS_HDF=n`. → `00_emulator_recon.txt`
5. **Эмулятор грузит и резолвит символы** `libhdf_platform` — `I2cOpen` найден, вызов дошёл до `open()` (EACCES из-за SELinux shell-домена). → `01_sanity_emulator.txt`

### 3.2 Проверено статически

1. `HDF_WRITE_READ = _IO('b',1)` и `struct HdfWriteReadBuf` — `~/hdfcore/interfaces/inner_api/core/hdf_io_service.h`; совпало с дизассемблером (`HdfSyscallAdapterDispatch`, 5.x и 6.x — идентично).
2. Пользовательская сторона: `ioctl(ioService->fd, HDF_WRITE_READ, &wrBuf)` — `~/hdfcore/framework/core/adapter/syscall/src/hdf_syscall_adapter.c:712`.
3. Kernel-сторона: `HdfVNodeAdapterIoctl` → `HdfVNodeAdapterServCall` (CopyFromUser, `MAX_RW_SIZE=1024*1204`) → `HdfKIoServiceDispatch` → `device->service->Dispatch` — `~/hdfcore/framework/core/adapter/vnode/src/hdf_vnode_adapter.c`, `framework/core/common/src/hdf_device_node_ext.c`.
4. cmdId платформенных интерфейсов (I2C/SPI/UART/Clock/RTC/PWM/Timer/Watchdog/ADC/Pin/DAC) — `~/hdfcore/framework/include/platform/*_if.h`.
5. Имена сервисов `HDF_PLATFORM_{ADC,CLOCK,GPIO,I2C}_MANAGER`, `..._PWM_%u`, `..._RTC`, `..._TIMER_MANAGER`, `..._SPI_%u`, `..._UART_%u`, `..._WATCHDOG_%d` — strings `vendor/lib64/libhdf_platform.z.so`.
6. `/dev/HDF_PLATFORM_I2C_MANAGER` — SELinux `file_contexts` (строка 90) в `~/hp6/sys6`.
7. 41 userspace-хост (`power_host`, `audio_host`, `sensor_host`, `wifi_host`, …) — `chip_prod/etc/init/hdf_devhost.cfg`.
8. `libhdf_utils.z.so` 5.x ≠ 6.x побайтно, но `movz #0x6201` присутствует в обеих (по 1 шт.); декомпиляция 6.x идентична 5.x.
9. Ядро x86 7.0.0-B1: Linux 5.10.210, `CONFIG_KALLSYMS_ALL=y`, `CONFIG_DRIVERS_HDF` не установлен; 117 586 символов восстановлено из kallsyms.
10. `boot.img` телефона — secimg: DER-цепочка, payload entropy ≈7.998, HVB-футер `HVB\0`; ни одного kernel-маркера во всех 52 разделах.
11. Разметка 5.x → 6.x: 94 → 98 разделов (+`module_update`, `ext_rvt`, `reserved3`, `reserved7`).
12. Микроядерные маркеры: `grep -rl -E "libhmkernel|libcapability|lsyscall|archsyscall|hm_ipc"` по `.so` → **0 файлов** в обоих образах (6.0.0.108 и 7.0.0-B1); `capability_` в `libace_*` и `libark_jsruntime` — 0 вхождений.

### 3.3 Не проверено

1. **ArkRuntime на Linux** — `libark_jsruntime.so` не запускался ни разу; требуется закрыть NEEDED (`libhmicui18n`, `libhmicuuc`, `libffrt`, `libqos`, `libjit_code_sign`, `libdfx_signalhandler`) и понять, что из этого POSIX, а что зависит от сервисов OHOS.
2. **Ability framework / samgr** — ни `libability_manager`, ни `libsamgr_proxy` не грузились; зависимости от `samgr` (IPC) не проверены.
3. **Render Service / ACE** — `libace_engine_pa_ark`, `libace_ndk`, `libskia_canvaskit` не грузились; графический стек не проверялся.
4. **Capability-примитивы / микроядро** — существование ABI `libhmkernel`/`lsyscall` в рантайме не проверено; статически маркеров нет, но это не доказывает отсутствия иного механизма.
5. **TEE/HMS** — не проверялись; `teeos.img`, `hisee*`, `hhee`, `hkrr` только инвентаризированы как разделы.
6. **HDF на реальном телефоне** — kernel-сторона недоступна (boot.img зашифрован); выводы о khdf только по исходникам и SELinux-контекстам.
7. **`drivers/hdf_core` против современного Linux-ядра** — не собиралось.
8. **SM8150/cepheus kernel с `CONFIG_DRIVERS_HDF=y`** — не собиралось.
9. **arm64-бинарники на Linux** — не запускались (тестировался только x86_64 из эмулятора).
10. **`libhdf_host` / IPC-путь** (`libhdf_ipc_adapter` → `samgr`) — не проверялся.

---

## 4. Ключевой вопрос: микроядерные зависимости

Проверка: NEEDED (readelf) + `strings` по шаблонам `libhmkernel`, `libcapability`, `lsyscall`, `archsyscall`, `hm_ipc`, `capability_`.

| .so | есть / нет / не проверялось |
|---|---|
| `libability_manager.z.so` | нет |
| `libabilitykit_native.z.so` | нет |
| `libsamgr_proxy.z.so` | нет |
| `libsamgr_common.z.so` | нет |
| `libark_jsruntime.so` | нет (в strings 1 вхождение слова «syscall», не ABI-маркер) |
| `libark_interop.z.so` | нет |
| `libipc_single.z.so` | нет |
| `libipc_core.z.so` | нет |
| `libipc_common.z.so` | нет |
| `libhdf_platform.z.so` | нет |
| `libhdf_host.z.so` | нет |
| `libhdf_utils.z.so` | нет |
| `libhdf_ipc_adapter.z.so` | нет |
| `libhilog.so` | нет |
| `libbegetutil.z.so` | нет |
| `libace_engine_pa_ark.z.so` / `libace_ndk.z.so` / `libace_napi.z.so` | нет (`capability_` = 0) |
| `libbinder*.z.so` | не применимо (в образе отсутствует) |

Глобальный скан: **0 `.so`-файлов** с маркерами микроядерного ABI в 6.0.0.108 и 7.0.0-B1.

Ограничение вывода: отсутствие строк/NEDED не доказывает отсутствия иного механизма; проверены только эти образы и только статически.

---

## 5. Известные ограничения и тупики

1. **`CONFIG_DRIVERS_HDF=n` в ядре эмулятора** — platform-узлов быть не может; живой тест platform-слоя на эмуляторе невозможен by design. Обход: QEMU-VM со своим модулем.
2. **SELinux на эмуляторе** — shell `uid=2000, u:r:sh:s0`: `/dev`, `/proc/cmdline`, `dmesg`, `/sys` → EACCES. Отсюда `EACCES` вместо `ENOENT` в sanity; `strace` на эмуляторе отсутствует.
3. **Ядро телефона зашифровано** — `boot.img` secimg/HVB, payload entropy ≈7.998; статически ядро не извлечь. Ни один раздел не содержит `Linux version`/`ARM64`/компресс-маркеров.
4. **`libhilog` в тестовой VM** — реальный `libhilog.so` тянет `libbegetutil` → hilog-сервис; заменён на собственную заглушку (`stub_hilog.c`). Это единственная подмена, только логирование.
5. **musl vs glibc** — решено запуском через musl-лоадер и sysroot образа (`ld-musl-x86_64.so.1`, `--library-path`), не через glibc. Требует закрытия цепочки: `libsec_shared`, `libutils`, `libc++_shared`, `libclang_rt.ubsan_minimal`.
6. **WSL2 без kernel-headers** — собственный модуль в WSL не собрать/не загрузить; поэтому стенд вынесен в QEMU-VM (Ubuntu 24.04, 6.8.0-147-generic).
7. **WSL убивает фоновые процессы** при завершении `wsl.exe`-вызова — VM держится только живым job'ом; без этого QEMU умирает (наблюдалось).
8. **Нестабильность эмулятора** — при нагрузке падал (freeze/minidump); потребовался перезапуск headless `Emulator -start "<name>" -noWindow`.
9. **`.hcs`-конфигов на телефоне нет** — HDF-конфиг скомпилирован (`chip_prod/etc/hdfconfig/hdf_default.hcb`), host-имена вытащены из init-cfg и strings.

---

## 6. Следующие шаги (открытая очередь)

1. **Собрать `drivers/hdf_core` против Linux 6.8 в VM с `CONFIG_DRIVERS_HDF=y`.**
   Готово, когда: модуль/ядро компилируется без правок HDF-кода, `khdf` регистрирует `/dev/HDF_PLATFORM_I2C_MANAGER`, и реальная `libhdf_platform.z.so` работает **без** нашего stub-модуля (dmesg — от khdf).
2. **Собрать SM8150 (cepheus) ядро с `CONFIG_DRIVERS_HDF=y`.**
   Готово, когда: ядро собирается, грузится в QEMU (или на устройстве), создаются platform-узлы, `I2cOpen` из `libhdf_platform` доходит до реального I2C-контроллера SM8150.
3. **Проверить arm64-бинарники на Linux (qemu-aarch64).**
   Готово, когда: `libhdf_platform.z.so` (arm64, 6.0.0.108) грузится и делает `ioctl(0x6201)`; зафиксирован список недостающих символов.
4. **Smoke-тест ArkRuntime/ACE на x86_64 7.0.0-B1.**
   Готово, когда: `dlopen libark_jsruntime.so` и `libace_engine_pa_ark.z.so` возвращают конкретный список unresolved-символов, из которого составлен план адаптации (POSIX vs OHOS-сервисы).
5. **Добыть пакет Pura 70 (`HBP-*`)** тем же методом (OTA token) и сравнить `vendor/etc/param` с ALN-образом.
   Готово, когда: пакет скачан с `update.dbankcdn.com`, распакован, выгружены `const.product.model`/`build.description` и состав разделов.
