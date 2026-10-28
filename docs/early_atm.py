#!/usr/bin/env python3
"""Ранний старт accesstoken_service: переносим start из early-boot в pre-init
и ставим start-mode=boot, чтобы ATM публиковался ДО foundation/BMS."""
import json

p = "/home/kharki/hsroot2/system/etc/init/access_token.cfg"
d = json.load(open(p))
for j in d.get("jobs", []):
    cmds = j.get("cmds", [])
    if j.get("name") == "early-boot":
        j["cmds"] = [c for c in cmds if "start accesstoken_service" not in c]
    if j.get("name") == "pre-init":
        if "start accesstoken_service" not in cmds:
            cmds.append("start accesstoken_service")
for s in d.get("services", []):
    if s.get("name") == "accesstoken_service":
        s["start-mode"] = "boot"
json.dump(d, open(p, "w"), indent=1)
print("access_token.cfg updated")
