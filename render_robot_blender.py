# -*- coding: utf-8 -*-
"""
render_robot_blender.py
=======================
Monta la escena de estudio y renderiza fotorrealista el modelo
    robot_modular.obj   (generado por generar_robot_modular.py)

COMO USARLO (Blender 3.6 / 4.x / 5.x):
  1) Abre Blender.
  2) Pestana "Scripting" -> boton "Open" -> elige este archivo -> "Run Script" (Alt+P).
     (o en la barra de menus: Scripting > Run)
  3) Al terminar, el render queda en 3d-models/render/robot_modular_####.png

Si prefieres lanzarlo sin abrir la interfaz:
  blender -b -P render_robot_blender.py

Ajustes rapidos en la seccion CONFIG de abajo.
"""

import math
import os
import sys

try:
    import bpy
    from mathutils import Vector
except ImportError:                                    # fuera de Blender
    print("Este script debe ejecutarse DENTRO de Blender (Scripting > Run).")
    sys.exit(1)


# ============================== CONFIG ===================================
OBJ_NAME = "robot_modular.obj"                 # se busca en la carpeta del script
RES_X, RES_Y = 1920, 1200
SAMPLES = 220                                  # 128 rapido / 512 calidad
ENGINE = "CYCLES"                              # "CYCLES" (fotorreal) o "BLENDER_EEVEE_NEXT"
BG_GREY = 0.32                                 # gris del fondo de estudio
CAM_DIST = 2.35                                # distancia de camara (x tamaño del modelo)
CAM_AZIM, CAM_ELEV = -128.0, 14.0              # grados: azimut / elevacion
DOF = True                                     # desenfoque de fondo suave
# =========================================================================

HERE = os.path.dirname(os.path.abspath(bpy.data.filepath or __file__))
CANDIDATES = [os.path.join(HERE, OBJ_NAME),
              os.path.join(os.getcwd(), OBJ_NAME),
              os.path.join(os.getcwd(), "3d-models", OBJ_NAME),
              os.path.join(HERE, "3d-models", OBJ_NAME)]


# ------------------------------------------------------------------ utils
def find_obj():
    for p in CANDIDATES:
        if os.path.isfile(p):
            return p
    raise RuntimeError("No encuentro %s. Edita OBJ_NAME/CANDIDATES en el script."
                       % OBJ_NAME)


def set_input(node, names, value):
    """Asigna un input del Principled BSDF probando varios nombres de version."""
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return True
    return False


def make_material(name, color, metallic=0.0, roughness=0.5, ior=1.45,
                  transmission=0.0, alpha=1.0, emission=None):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if out:
            nt.links.new(bsdf.outputs[0], out.inputs[0])
    set_input(bsdf, ["Base Color"], (color[0], color[1], color[2], 1.0))
    set_input(bsdf, ["Metallic"], metallic)
    set_input(bsdf, ["Roughness"], roughness)
    set_input(bsdf, ["IOR"], ior)
    set_input(bsdf, ["Transmission Weight", "Transmission"], transmission)
    set_input(bsdf, ["Alpha"], alpha)
    if emission:
        set_input(bsdf, ["Emission Color", "Emission"], (emission[0], emission[1], emission[2], 1.0))
        set_input(bsdf, ["Emission Strength"], 1.2)
    # propiedades de vista/mezcla segun version
    if alpha < 1.0 or transmission > 0.0:
        try:
            mat.blend_method = "BLEND"
        except Exception:
            pass
        try:
            mat.surface_render_method = "BLENDED"
        except Exception:
            pass
        mat.use_backface_culling = False
    return mat


