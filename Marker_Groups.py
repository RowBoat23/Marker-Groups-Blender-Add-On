bl_info = {
    "name": "Marker Groups",
    "author": "RowBoat23",
    "version": (1, 3, 0),
    "blender": (3, 5, 0),
    "location": "Graph Editor / Dope Sheet / Sequencer > Sidebar",
    "description": "Group timeline markers, rename groups, assign/remove, toggle visibility, and update stored positions",
    "category": "Animation",
}

import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import StringProperty, BoolProperty, CollectionProperty


# -----------------------------------------
# Utilities
# -----------------------------------------

def get_group_markers(scene, group_name):
    return [m for m in scene.timeline_markers if m.get("group") == group_name]


def update_group_name(self, context):
    scene = context.scene
    old_name = self.old_name
    new_name = self.name

    for m in scene.timeline_markers:
        if m.get("group") == old_name:
            m["group"] = new_name

    self.old_name = new_name


def update_group_visibility(self, context):
    scene = context.scene
    group_name = self.name
    markers = get_group_markers(scene, group_name)

    if not markers:
        return

    if self.visible:
        for m in markers:
            if "orig_frame" in m:
                m.frame = m["orig_frame"]
    else:
        for m in markers:
            if "orig_frame" not in m:
                m["orig_frame"] = m.frame
            m.frame = -999999


# -----------------------------------------
# Properties
# -----------------------------------------

class MarkerGroupItem(PropertyGroup):
    name: StringProperty(
        name="Group Name",
        default="Group",
        update=update_group_name
    )
    visible: BoolProperty(
        name="Visible",
        default=True,
        update=update_group_visibility
    )

    old_name: StringProperty(default="")


# -----------------------------------------
# Operators
# -----------------------------------------

class MARKERGROUPS_OT_make_group(Operator):
    bl_idname = "markergroups.make_group"
    bl_label = "Make New Group"

    group_name: StringProperty(name="Group Name", default="NewGroup")

    def execute(self, context):
        scene = context.scene

        if any(g.name == self.group_name for g in scene.marker_groups):
            self.report({'WARNING'}, f"Group '{self.group_name}' already exists.")
            return {'CANCELLED'}

        g = scene.marker_groups.add()
        g.name = self.group_name
        g.old_name = self.group_name
        g.visible = True

        self.report({'INFO'}, f"Created group '{self.group_name}'")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class MARKERGROUPS_OT_assign_selected(Operator):
    bl_idname = "markergroups.assign_selected"
    bl_label = "Assign Selected Markers"

    group_name: StringProperty()

    def execute(self, context):
        scene = context.scene
        selected = [m for m in scene.timeline_markers if m.select]

        if not selected:
            self.report({'WARNING'}, "No selected markers!")
            return {'CANCELLED'}

        for m in selected:
            m["group"] = self.group_name
            m["orig_frame"] = m.frame

        self.report({'INFO'}, f"Assigned {len(selected)} markers to '{self.group_name}'")
        return {'FINISHED'}


class MARKERGROUPS_OT_remove_selected(Operator):
    bl_idname = "markergroups.remove_selected"
    bl_label = "Remove Selected Markers from Group"

    group_name: StringProperty()

    def execute(self, context):
        scene = context.scene
        selected = [m for m in scene.timeline_markers if m.select and m.get("group") == self.group_name]

        if not selected:
            self.report({'WARNING'}, "No selected markers in this group!")
            return {'CANCELLED'}

        for m in selected:
            del m["group"]

        self.report({'INFO'}, f"Removed {len(selected)} markers from '{self.group_name}'")
        return {'FINISHED'}


class MARKERGROUPS_OT_update_orig_frames(Operator):
    bl_idname = "markergroups.update_orig_frames"
    bl_label = "Update Stored Positions"

    group_name: StringProperty()

    def execute(self, context):
        scene = context.scene
        markers = get_group_markers(scene, self.group_name)

        if not markers:
            self.report({'WARNING'}, "No markers in this group to update.")
            return {'CANCELLED'}

        for m in markers:
            m["orig_frame"] = m.frame

        self.report({'INFO'}, f"Updated {len(markers)} markers for '{self.group_name}'")
        return {'FINISHED'}


# -----------------------------------------
# Panels (multi-editor)
# -----------------------------------------

class MARKERGROUPS_PT_base:
    bl_label = "Marker Groups"
    bl_region_type = 'UI'
    bl_category = 'Marker Groups'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.operator("markergroups.make_group", icon="ADD")

        layout.separator()

        if not scene.marker_groups:
            layout.label(text="No groups yet.")
        else:
            for group in scene.marker_groups:
                row = layout.row(align=True)
                icon = 'HIDE_OFF' if group.visible else 'HIDE_ON'
                row.prop(group, "visible", text="", icon=icon, emboss=False)  # Eye first!
                row.prop(group, "name", text="")

                row = layout.row(align=True)
                assign = row.operator("markergroups.assign_selected", text="Assign")
                assign.group_name = group.name

                remove = row.operator("markergroups.remove_selected", text="Remove")
                remove.group_name = group.name

                update = row.operator("markergroups.update_orig_frames", text="Update")
                update.group_name = group.name


class MARKERGROUPS_PT_graph_editor(MARKERGROUPS_PT_base, Panel):
    bl_space_type = 'GRAPH_EDITOR'


class MARKERGROUPS_PT_dopesheet(MARKERGROUPS_PT_base, Panel):
    bl_space_type = 'DOPESHEET_EDITOR'


class MARKERGROUPS_PT_sequencer(MARKERGROUPS_PT_base, Panel):
    bl_space_type = 'SEQUENCE_EDITOR'


# -----------------------------------------
# Register / Unregister
# -----------------------------------------

classes = (
    MarkerGroupItem,
    MARKERGROUPS_OT_make_group,
    MARKERGROUPS_OT_assign_selected,
    MARKERGROUPS_OT_remove_selected,
    MARKERGROUPS_OT_update_orig_frames,
    MARKERGROUPS_PT_graph_editor,
    MARKERGROUPS_PT_dopesheet,
    MARKERGROUPS_PT_sequencer,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.marker_groups = CollectionProperty(type=MarkerGroupItem)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.marker_groups

if __name__ == "__main__":
    register()
