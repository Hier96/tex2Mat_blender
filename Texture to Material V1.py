bl_info = {
    "name": "Texture to Material V1 with Advanced Features",
    "blender": (4, 0, 0),
    "category": "Object",
    "description": "Apply textures with auto-fill and correct color space.",
    "author": "肖彤",
    "version": (1, 8),
    "location": "View3D > Sidebar > Texture to Material Tab",
}

import bpy
import os
from bpy.props import StringProperty, PointerProperty, EnumProperty
from bpy.types import Operator, Panel, PropertyGroup

class TexturePaths(PropertyGroup):
    base_color: StringProperty(name="Base Color", subtype='FILE_PATH')
    metallic: StringProperty(name="Metallic", subtype='FILE_PATH')
    roughness: StringProperty(name="Roughness", subtype='FILE_PATH')
    alpha: StringProperty(name="Alpha", subtype='FILE_PATH')
    normal: StringProperty(name="Normal", subtype='FILE_PATH')
    emission: StringProperty(name="Emission", subtype='FILE_PATH')
    material_name: StringProperty(name="Material Name", description="Name for the created material", default="NewMaterial")
    available_materials: EnumProperty(
        name="Available Materials",
        description="Choose a material to assign",
        items=lambda self, context: [(mat.name, mat.name, "") for mat in bpy.data.materials]
    )

def auto_fill_textures(base_path, settings):
    if base_path:
        try:
            files = os.listdir(base_path)
            texture_types = ["metallic", "roughness", "alpha", "normal", "emission"]
            for tex_type in texture_types:
                for file in files:
                    if tex_type in file.lower():
                        setattr(settings, tex_type, os.path.join(base_path, file))
                        break
        except Exception as e:
            print("自动填充下列路径失败:", e)

class OBJECT_OT_apply_complex_textures(Operator):
    bl_idname = "object.apply_complex_textures"
    bl_label = "Apply Textures"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.texture_settings
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                apply_material(obj, settings)
                clear_texture_paths(settings)
        return {'FINISHED'}

def apply_material(obj, settings):
    material_name = settings.material_name
    material = bpy.data.materials.new(name=material_name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = 0, 0

    output = nodes.new(type="ShaderNodeOutputMaterial")
    output.location = 400, 0

    texture_settings = {
        "base_color": ("Base Color", "sRGB"),
        "metallic": ("Metallic", "Non-Color"),
        "roughness": ("Roughness", "Non-Color"),
        "alpha": ("Alpha", "Non-Color"),
        "normal": ("Normal", "Non-Color"),
        "emission": ("Emission", "sRGB"),
    }

    for tex_name, (input_name, color_space) in texture_settings.items():
        filepath = getattr(settings, tex_name)
        if filepath:
            tex_node = nodes.new(type="ShaderNodeTexImage")
            tex_node.image = bpy.data.images.load(filepath)
            tex_node.location = (-300, 0)
            tex_node.image.colorspace_settings.name = color_space

            if tex_name == "normal":
                normal_map = nodes.new(type="ShaderNodeNormalMap")
                normal_map.location = (-600, 0)
                links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
                links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
            else:
                links.new(tex_node.outputs['Color'], bsdf.inputs[input_name])

    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)

def clear_texture_paths(settings):
    settings.base_color = ""
    settings.metallic = ""
    settings.roughness = ""
    settings.alpha = ""
    settings.normal = ""
    settings.emission = ""

class OBJECT_OT_auto_fill_textures(Operator):
    bl_idname = "object.auto_fill_textures"
    bl_label = "自动填充下列路径"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.texture_settings
        base_path = os.path.dirname(bpy.path.abspath(settings.base_color))
        auto_fill_textures(base_path, settings)
        return {'FINISHED'}

class OBJECT_OT_assign_material_to_objects(Operator):
    bl_idname = "object.assign_material_to_objects"
    bl_label = "Assign Material to Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.texture_settings
        material_name = settings.available_materials
        if material_name:
            material = bpy.data.materials.get(material_name)
            if material:
                for obj in context.selected_objects:
                    if obj.type == 'MESH':
                        if obj.data.materials:
                            obj.data.materials[0] = material
                        else:
                            obj.data.materials.append(material)
                self.report({'INFO'}, f"Assigned material '{material_name}' to selected objects.")
            else:
                self.report({'ERROR'}, f"Material '{material_name}' not found.")
        else:
            self.report({'ERROR'}, "No material selected.")
        return {'FINISHED'}

class TEXTURE_PT_custom_panel(Panel):
    bl_label = "Texture to Material V1"
    bl_idname = "TEXTURE_PT_custom"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Texture to Material'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene.texture_settings, "material_name")
        layout.prop(scene.texture_settings, "base_color")
        layout.operator("object.auto_fill_textures", text="自动填充下列路径")
        layout.prop(scene.texture_settings, "metallic")
        layout.prop(scene.texture_settings, "roughness")
        layout.prop(scene.texture_settings, "alpha")
        layout.prop(scene.texture_settings, "normal")
        layout.prop(scene.texture_settings, "emission")
        layout.operator("object.apply_complex_textures")
        layout.separator()
        layout.label(text="Assign Existing Material:")
        layout.prop(scene.texture_settings, "available_materials", text="Material")
        layout.operator("object.assign_material_to_objects", text="Assign Material")

def register():
    bpy.utils.register_class(TexturePaths)
    bpy.utils.register_class(OBJECT_OT_apply_complex_textures)
    bpy.utils.register_class(OBJECT_OT_auto_fill_textures)
    bpy.utils.register_class(OBJECT_OT_assign_material_to_objects)
    bpy.utils.register_class(TEXTURE_PT_custom_panel)
    bpy.types.Scene.texture_settings = PointerProperty(type=TexturePaths)

def unregister():
    bpy.utils.unregister_class(TexturePaths)
    bpy.utils.unregister_class(OBJECT_OT_apply_complex_textures)
    bpy.utils.unregister_class(OBJECT_OT_auto_fill_textures)
    bpy.utils.unregister_class(OBJECT_OT_assign_material_to_objects)
    bpy.utils.unregister_class(TEXTURE_PT_custom_panel)
    del bpy.types.Scene.texture_settings

if __name__ == "__main__":
    register()
