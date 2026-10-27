#!/usr/bin/env python3
"""inject_launcher_db.py — вписать лаунчер в БД BMS (installed + preinstalled).

Берём JSON существующей HSP-записи (com.huawei.hms.weather) и заменяем
идентичность на com.huawei.hmos.slassistant (модуль "phone", entry-HAP
/system/app/SuperLauncher/SuperLauncher.hap, versionCode 60000302).
Пишем обе таблицы в bmsdb.db и bmsdb_slave.db дерева образа.
"""
import json
import sqlite3

SRC_DB = "/tmp/bmdb2.db"
TREE_DB = "/home/kharki/hsroot2/data/service/el1/public/bms/bundle_manager_service"
OLD_BUNDLE = "com.huawei.hms.weather"
NEW_BUNDLE = "com.huawei.hmos.slassistant"
OLD_MODULE = "WeatherService"
NEW_MODULE = "phone"
OLD_HSP = "/system/app/appServiceFwk/WeatherService/WeatherService.hsp"
NEW_HAP = "/system/app/SuperLauncher/SuperLauncher.hap"
VERSION_CODE = 60000302


def retarget(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out[k] = retarget(v)
        # точечные поля
        for key in ("bundleName",):
            if out.get(key) == OLD_BUNDLE:
                out[key] = NEW_BUNDLE
        return out
    if isinstance(obj, list):
        return [retarget(v) for v in obj]
    if isinstance(obj, str):
        s = obj
        s = s.replace(OLD_BUNDLE, NEW_BUNDLE)
        s = s.replace(OLD_HSP, NEW_HAP)
        s = s.replace(OLD_MODULE, NEW_MODULE)
        return s
    return obj


def main():
    src = sqlite3.connect(SRC_DB)
    inst = json.loads(src.execute(
        "select VALUE from installed_bundle where KEY=?", (OLD_BUNDLE,)).fetchone()[0])
    pre = json.loads(src.execute(
        "select VALUE from preinstalled_bundle where KEY=?", (OLD_BUNDLE,)).fetchone()[0])

    inst = retarget(inst)
    pre = retarget(pre)
    # правки под entry-HAP приложение
    inst["bundleType"] = 0
    inst["versionCode"] = VERSION_CODE
    inst["versionName"] = "6.0.0.302"
    inst.setdefault("baseApplicationInfo", {})
    inst["baseApplicationInfo"]["bundleType"] = 0
    inst["baseApplicationInfo"]["versionCode"] = VERSION_CODE
    inst["baseApplicationInfo"]["versionName"] = "6.0.0.302"
    inst["baseApplicationInfo"]["bundleName"] = NEW_BUNDLE
    inst["baseApplicationInfo"]["codePath"] = NEW_HAP
    inst["bundleName"] = NEW_BUNDLE
    pre.update({
        "bundleName": NEW_BUNDLE,
        "bundlePaths": [NEW_HAP],
        "bundleType": 0,
        "moduleName": NEW_MODULE,
        "versionCode": VERSION_CODE,
        "systemApp": True,
        "removable": False,
        "appType": 0,
        "isUninstalled": False,
    })

    for name in ("bmsdb.db", "bmsdb_slave.db"):
        path = "%s/%s" % (TREE_DB, name)
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        for table, value in (("installed_bundle", inst), ("preinstalled_bundle", pre)):
            cur.execute("delete from %s where KEY=?" % table, (NEW_BUNDLE,))
            cur.execute("insert into %s (KEY, VALUE) values (?,?)" % table,
                        (NEW_BUNDLE, json.dumps(value, separators=(",", ":"))))
        conn.commit()
        rows = {t: cur.execute("select count(*) from %s" % t).fetchone()[0]
                for t in ("installed_bundle", "preinstalled_bundle")}
        keys = cur.execute("select KEY from installed_bundle").fetchall()
        print(path, rows, [k[0] for k in keys])
        conn.close()


if __name__ == "__main__":
    main()
