"""Verify a local Blender install without rendering or changing user preferences.

Run with Blender's --background --factory-startup --python-exit-code 1 flags.
Only a small verification scene and its exports are written beside this script.
"""

from __future__ import annotations

import hashlib
import json
import platform
import traceback
from datetime import datetime, timezone
from pathlib import Path

import addon_utils
import bpy
from mathutils import Vector


OUTPUT_DIR = Path(__file__).resolve().parent / "verification"
RESULT_PATH = OUTPUT_DIR / "blender-result.json"


def inspect_auto_rig_pro() -> dict:
    """Discover installed modules without enabling a paid/third-party add-on."""
    enabled = set(bpy.context.preferences.addons.keys())
    matches = []
    for module in addon_utils.modules(refresh=True):
        name = module.__name__
        label = getattr(module, "bl_info", {}).get("name", "")
        normalized = (name + " " + label).lower().replace("-", "_").replace(" ", "_")
        if "auto_rig_pro" in normalized or "autorigpro" in normalized:
            info = getattr(module, "bl_info", {})
            matches.append(
                {
                    "module": name,
                    "name": label,
                    "version": list(info.get("version", ())),
                    "enabled": name in enabled,
                    "path": str(getattr(module, "__file__", "")),
                }
            )
    return {"detected": bool(matches), "modules": matches}


def ensure_exporter(module_name: str) -> None:
    addon_utils.enable(module_name, default_set=False, persistent=False)
    if not addon_utils.check(module_name)[1]:
        raise RuntimeError(f"Bundled exporter failed to load: {module_name}")


def checked_operator(result: set, operation: str) -> None:
    if "FINISHED" not in result:
        raise RuntimeError(f"{operation} did not finish: {result}")


def artifact_info(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Output is missing or empty: {path}")
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def create_scene() -> None:
    checked_operator(bpy.ops.wm.read_factory_settings(use_empty=True), "Create empty scene")
    checked_operator(bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1)), "Create cube")
    cube = bpy.context.active_object
    cube.name = "VerificationCube"

    material = bpy.data.materials.new("VerificationMaterial")
    material.diffuse_color = (0.18, 0.48, 0.8, 1.0)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = material.diffuse_color
    shader.inputs["Roughness"].default_value = 0.5
    cube.data.materials.append(material)

    camera_data = bpy.data.cameras.new("VerificationCamera")
    camera = bpy.data.objects.new("VerificationCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (6, -6, 5)
    camera.rotation_euler = (Vector((0, 0, 1)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera

    light_data = bpy.data.lights.new("VerificationLight", type="POINT")
    light_data.energy = 1000
    light = bpy.data.objects.new("VerificationLight", light_data)
    bpy.context.collection.objects.link(light)
    light.location = (3, -4, 6)

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.resolution_x = 320
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100


def run() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "running",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "blender_version": bpy.app.version_string,
        "blender_version_tuple": list(bpy.app.version),
        "blender_executable": bpy.app.binary_path,
        "python_version": platform.python_version(),
        "background_mode": bool(bpy.app.background),
        "rendered": False,
        "auto_rig_pro": {"detected": None, "modules": []},
        "artifacts": {},
    }
    try:
        try:
            result["auto_rig_pro"] = inspect_auto_rig_pro()
        except Exception as exc:
            result["auto_rig_pro"]["detection_error"] = str(exc)

        create_scene()
        result["scene"] = {
            "objects": sorted(obj.name for obj in bpy.context.scene.objects),
            "mesh_count": sum(obj.type == "MESH" for obj in bpy.context.scene.objects),
            "camera_count": sum(obj.type == "CAMERA" for obj in bpy.context.scene.objects),
            "light_count": sum(obj.type == "LIGHT" for obj in bpy.context.scene.objects),
        }
        blend_path = OUTPUT_DIR / "blender-smoke.blend"
        checked_operator(bpy.ops.wm.save_as_mainfile(filepath=str(blend_path)), "Save Blender scene")
        result["artifacts"]["blend"] = artifact_info(blend_path)

        ensure_exporter("io_scene_gltf2")
        glb_path = OUTPUT_DIR / "blender-smoke.glb"
        checked_operator(
            bpy.ops.export_scene.gltf(
                filepath=str(glb_path),
                export_format="GLB",
                export_cameras=True,
                export_lights=True,
            ),
            "Export GLB",
        )
        result["artifacts"]["glb"] = artifact_info(glb_path)
        if glb_path.read_bytes()[:4] != b"glTF":
            raise RuntimeError("GLB output has an invalid header")

        ensure_exporter("io_scene_fbx")
        fbx_path = OUTPUT_DIR / "blender-smoke.fbx"
        checked_operator(
            bpy.ops.export_scene.fbx(
                filepath=str(fbx_path),
                object_types={"MESH", "CAMERA", "LIGHT"},
                add_leaf_bones=False,
                bake_anim=False,
            ),
            "Export FBX",
        )
        result["artifacts"]["fbx"] = artifact_info(fbx_path)
        if not fbx_path.read_bytes().startswith(b"Kaydara FBX Binary"):
            raise RuntimeError("FBX output has an invalid header")

        result["status"] = "passed"
        return result
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
        raise
    finally:
        RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("BLENDER_VERIFICATION_RESULT=" + str(RESULT_PATH), flush=True)
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    run()
