bl_info = {
    "name": "Marker Groups",
    "author": "Rowboat23",
    "version": (1, 5, 0),
    "blender": (5, 0, 0),
    "location": "Graph Editor / Dope Sheet / Sequencer > Sidebar",
    "description": "Group timeline markers and toggle their visibility safely, now with delete button",
    "category": "Animation",
    "URL": "https://github.com/RowBoat23/Marker-Groups-Blender-Add-On",
}

import bpy
from bpy.types import PropertyGroup, Operator, Panel
from bpy.props import StringProperty, BoolProperty, IntProperty, CollectionProperty

# -------------------------------------------------
# Constants
# -------------------------------------------------
HIDE_FRAME = -1000000

# -------------------------------------------------
# PropertyGroups
# -------------------------------------------------
class MarkerRef(PropertyGroup):
    """Stores a reference to a timeline marker"""
    name: StringProperty()
    frame: IntProperty()


class MarkerGroupItem(PropertyGroup):
    """Stores a group of MarkerRefs"""
    name: StringProperty(default="Group")
    visible: BoolProperty(default=True)
    markers: CollectionProperty(type=MarkerRef)

# -------------------------------------------------
# Utilities
# -------------------------------------------------
def find_markers_by_ref(scene, ref):
    return [m for m in scene.timeline_markers if m.name == ref.name and m.frame == ref.frame]

# -------------------------------------------------
# Operators
# -------------------------------------------------
class MARKERGROUPS_OT_make_group(Operator):
    bl_idname = "markergroups.make_group"
    bl_label = "Make New Group"

    name: StringProperty(default="New Group")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        g = context.scene.marker_groups.add()
        g.name = self.name
        g.visible = True
        self.report({'INFO'}, f"Created group '{self.name}'")
        return {'FINISHED'}


class MARKERGROUPS_OT_assign_selected(Operator):
    bl_idname = "markergroups.assign_selected"
    bl_label = "Assign Selected Markers"

    group_index: IntProperty()

    def execute(self, context):
        scene = context.scene
        group = scene.marker_groups[self.group_index]

        selected = [m for m in scene.timeline_markers if m.select]
        if not selected:
            self.report({'WARNING'}, "No selected markers")
            return {'CANCELLED'}

        for m in selected:
            ref = group.markers.add()
            ref.name = m.name
            ref.frame = m.frame

        self.report({'INFO'}, f"Assigned {len(selected)} markers to '{group.name}'")
        return {'FINISHED'}


class MARKERGROUPS_OT_remove_selected(Operator):
    bl_idname = "markergroups.remove_selected"
    bl_label = "Remove Selected Markers"

    group_index: IntProperty()

    def execute(self, context):
        scene = context.scene
        group = scene.marker_groups[self.group_index]

        to_remove = []
        for i, ref in enumerate(group.markers):
            for m in scene.timeline_markers:
                if m.select and m.name == ref.name and m.frame == ref.frame:
                    to_remove.append(i)

        for i in reversed(to_remove):
            group.markers.remove(i)

        self.report({'INFO'}, f"Removed {len(to_remove)} markers from '{group.name}'")
        return {'FINISHED'}


class MARKERGROUPS_OT_toggle_visibility(Operator):
    bl_idname = "markergroups.toggle_visibility"
    bl_label = "Toggle Visibility"

    group_index: IntProperty()

    def execute(self, context):
        scene = context.scene
        group = scene.marker_groups[self.group_index]

        if group.visible:
            # Hide all markers
            for ref in group.markers:
                for m in find_markers_by_ref(scene, ref):
                    m.frame = HIDE_FRAME
        else:
            # Restore all markers
            for ref in group.markers:
                hidden = [m for m in scene.timeline_markers if m.name == ref.name and m.frame == HIDE_FRAME]
                for m in hidden:
                    m.frame = ref.frame
                    break

        group.visible = not group.visible
        return {'FINISHED'}


class MARKERGROUPS_OT_resync(Operator):
    bl_idname = "markergroups.resync"
    bl_label = "Update Stored Positions"

    group_index: IntProperty()

    def execute(self, context):
        scene = context.scene
        group = scene.marker_groups[self.group_index]

        if not group.visible:
            self.report({'WARNING'}, "Group hidden — cannot resync")
            return {'CANCELLED'}

        count = 0
        for ref in group.markers:
            for m in scene.timeline_markers:
                if m.name == ref.name:
                    ref.frame = m.frame
                    count += 1
                    break

        self.report({'INFO'}, f"Resynced {count} markers for '{group.name}'")
        return {'FINISHED'}


class MARKERGROUPS_OT_delete_group(Operator):
    bl_idname = "markergroups.delete_group"
    bl_label = "Delete Marker Group"
    bl_description = "Delete this marker group"

    group_index: IntProperty()

    def execute(self, context):
        scene = context.scene
        group = scene.marker_groups[self.group_index]
        scene.marker_groups.remove(self.group_index)
        self.report({'INFO'}, f"Deleted group '{group.name}'")
        return {'FINISHED'}

# -------------------------------------------------
# Panel
# -------------------------------------------------
class MARKERGROUPS_PT_base:
    bl_label = "Marker Groups"
    bl_region_type = 'UI'
    bl_category = 'Marker Groups'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.operator("markergroups.make_group", icon="ADD")

        for i, g in enumerate(scene.marker_groups):
            box = layout.box()
            row = box.row(align=True)

            # Eye toggle
            icon = 'HIDE_OFF' if g.visible else 'HIDE_ON'
            t = row.operator("markergroups.toggle_visibility", text="", icon=icon, emboss=False)
            t.group_index = i

            # Group name
            row.prop(g, "name", text="")

            # Delete button (X)
            delete_op = row.operator("markergroups.delete_group", text="", icon='X', emboss=True)
            delete_op.group_index = i

            # Assign / Remove / Update row
            row2 = box.row(align=True)
            a = row2.operator("markergroups.assign_selected", text="Assign")
            a.group_index = i
            r = row2.operator("markergroups.remove_selected", text="Remove")
            r.group_index = i
            u = row2.operator("markergroups.resync", text="Update")
            u.group_index = i


class MARKERGROUPS_PT_graph(MARKERGROUPS_PT_base, Panel):
    bl_space_type = 'GRAPH_EDITOR'


class MARKERGROUPS_PT_dopesheet(MARKERGROUPS_PT_base, Panel):
    bl_space_type = 'DOPESHEET_EDITOR'


class MARKERGROUPS_PT_sequencer(MARKERGROUPS_PT_base, Panel):
    bl_space_type = 'SEQUENCE_EDITOR'

# -------------------------------------------------
# Registration
# -------------------------------------------------
classes = (
    MarkerRef,
    MarkerGroupItem,
    MARKERGROUPS_OT_make_group,
    MARKERGROUPS_OT_assign_selected,
    MARKERGROUPS_OT_remove_selected,
    MARKERGROUPS_OT_toggle_visibility,
    MARKERGROUPS_OT_resync,
    MARKERGROUPS_OT_delete_group,
    MARKERGROUPS_PT_graph,
    MARKERGROUPS_PT_dopesheet,
    MARKERGROUPS_PT_sequencer,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.marker_groups = CollectionProperty(type=MarkerGroupItem)

def unregister():
    del bpy.types.Scene.marker_groups
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
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

