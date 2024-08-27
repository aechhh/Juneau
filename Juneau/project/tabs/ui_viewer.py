def _open_ui_view(sender, app_data, user_data):
    if g_current_obj_in_view == None:
        print("No object in view")
        return

    ui_elems : list[ObjectInstance] = g_current_obj_in_view.field_data[0].external_list_objects

    assert len(ui_elems) != 0

    with dpg.window(label="UI Viewer"):
        for obj_inst in ui_elems:
            base_elem : ObjectInstance = obj_inst.get_obj_param('BaseElement').subobjects[0]

            ui_rendering_data_id = base_elem.get_obj_param('UIRenderingData').resource_handles[0]["obj_id_1"]

            # struct bs needed to convert from unsigned to signed int
            # todo refactor this whole code base this whole thing is evil and fucked up
            pos_x = unpack("i", pack("I", base_elem.get_obj_param('PositionX').data[0]))[0]
            pos_y = unpack("i", pack("I", base_elem.get_obj_param('PositionY').data[0]))[0]

            name = obj_inst.obj_def.obj_name

            ui_obj : ObjectInstance = None

            for obj in g_genesys_instances:
                if obj.id == ui_rendering_data_id:
                    ui_obj = obj
                    break
            else:
                raise Exception("Couldnt find matching ui object")

            texture_handle = ui_obj.get_obj_param('TextureHandle')

            if texture_handle.resource_handles[0] != None:
                texture_id = texture_handle.resource_handles[0]["obj_id_1"]

                texture_tag = None

                for texture in g_textures:
                    if texture.id == texture_id:
                        texture_tag = texture.dpg_tag
                        break
                else:
                    raise Exception("Couldnt find matching texture for ui object")

                dpg.add_image(texture_tag, pos=(pos_x, pos_y))

            else:
                dpg.draw_text((pos_x, pos_y), name, color=(250, 250, 250, 255), size=15)