# PBR por material del MTL (nombres definidos en generar_robot_modular.py)
PBR = {
    "plastic_white":  dict(color=(0.90, 0.90, 0.88), roughness=0.42),
    "plastic_black":  dict(color=(0.06, 0.06, 0.07), roughness=0.45),
    "plastic_clear":  dict(color=(0.85, 0.92, 0.98), roughness=0.06,
                           transmission=0.92, alpha=0.30, ior=1.49),
    "metal_steel":    dict(color=(0.62, 0.64, 0.68), metallic=1.0, roughness=0.26),
    "metal_dark":     dict(color=(0.30, 0.31, 0.34), metallic=1.0, roughness=0.38),
    "rubber_black":   dict(color=(0.035, 0.035, 0.04), roughness=0.88),
    "pcb_blue":       dict(color=(0.04, 0.20, 0.42), roughness=0.38),
    "pcb_green":      dict(color=(0.04, 0.26, 0.15), roughness=0.38),
    "breadboard":     dict(color=(0.90, 0.90, 0.88), roughness=0.50),
    "component_dark": dict(color=(0.12, 0.12, 0.14), roughness=0.42),
    "battery_pack":   dict(color=(0.09, 0.11, 0.17), roughness=0.30),
    "battery_cell":   dict(color=(0.18, 0.20, 0.26), metallic=0.6, roughness=0.35),
    "wire_red":       dict(color=(0.62, 0.05, 0.04), roughness=0.35),
    "wire_yellow":    dict(color=(0.80, 0.62, 0.04), roughness=0.35),
    "wire_black":     dict(color=(0.05, 0.05, 0.06), roughness=0.35),
    "wire_blue":      dict(color=(0.06, 0.18, 0.62), roughness=0.35),
    "label_white":    dict(color=(0.96, 0.96, 0.95), roughness=0.45),
    "copper":         dict(color=(0.72, 0.45, 0.20), metallic=1.0, roughness=0.30),
}


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    try:
        sc.render.engine = ENGINE if ENGINE in {
            e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
        } else "CYCLES"
    except Exception:
        sc.render.engine = "CYCLES"
    sc.render.resolution_x, sc.render.resolution_y = RES_X, RES_Y
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = "AgX"
    except Exception:
        try:
            sc.view_settings.view_transform = "Filmic"
        except Exception:
            pass
    if sc.render.engine == "CYCLES":
        sc.cycles.samples = SAMPLES
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 12
        sc.cycles.transmission_bounces = 12
        sc.cycles.device = "GPU" if os.environ.get("BLENDER_GPU") else "CPU"
    return sc


def import_model(path):
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=path)
    else:
        bpy.ops.import_scene.obj(filepath=path)
    objs = [o for o in bpy.context.selected_objects] or list(bpy.context.scene.objects)
    for o in objs:                      # el OBJ viene en mm -> pasar a metros
        o.scale = (0.001, 0.001, 0.001)
    bpy.context.view_layer.update()
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # suavizado por angulo + normales correctas
    for o in objs:
        if o.type == "MESH":
            try:
                o.data.shade_smooth_by_angle(angle=math.radians(35))   # Blender 4.1+
            except Exception:
                try:
                    bpy.ops.object.shade_smooth()
                    o.data.use_auto_smooth = True
                    o.data.auto_smooth_angle = math.radians(35)
                except Exception:
                    pass
    return objs


def assign_pbr():
    """Reemplaza los materiales del MTL por Principled BSDF reales."""
    for mat in list(bpy.data.materials):
        spec = PBR.get(mat.name)
        if spec is None:                       # el OBJ puede renombrar a name.001
            base = mat.name.split(".")[0]
            spec = PBR.get(base)
        if spec is None:
            continue
        new = make_material(mat.name, **spec)
        for o in bpy.data.objects:
            if o.type != "MESH":
                continue
            for i, slot in enumerate(o.data.materials):
                if slot is mat:
                    o.data.materials[i] = new


def bounds(objs):
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
    return mn, mx


