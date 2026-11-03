# Renders flag-icons (MIT, github.com/lipis/flag-icons) 4x3 SVGs to small PNGs with the system librsvg + cairo.
import ctypes, os, sys
src, out, W, H = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
rsvg = ctypes.CDLL("librsvg-2.so.2"); cairo = ctypes.CDLL("libcairo.so.2"); gobj = ctypes.CDLL("libgobject-2.0.so.0")
class Rect(ctypes.Structure): _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double), ("width", ctypes.c_double), ("height", ctypes.c_double)]
rsvg.rsvg_handle_new_from_file.restype = ctypes.c_void_p; rsvg.rsvg_handle_new_from_file.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
rsvg.rsvg_handle_render_document.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(Rect), ctypes.c_void_p]
cairo.cairo_image_surface_create.restype = ctypes.c_void_p; cairo.cairo_create.restype = ctypes.c_void_p; cairo.cairo_create.argtypes = [ctypes.c_void_p]
cairo.cairo_surface_write_to_png.argtypes = [ctypes.c_void_p, ctypes.c_char_p]; cairo.cairo_destroy.argtypes = [ctypes.c_void_p]; cairo.cairo_surface_destroy.argtypes = [ctypes.c_void_p]
gobj.g_object_unref.argtypes = [ctypes.c_void_p]
os.makedirs(out, exist_ok=True); n = 0
for name in sorted(os.listdir(src)):
    if not name.endswith(".svg"): continue
    h = rsvg.rsvg_handle_new_from_file(os.path.join(src, name).encode(), None)
    if not h: print("fail", name); continue
    s = cairo.cairo_image_surface_create(0, W, H); c = cairo.cairo_create(s)
    ok = rsvg.rsvg_handle_render_document(h, c, ctypes.byref(Rect(0, 0, W, H)), None)
    cairo.cairo_surface_write_to_png(s, os.path.join(out, name[:-4] + ".png").encode())
    cairo.cairo_destroy(c); cairo.cairo_surface_destroy(s); gobj.g_object_unref(h); n += 1
print("rendered", n)
