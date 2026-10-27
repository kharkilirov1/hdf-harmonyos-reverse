#!/usr/bin/env python3
"""inject_launcher_full.py — "уже установленный" лаунчер в БД BMS.

Идея (вариант B, подсказка из DevEco-эмулятора):
  На эмуляторе приложения не устанавливаются, а лежат уже установленными
  в userdata: BMS DB содержит полный BundleInfo, а HAP берётся прямо из
  /system/app/... (hapPath).

Берём из БД эмулятора (7.0.0) запись com.ohos.sceneboard (лаунчер,
entry-HAP /system/app/SceneBoard/SceneBoard.hap) как шаблон и
перецеливаем её на наш arm64-лаунчер:
  bundleName  com.huawei.hmos.slassistant
  module      phone
  hapPath     /system/app/SuperLauncher/SuperLauncher.hap
  codePath    /system/app/SuperLauncher
  abilities   SuperLauncherMainAbility (+ остальные из module.json)
  versionCode 60000302 / 6.0.0.302
  cpuAbi      arm64 (нативных библиотек нет)
и пишем запись в installed_bundle нашей БД (без preinstalled, чтобы BMS
не пытался ставить HAP).
"""
import json
import sqlite3

EMU_DB = "/tmp/emu_bms.db"
BASE_DB = "/tmp/bmdb2.db"          # наша БД (HarmonyOS 6.0.0.108, arm64)
TREE = "/home/kharki/hsroot2/data/service/el1/public/bms/bundle_manager_service"

TPL_BUNDLE = "com.ohos.sceneboard"
NEW_BUNDLE = "com.huawei.hmos.slassistant"
NEW_APP_PATH = "/system/app/SuperLauncher"
NEW_HAP = "/system/app/SuperLauncher/SuperLauncher.hap"
NEW_MODULE = "phone"
VERSION_CODE = 60000302
VERSION_NAME = "6.0.0.302"

ABILITIES = [
    "SuperLauncherMainAbility",
    "SuperLauncherUIability",
    "DefaultIntentBackgroundUiAbility",
    "PermissionRequestAbility",
]


def rep(o):
    """Глубокая замена идентичностей шаблона."""
    if isinstance(o, dict):
        return {rep(k): rep(v) for k, v in o.items()}
    if isinstance(o, list):
        return [rep(v) for v in o]
    if isinstance(o, str):
        s = o
        s = s.replace(TPL_BUNDLE, NEW_BUNDLE)
        s = s.replace("phone_sceneboard", NEW_MODULE)
        s = s.replace("SceneBoard", "SuperLauncher")
        return s
    return o


def main():
    emu = sqlite3.connect(EMU_DB)
    tpl = json.loads(emu.execute(
        "select VALUE from installed_bundle where KEY=?", (TPL_BUNDLE,)).fetchone()[0])
    d = rep(tpl)

    # базовая инфа приложения
    ai = d.setdefault("baseApplicationInfo", {})
    ai.update({
        "bundleName": NEW_BUNDLE,
        "codePath": NEW_APP_PATH,
        "cpuAbi": "arm64",
        "nativeLibraryPath": "",
        "versionCode": VERSION_CODE,
        "versionName": VERSION_NAME,
        "appProvisionType": "release",
        "appFeature": "hos_system_app",
        "systemApp": True,
        "debug": False,
    })

    # модули: оставляем только entry-модуль phone
    imi = d.get("innerModuleInfos") or {}
    entry = None
    for name, m in imi.items():
        if m.get("isEntry") and str(m.get("hapPath", "")).endswith(".hap"):
            entry = m
            break
    if entry is None:
        raise SystemExit("entry module not found in template")
    entry = rep(entry)
    entry.update({
        "moduleName": NEW_MODULE,
        "name": NEW_MODULE,
        "hapPath": NEW_HAP,
        "mainAbility": "%s.%s" % (NEW_BUNDLE, ABILITIES[0]),
        "cpuAbi": "arm64",
        "nativeLibraryPath": "",
        "nativeLibraryFileNames": [],
        "deviceTypes": ["phone"],
        "modulePackage": NEW_MODULE,
        "modulePath": NEW_MODULE,
        "moduleResPath": "",
        "moduleDataDir": "",
        "versionCode": VERSION_CODE,
        "versionName": VERSION_NAME,
        "abilityInfos": [],
        "extensionInfos": [],
        "dependencies": [],
    })
    d["innerModuleInfos"] = {NEW_MODULE: entry}

    # базовые ability-инфо: берём шаблонную ability и переименовываем
    bai = d.get("baseAbilityInfos") or {}
    tpl_ab = None
    for k, v in bai.items():
        if "phone" in k and isinstance(v, dict):
            tpl_ab = v
            break
    if tpl_ab is None and bai:
        tpl_ab = next(v for v in bai.values() if isinstance(v, dict))
    new_bai = {}
    if tpl_ab:
        for ab_name in ABILITIES:
            a = rep(tpl_ab)
            a.update({
                "name": ab_name,
                "bundleName": NEW_BUNDLE,
                "moduleName": NEW_MODULE,
                "applicationName": "SuperLauncher",
            })
            new_bai["%s.%s.%s" % (NEW_BUNDLE, NEW_MODULE, ab_name)] = a
    d["baseAbilityInfos"] = new_bai

    # baseBundleInfo
    bbi = d.setdefault("baseBundleInfo", {})
    bbi.update({
        "appId": NEW_BUNDLE,
        "entryModuleName": NEW_MODULE,
        "hapModuleNames": [NEW_MODULE],
        "cpuAbi": "arm64",
        "entryInstallationFree": False,
        "appIndex": 0,
        "uid": -1,
        "gid": "",
    })
    if isinstance(bbi.get("hapModuleInfos"), list):
        bbi["hapModuleInfos"] = [rep(x) for x in bbi["hapModuleInfos"][:1]]
    bbi["hapModuleInfos"] = []
    bbi["hapModuleNames"] = [NEW_MODULE]

    # прочее
    d["bundleStatus"] = 1
    d["isNewVersion"] = True
    if isinstance(d.get("innerBundleUserInfos"), list):
        d["innerBundleUserInfos"] = d["innerBundleUserInfos"][:1]
    d["installMark"] = {}

    payload = json.dumps(d, separators=(",", ":"))

    for name in ("bmsdb.db", "bmsdb_slave.db"):
        path = "%s/%s" % (TREE, name)
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        for t in ("installed_bundle", "preinstalled_bundle"):
            cur.execute("delete from %s where KEY=?" % t, (NEW_BUNDLE,))
        cur.execute("insert into installed_bundle (KEY, VALUE) values (?,?)",
                    (NEW_BUNDLE, payload))
        conn.commit()
        keys = [r[0] for r in cur.execute("select KEY from installed_bundle")]
        print(path, "installed:", keys)
        conn.close()


if __name__ == "__main__":
    main()