def build_studio(mn, mx):
    size = max((mx - mn).x, (mx - mn).y, (mx - mn).z)
    ctr = (mn + mx) * 0.5
    sc = bpy.context.scene

    # ---- fondo de estudio: suelo infinito + pared ----
    bpy.ops.mesh.primitive_plane_add(size=size * 22, location=(ctr.x, ctr.y, mn.z - size * 0.01))
    floor = bpy.context.object
    floor.name = "ESTUDIO_SUELO"
    floor.data.materials.append(make_material("studio_grey", (BG_GREY, BG_GREY, BG_GREY),
                                             roughness=0.62))

    bpy.ops.mesh.primitive_plane_add(size=size * 22)
    back = bpy.context.object
    back.name = "ESTUDIO_FONDO"
    d = size * 5.0
    ang = math.radians(CAM_AZIM)
    back.location = (ctr.x + math.cos(ang) * d, ctr.y + math.sin(ang) * d, ctr.z)
    back.rotation_euler = (math.radians(90), 0, ang + math.pi)
    back.data.materials.append(make_material("studio_back", (BG_GREY * 1.15,) * 3,
                                            roughness=0.7))

    # ---- mundo: gris neutro suave ----
    w = bpy.data.worlds.new("estudio") if not bpy.data.worlds else bpy.data.worlds[0]
    sc.world = w
    w.use_nodes = True
    bg = next((n for n in w.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg:
        bg.inputs[0].default_value = (BG_GREY, BG_GREY, BG_GREY, 1.0)
        bg.inputs[1].default_value = 1.0

    # ---- luces suaves tipo softbox ----
    def area(name, loc, look, power, sz):
        bpy.ops.object.light_add(type="AREA", location=loc)
        L = bpy.context.object
        L.name = name
        L.data.energy = power
        L.data.size = sz
        L.data.shape = "SQUARE"
        v = (Vector(look) - Vector(loc)).normalized()
        L.rotation_euler = v.to_track_quat("-Z", "Y").to_euler()
        return L

    top = Vector((ctr.x, ctr.y, ctr.z + size * 0.9))
    area("LUZ_KEY", (ctr.x - size * 1.15, ctr.y - size * 1.05, ctr.z + size * 1.25),
         top, 260.0 * size * size, size * 1.6)
    area("LUZ_FILL", (ctr.x + size * 1.35, ctr.y - size * 0.55, ctr.z + size * 0.45),
         top, 70.0 * size * size, size * 2.2)
    area("LUZ_RIM", (ctr.x + size * 0.35, ctr.y + size * 1.30, ctr.z + size * 0.80),
         top, 120.0 * size * size, size * 1.4)

    # ---- camara ----
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.name = "CAM_ESTUDIO"
    sc.camera = cam
    cam.data.lens = 78.0
    az, el = math.radians(CAM_AZIM), math.radians(CAM_ELEV)
    dist = size * CAM_DIST
    cam.location = (ctr.x + dist * math.cos(az) * math.cos(el),
                    ctr.y + dist * math.sin(az) * math.cos(el),
                    ctr.z + dist * math.sin(el) + size * 0.08)
    aim = bpy.data.objects.new("MIRA", None)
    bpy.context.collection.objects.link(aim)
    aim.location = (ctr.x, ctr.y, ctr.z + size * 0.02)
    tgt = cam.constraints.new("TRACK_TO")
    tgt.target = aim
    tgt.track_axis = "TRACK_NEGATIVE_Z"
    tgt.up_axis = "UP_Y"
    if DOF:
        cam.data.dof.use_dof = True
        cam.data.dof.focus_object = aim
        cam.data.dof.aperture_fstop = 5.6
    return cam


def main():
    path = find_obj()
    print("Importando:", path)
    reset_scene()
    objs = import_model(path)
    assign_pbr()
    mn, mx = bounds(objs)
    print("Bounding box (m):", tuple(round(v, 4) for v in mn), tuple(round(v, 4) for v in mx))
    build_studio(mn, mx)
    out = os.path.join(HERE, "render")
    bpy.context.scene.render.filepath = os.path.join(out, "robot_modular_")
    bpy.context.scene.render.image_settings.file_format = "PNG"
    print("Renderizando en", out, "...")
    bpy.ops.render.render(write_still=True)
    print("Listo.")


if __name__ == "__main__":
    main()
