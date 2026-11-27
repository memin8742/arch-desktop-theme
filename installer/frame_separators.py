"""Extend GTK's vertical separators through the Xfwm theme's bottom margin."""
import ctypes as C


class Cookie(C.Structure):
    _fields_ = [('sequence', C.c_uint)]


class Tree(C.Structure):
    _fields_ = [('header', C.c_uint64), ('root', C.c_uint32), ('parent', C.c_uint32)]


class Geometry(C.Structure):
    _fields_ = [('header', C.c_uint64), ('root', C.c_uint32),
                ('x', C.c_int16), ('y', C.c_int16), ('width', C.c_uint16), ('height', C.c_uint16)]


def bind(library, name, result, *arguments):
    function = getattr(library, name)
    function.restype = result
    function.argtypes = arguments
    return function


class FrameSeparators:
    def __init__(self):
        xcb = C.CDLL('libxcb.so.1')
        shape = C.CDLL('libxcb-shape.so.0')
        pointer = C.c_void_p
        resource = C.c_uint32
        self.connection = bind(xcb, 'xcb_connect', pointer, C.c_char_p, pointer)(None, None)
        self.disconnect = bind(xcb, 'xcb_disconnect', None, pointer)
        self.flush = bind(xcb, 'xcb_flush', C.c_int, pointer)
        self.free = bind(C.CDLL(None), 'free', None, pointer)
        self.tree = bind(xcb, 'xcb_query_tree', Cookie, pointer, resource)
        self.read_tree = bind(xcb, 'xcb_query_tree_reply', pointer, pointer, Cookie, pointer)
        self.geometry = bind(xcb, 'xcb_get_geometry', Cookie, pointer, resource)
        self.read_geometry = bind(xcb, 'xcb_get_geometry_reply', pointer, pointer, Cookie, pointer)
        self.generate_id = bind(xcb, 'xcb_generate_id', resource, pointer)
        self.create_window = bind(xcb, 'xcb_create_window', Cookie, pointer, C.c_uint8,
            resource, resource, C.c_int16, C.c_int16, C.c_uint16, C.c_uint16,
            C.c_uint16, C.c_uint16, resource, resource, pointer)
        self.set_shape = bind(shape, 'xcb_shape_rectangles', Cookie, pointer, C.c_uint8,
            C.c_uint8, C.c_uint8, resource, C.c_int16, C.c_int16, resource, pointer)
        self.map_window = bind(xcb, 'xcb_map_window', Cookie, pointer, resource)
        self.destroy_window = bind(xcb, 'xcb_destroy_window', Cookie, pointer, resource)
        self.windows = []
        self.layout = None

    def reply(self, request, read, layout, window):
        reply = read(self.connection, request(self.connection, window), None)
        if not reply: return None
        try:
            return layout.from_buffer_copy(C.string_at(reply, C.sizeof(layout)))
        finally:
            self.free(reply)

    def clear(self):
        for window in self.windows:
            self.destroy_window(self.connection, window)
        self.windows.clear()
        self.layout = None
        self.flush(self.connection)

    def close(self):
        self.disconnect(self.connection)

    def sync(self, client, separators):
        if not separators:
            self.clear()
            return
        tree = self.reply(self.tree, self.read_tree, Tree, client)
        child = self.reply(self.geometry, self.read_geometry, Geometry, client)
        frame = self.reply(self.geometry, self.read_geometry, Geometry, tree.parent) if tree else None
        if not frame or not child or tree.parent == tree.root:
            self.clear()
            return
        bottom = child.y + child.height
        if frame.height - bottom != 20 or child.x != 3:
            # Arch Blue's rounded frame is absent or clipped by the WM.
            self.clear()
            return
        columns = tuple((x + child.x, y + child.y, width) for x, y, width in separators
                        if 20 <= x < child.width - 20 and 0 <= child.height - y <= 4)
        layout = (tree.parent, bottom, columns)
        if self.layout == layout: return
        self.clear()
        self.layout = layout
        # Background and override-redirect are ordered by the XCB value-mask bits.
        values = (C.c_uint32 * 2)(0xff2e729d, 1)
        for x, y, width in columns:
            window = self.generate_id(self.connection)
            self.create_window(self.connection, 0, window, tree.parent, x, y,
                width, frame.height - y - 1, 0, 1, 0, (1 << 1) | (1 << 9), values)
            # An empty input shape leaves the WM's resize area usable.
            self.set_shape(self.connection, 0, 2, 0, window, 0, 0, 0, None)
            self.map_window(self.connection, window)
            self.windows.append(window)
        self.flush(self.connection)
