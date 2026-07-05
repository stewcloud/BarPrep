import os
import tempfile
from PIL import Image

# PILLOW_ANTIALIAS_COMPAT: Pillow 10 removed Image.ANTIALIAS, but brother_ql still references it.
try:
    from PIL import Image as _PIL_Image
    if not hasattr(_PIL_Image, "ANTIALIAS"):
        _PIL_Image.ANTIALIAS = _PIL_Image.Resampling.LANCZOS
except Exception:
    pass


PRINT_MODE = os.getenv("PRINT_MODE", "mock")
BROTHER_MODEL = os.getenv("BROTHER_MODEL", "QL-820NWB")
BROTHER_PRINTER = os.getenv("BROTHER_PRINTER", "tcp://192.168.1.156:9100")
BROTHER_LABEL = os.getenv("BROTHER_LABEL", "62")


def print_png(img: Image.Image) -> str:
    """
    Print a rendered 1-bit PIL image.

    mock mode:
      saves to /tmp and reports success.

    brother_ql mode:
      uses brother_ql's Python API to send raster data directly to the printer.

    Note:
      On some environments, QL-820NWB may require a newer brother_ql than pip has.
      If that happens, keep PRINT_MODE=mock while we swap the adapter to your
      running brother_ql_web container or pin a GitHub version.
    """
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img.save(tmp.name)
        tmp_path = tmp.name

    if PRINT_MODE == "mock":
        return f"Mock print OK. Label image saved at {tmp_path}"

    if PRINT_MODE != "brother_ql":
        return f"Unknown PRINT_MODE={PRINT_MODE}. Nothing printed."

    try:
        from brother_ql.conversion import convert
        from brother_ql.backends.helpers import send
        from brother_ql.raster import BrotherQLRaster

        qlr = BrotherQLRaster(BROTHER_MODEL)
        qlr.exception_on_warning = True

        instructions = convert(
            qlr=qlr,
            images=[tmp_path],
            label=BROTHER_LABEL,
            rotate="0",
            threshold=70.0,
            dither=False,
            compress=True,
            red=False,
            dpi_600=False,
            hq=True,
            cut=True,
        )

        send(
            instructions=instructions,
            printer_identifier=BROTHER_PRINTER,
            backend_identifier="network",
            blocking=True,
        )
        return "Printed label successfully."
    except Exception as exc:
        return f"Print failed: {exc}"
