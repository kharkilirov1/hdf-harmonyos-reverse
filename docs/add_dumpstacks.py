#!/usr/bin/env python3
"""Добавляет в foundation.cfg job services:dumpstacks и on-start хук,
чтобы стек-дампы снимались при каждом старте foundation (надёжно)."""
import json

p = "/home/kharki/hsroot2/system/etc/init/foundation.cfg"
d = json.load(open(p))

names = [j["name"] for j in d["jobs"]]
if "services:dumpstacks" not in names:
    d["jobs"].append({
        "name": "services:dumpstacks",
        "cmds": [
            "exec /system/bin/delayed_exec 3 /data/diag/e1.log /system/bin/sh /system/bin/dumpstack4.sh",
            "exec /system/bin/delayed_exec 35 /data/diag/e2.log /system/bin/sh /system/bin/dumpstack4.sh",
            "exec /system/bin/delayed_exec 70 /data/diag/e3.log /system/bin/sh /system/bin/dumpstack4.sh",
            "exec /system/bin/delayed_exec 110 /data/diag/e4.log /system/bin/sh /system/bin/dumpstack4.sh",
        ],
    })
for s in d["services"]:
    if s.get("name") == "foundation":
        s.setdefault("jobs", {})["on-start"] = "services:dumpstacks"
json.dump(d, open(p, "w"), indent=1)
print("foundation.cfg updated:", [j["name"] for j in d["jobs"]])
