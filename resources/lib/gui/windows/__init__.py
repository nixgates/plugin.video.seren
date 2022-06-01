from resources.lib.common import source_utils
from resources.lib.modules.globals import g


def set_info_properties(info, item):
    """
    Set standard properties for an item.
    The item can be anything that supports a setProperty() method such as window or list item
    :param info: The info set from the source
    :type info: set
    :param item: xbmcgui element with setProperty() method
    """
    struct_info = source_utils.info_set_to_dict(info)
    codec_type_display_list = ["hdrcodec", "videocodec", "misc", "audiocodec", "audiochannels"]
    color_tag = "[COLOR {}]".format(g.get_user_text_color())

    item.setProperty(
        "info_text",
        " | ".join(
            [
                " ".join(struct_info[c])
                for c in codec_type_display_list
                if struct_info[c]
            ]
        ),
    )

    item.setProperty(
        "info_text_formatted",
        " | ".join(
            [
                "{}{}[/COLOR]".format(color_tag, " ".join(struct_info[c]))
                for c in codec_type_display_list
                if struct_info[c]
            ]
        ),
    )

    for prop in struct_info:
        item.setProperty("info.{}_text".format(prop), " ".join(struct_info[prop]))
        for n in range(0, len(struct_info[prop])):
            item.setProperty("info.{}_{}".format(prop, n + 1), struct_info[prop][n])
