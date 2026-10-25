"""Install the user-provided Bridge ZIP into this portable Blender only."""
import hashlib
import importlib
import json
from pathlib import Path, PurePosixPath
import shutil
import time
import zipfile

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = Path(r"C:\Users\20665\Downloads\Tripo3d_Blender_Bridge-latest.zip")
MODULE = "Tripo3d_Blender_Bridge"
PORTABLE = ROOT / "tools/blender-4.5.14-windows-x64/portable"
EVIDENCE = ROOT / "setup/verification/tripo-bridge"

config = Path(bpy.utils.user_resource("CONFIG")).resolve()
scripts = Path(bpy.utils.user_resource("SCRIPTS")).resolve()
assert config.is_relative_to(PORTABLE), config
assert scripts.is_relative_to(PORTABLE), scripts
EVIDENCE.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(ARCHIVE) as archive:
    assert archive.testzip() is None, "ZIP CRC check failed"
    for entry in archive.infolist():
        path = PurePosixPath(entry.filename.replace("\\", "/"))
        assert not path.is_absolute() and ".." not in path.parts
        assert path.parts[0] == MODULE, entry.filename
        assert all(":" not in part for part in path.parts)

previous_preferences = config / "userpref.blend"
if previous_preferences.exists():
    backup = EVIDENCE / ("userpref-before-" + time.strftime("%Y%m%d-%H%M%S") + ".blend")
    shutil.copy2(previous_preferences, backup)

destination = scripts / "addons" / MODULE
assert not destination.exists(), "Existing installation found; inspect before replacing"
result = bpy.ops.preferences.addon_install(filepath=str(ARCHIVE), overwrite=False)
assert "FINISHED" in result, result
addon_utils.enable(MODULE, default_set=True, persistent=True)
assert addon_utils.check(MODULE) == (True, True), addon_utils.check(MODULE)
module = importlib.import_module(MODULE)
status_module = importlib.import_module(MODULE + ".core.status_manager")
task_module = importlib.import_module(MODULE + ".core.task")

deadline = time.monotonic() + 8
while status_module.status.state.value == "disconnected" and time.monotonic() < deadline:
    time.sleep(0.1)

report = {
    "blender": bpy.app.version_string,
    "addon": MODULE,
    "version": list(module.bl_info["version"]),
    "archive": str(ARCHIVE),
    "archive_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
    "installation": str(destination),
    "enabled": addon_utils.check(MODULE),
    "panel_registered": hasattr(bpy.types, "VIEW3D_PT_tripo"),
    "bridge_state": status_module.status.state.value,
    "last_log": status_module.status.last_log,
    "local_host": task_module.task_manager.ws_server.host,
    "local_port": task_module.task_manager.ws_server.port,
    "studio_account_connection_tested": False,
}
assert report["panel_registered"], report
assert report["bridge_state"] in ("listening", "connected"), report
assert "FINISHED" in bpy.ops.wm.save_userpref()
report["preferences_saved"] = True
(EVIDENCE / "installation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("TRIPO_INSTALL=" + json.dumps(report), flush=True)
# Stop this verification process's listener while keeping the saved enablement.
addon_utils.disable(MODULE, default_set=False)
