import struct, sys
from PIL import Image, ImageChops
from io import BufferedReader
from pathlib import Path
from array import array
from contextlib import contextmanager
import toml
from math import floor

# DO NOT CHANGE
ART_VERSION = 1
# I don't know what is actually the max tile size for BUILD (probably sizeof(short) ^ 2),
# but I feel like this is a sensible maximum from an aesthetic/size point of view
# TODO: Check if all of D3Ds tiles don't exceed this
MAX_TILE_SIZE = 256.0
MAX_TILE_SIZE_SQUARE = MAX_TILE_SIZE * MAX_TILE_SIZE

# DO NOT CHANGE
C_SHORT = "<h"
C_SHORT_LEN = struct.calcsize(C_SHORT)
C_SHORT_UNPACK = struct.Struct(C_SHORT).unpack_from
C_LONG = "<l"
C_LONG_LEN = struct.calcsize(C_LONG)
C_LONG_UNPACK = struct.Struct(C_LONG).unpack_from
C_UCHAR = "<B"
C_UCHAR_LEN = struct.calcsize(C_UCHAR)
C_UCHAR_UNPACK = struct.Struct(C_UCHAR).unpack_from
C_UCHAR3 = "<BBB"
C_UCHAR3_LEN = struct.calcsize(C_UCHAR3)
C_UCHAR3_UNPACK = struct.Struct(C_UCHAR3).unpack_from

# TOML config
# the sets aren't used anywhere, reference only
ART_CONFIG_OPTIONS: set[str] = { 'numtiles', 'starttile' }
TILE_CONFIG_OPTIONS: set[str] = { 'x', 'y', 'frames', 'animtype', 'speed', 'dither', 'offscorrect', 'nocorrectx', 'nocorrecty', 'correct_pivot_x', 'correct_pivot_y' }
DEFAULT_CONFIG: dict[str, dict[str, int]] = {'art': {'start': 0, 'length': 256}}
g_config = dict()

# 241 color palette (excludes fullbright colors)
g_palette: Image.Image = Image.Image()

# Contains the tilesend-tilesstart+1
g_art_numtiles: int = 256
# Contains real amount of tiles
g_art_lasttile: int = 0

g_art_tilesstart: int = 0
g_art_tilesend: int = 255

g_art_tilesizex: array[int] = array('H', [0] * 256)
g_art_tilesizey: array[int] = array('H', [0] * 256)
g_art_picanms: array[int] = array('l', [0] * 256)
g_art_tile_data: list[bytes] = [bytes(0)] * 256
g_export: bytearray = bytearray(0)

g_offscorrect_remaining: int = 0
g_offscorrect_reference_tile: int = 0
g_offscorrect_mode: int = 0
g_offscorrect_pivot: list[ int | None ] = [None] * 4

# Not used anywhere, but should still be valid
g_export_offset: int = 0

@contextmanager
def PILImage(filep: Path):
    img = Image.open(filep)
    try:
        yield img
    finally:
        img.close()

def is_powerof2(n: int) -> bool:
    "Is power of 2. Zero returns true"
    return bool(n & (n-1) == 0)

def reinit_globals(filep: Path) -> None:
    "Reads in config, and accomodates for ART file size"
    global g_art_numtiles, g_art_tilesend, g_art_tilesstart, g_art_tilesizey, g_art_tilesizex, g_art_picanms, g_art_tile_data

    try:
        read_config(filep / 'config.toml')
    except:
        if not (filep / 'config.toml').exists():
            with open((filep / 'config.toml'), "w") as f:
                print("Config file not present, creating default!")
                _ = toml.dump(o=DEFAULT_CONFIG, f=f)
        return

    g_art_tilesstart = configgetattrib_int('art', 'start')
    g_art_tilesend = g_art_tilesstart + (configgetattrib_int('art', 'length') - 1)
    if g_art_tilesstart > g_art_tilesend or g_art_tilesstart == g_art_tilesend:
        print("Invalid ART start & end values!")
        print_usage(error=True)

    if (g_art_tilesstart % configgetattrib_int('art', 'length')) != 0:
        print("WARNING: ART start is not a multiple of length! This could cause issues!")
    if not is_powerof2(configgetattrib_int('art', 'length')):
        print("""
        WARNING: ART length is not power of 2! This will cause issues!
        You have to use a power of 2 value!
              """)

    g_art_numtiles = g_art_tilesend - g_art_tilesstart + 1

    g_art_tilesizex = array('H', [0] * g_art_numtiles)
    g_art_tilesizey = array('H', [0] * g_art_numtiles)
    g_art_picanms = array('l', [0] * g_art_numtiles)
    g_art_tile_data = [bytes(0)] * g_art_numtiles

def read_config(filep: Path) -> None:
    global g_config
    try:
        with open(filep, "r") as f:
            g_config = toml.load(f)
    except Exception as error:
        print(f"Couldn't find/parse config file: {filep}")
        print(error)
        raise Exception('Hack cuz Im lazy')

def read_palette(filep: Path):
    global g_palette
    tmp: list[int] = []
    try:
        with open(filep, "rb") as f:
            for _ in range(240):
                rgb = read_3_unsigned_chars(f)
                
                # Undo a DOS optimization by multiplying the palette values by 4
                tmp.extend(map(( lambda c: c << 2 ), rgb))

        g_palette = Image.new('P', (16, 15))
        g_palette.putpalette(tmp)
    except Exception as error:
        print("Failed to read PALETTE.DAT")
        print("Error: ", error)
        sys.exit(65)

def read_short(file: BufferedReader) -> int:
    return C_SHORT_UNPACK(
            file.read(C_SHORT_LEN))[0]

def read_long(file: BufferedReader) -> int:
    return C_LONG_UNPACK(
            file.read(C_LONG_LEN))[0]

def read_unsigned_char(file: BufferedReader) -> int:
    return C_UCHAR_UNPACK(
            file.read(C_UCHAR_LEN))[0]

def read_3_unsigned_chars(file: BufferedReader) -> tuple[int]:
    return C_UCHAR3_UNPACK(
            file.read(C_UCHAR3_LEN))

def write_short(data: int) -> None:
    global g_export, g_export_offset
    g_export.extend(struct.pack(C_SHORT, data))
    g_export_offset += C_SHORT_LEN

def write_long(data: int) -> None:
    global g_export, g_export_offset
    g_export.extend(struct.pack(C_LONG, data))
    g_export_offset += C_LONG_LEN

def write_unsigned_char(data: int) -> None:
    global g_export, g_export_offset
    g_export.extend(struct.pack(C_UCHAR, data))
    g_export_offset += C_UCHAR_LEN

def write_bytearray(data: list[bytes]) -> None:
    global g_export, g_export_offset
    for byte in data:
        g_export.extend(byte)
    g_export_offset += len(data)

def ImageToBytes(image: Image.Image, dither: bool) -> bytes:
    global g_palette
    """
    Converts Image to bytes, handles transparency & palettization with optional dithering
    """
    istransparent: bool = False
    # Deal with transparency
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        istransparent = True

    if istransparent == True:
        mask = HandleTransparency(image)
        fullytransp = Image.new('L', image.size, color=(0xff))

    if image.mode != "RGB":
        image = image.convert("RGB")

    result = image.quantize(colors= 256, method=Image.Quantize.MEDIANCUT, palette=g_palette, dither=Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE)

    if istransparent == True:
        result = Image.composite(fullytransp, result, mask)

    result = result.transpose(Image.Transpose.TRANSPOSE)

    return result.tobytes()

def CorrectImageSize(image: Image.Image) -> Image.Image:
    image2 = image
    if (image.size[0] * image.size[1]) > MAX_TILE_SIZE_SQUARE:
        width_ratio = MAX_TILE_SIZE / image.size[0]
        height_ratio = MAX_TILE_SIZE / image.size[1]
        
        # Use the smaller ratio to maintain aspect ratio and fit within bounds
        scale_ratio = min(width_ratio, height_ratio)
        
        new_width = int(image.size[0] * scale_ratio)
        new_height = int(image.size[1] * scale_ratio)

        # Tiling textures break on walls if their height is not divisible by 2
        # I trust that the user is aware of this wall tiling bug, and will only
        # ever make sprites for actors that break the above rule.
        # Rescale while maintaining aspect ratio
        if new_height % 2 != 0:
            new_height += 1
            new_width += 1

        if image.format == "JPEG":
            image2 = image.resize((new_width, new_height), Image.Resampling.BILINEAR)
        else:
            image2 = image.resize((new_width, new_height), Image.Resampling.NEAREST)
    return image2

def HandleTransparency(image: Image.Image) -> Image.Image:
    image2 = image.convert('RGBA')

    alpha = image2.split()[-1]
    #alpha = ImageChops.invert(alpha)

    # Invert alpha & clamp values between 255 and 0
    # This threshold works perfectly for my horribly rotoscoped foliage
    alpha = alpha.point(lambda a: 255 if a <= 20 else 0)

    return alpha

def correct_offset(old_size: int, new_size: int, old_offset: int, old_pivot: int | None, new_pivot: int | None) -> int:
    """
    Corrects the new offset to point to the same pixel based off the old one, with
    an optional pivot (meant to be used with a 3D model's bones projected 2D coordinates eg. hand joint in viewmodel,
    though it can theoretically be a tracking marker's projected 2D coordinates from VFX/3D software)
    """
    if isinstance(old_pivot, int) and isinstance(new_pivot, int):
        cx = old_offset + (old_pivot - old_size) / 2.0
        return floor(( cx - (new_pivot - new_size) / 2.0))
    else:
        return floor(old_offset + (new_size - old_size) / 2.0)

def print_usage(error: bool) -> None:
    print("""Usage: pyartbuild [art_id]

       DESCRIPTION:
       Create a BUILD engine ART file from a directory.
       art_id=DIRECTORY
                A directory which is named 3 digits which corresponds
                to the resulting tiles###.art file's number.
       In the working directory a PALETTE.DAT file is required. A RAW
       256 color RGB palette will also work. The last 16 fullbright
       colors are omitted during palettization.
       The directory containing the input images needs to have a
       config.toml file, which gets generated on first use.
       Each tile can have attributes set in this file by specifying
       [tilenumber] with the following properties:
       'x' & 'y'         - configures offset
       'frames'          - specifies number of frames part of animation
       'speed'           - speed of the animation
       'animtype'        - specifies type of the animation, which can be:
                           'none' (noanim, null, 0)
                           'oscillate' (sin, cos, 1)
                           'forward' (fw, fd, 2)
                           'backward' (bk, bw, 3)
       'offscorrect'     - Intended for use with animations, weapon views.
                           The value should be set to the number of tiles
                           in the sequence.
                           Corrects the offsets for size changes during the
                           tile sequence.
                           Only works forwards! Overwrites all offsets for the
                           tiles in the sequence unless specified otherwise
                           with 'nocorrectx' & 'nocorrecty'
       'correct_pivot_x'
       'correct_pivot_y' - Sets a "pivot" point for the offset correction.
                           The pivot must be defined for all tiles in the
                           sequence. The pivot must be specified in a top-
                           -left origin coordinate system. The input data
                           for example could be the 2D projected coordinate
                           of a marker in 3D space or a model's joint's coordinates
       'nocorrectx'
       'nocorrecty'      - Prevents overwriting of the specified offset with
                           the corrected value. Must be specified per-tile
                           in the sequence.
       'dither'          - whether to dither the tile during palettization""")

    if error:
        sys.exit(1)
    
    sys.exit(0)

def has_image_extension(filename: str) -> bool:
    filename = filename.lower()
    valid_extensions = {'.png', '.bmp', '.jpg', '.jpeg', '.tiff', '.j2p', '.jpx', '.jfif',
                        '.pcx', '.ppm', '.pgm', '.pbm', '.webp', '.xbm', '.dcx', '.ico',
                        '.icns', '.imt', '.pcd', '.psd', '.tga', '.xpm', '.im', '.eps',
                        '.j2k', '.jp2', '.dib', '.dds', '.avif', '.qoi', '.fits', '.pcd'}
    return any(filename.endswith(extension) for extension in valid_extensions)

def configgetattrib_int(key: str, attrib: str) -> int:
    return int(configgetattrib_float(key, attrib))

def configgetattrib_float(key: str, attrib: str) -> float:
    if key in g_config.keys():
        if attrib in g_config[key].keys():
            if isinstance(g_config[key][attrib], str):
                s_attrib = str(g_config[key][attrib]).lower()
                if attrib == 'dither' or attrib == 'nocorrectx' or attrib == 'nocorrecty':
                    if s_attrib == "true":
                        return 1
                    else:
                        return 0
                elif attrib == 'animtype':
                    if s_attrib in ('none','no', 'noanm', 'noanim', 'noanimation', 'null', '0'):
                        return 0
                    elif s_attrib in ('oscil', 'oscillate', 'oscillates', 'sine', 'sin', 'cosine', 'cos', '1'):
                        return 1
                    elif s_attrib in ('forward', 'forwards', 'fd', 'fw', '2'):
                        return 2
                    elif s_attrib in ('backward', 'backwards', 'bw', 'bk', '3'):
                        return 3
                    else:
                        print(f"Invalid animtype keyvalue!")
                return 0.0

            return float(g_config[key][attrib])

    return 0.0

def configcheckattrib(key: str, attrib: str) -> bool:
    "Returns whether an attribute is defined"
    if key in g_config.keys():
        if attrib in g_config[key].keys():
            return True

    return False

def build_art(filep: Path):
    "Builds internal representation of final ART file"
    global g_art_tile_data, g_art_tilesizex, g_art_tilesizey, g_art_picanms, g_art_lasttile, g_offscorrect_remaining, g_offscorrect_reference_tile, g_offscorrect_mode, g_offscorrect_pivot
    weirdnumbering: bool = False
    # Number of tiles above end of artfile
    overflow: int = 0

    if not filep.exists():
        print(f"The given path {filep} doesn't exist!")
        print_usage(True)

    if not filep.is_dir():
        print(f"The target is not a directory!")
        print_usage(True)

    if len(str(filep)) != 3:
        print(f"Warning! Directory name must be 3 digits!")

    # Start of ART file is not zero, and the image naming scheme matches that
    # To me doing this seems insanely impractical... Let's hope this code works on Windows
    if filep.glob('./[0-9].*',
                  case_sensitive=False,
                  recurse_symlinks=True
                  ) and configgetattrib_int('art', 'start') > 0:
        weirdnumbering = True

    for f in sorted(filep.iterdir()):
        if has_image_extension(str(f)):
            tilenum = str(f).split(sep='.')[0]
            tilenum = tilenum.split(sep='/')[1]
            # valid file!
            if not tilenum.isdigit():
                print(tilenum)
                print("Error wrongly named file!")
                print_usage(True)
            
            dither: bool = False
            tilenum = int(tilenum)

            # Keep weird numbering to match the config
            strtilenum = str(tilenum)

            if weirdnumbering:
               tilenum -= g_art_tilesstart 

            if tilenum > g_art_numtiles-1:
                if overflow < 3:
                    print(f"Image no. {tilenum} is larger than amount of tiles in file! Ignoring!")
                overflow += 1
                continue

            with PILImage(f) as img:
                img = CorrectImageSize(img)
                g_art_tilesizex[tilenum] = img.size[0]
                g_art_tilesizey[tilenum] = img.size[1]

                dither = bool(configgetattrib_int(strtilenum, 'dither'))
                animspeed = ( configgetattrib_int(strtilenum, 'speed') << 24 ) & 0xF000000
                frames = configgetattrib_int(strtilenum, 'frames') & 0x3F
                animtype = ( configgetattrib_int(strtilenum, 'animtype') << 6 ) & 0xC0
                xofs = ( configgetattrib_int(strtilenum, 'x') << 8 ) & 0xFF00
                yofs = ( configgetattrib_int(strtilenum, 'y') << 16 ) & 0xFF0000
                g_offscorrect_pivot[0] = None
                if configcheckattrib(strtilenum, 'correct_pivot_x'):
                    g_offscorrect_pivot[0] = configgetattrib_int(strtilenum, 'correct_pivot_x')
                g_offscorrect_pivot[1] = None
                if configcheckattrib(strtilenum, 'correct_pivot_y'):
                    g_offscorrect_pivot[1] = configgetattrib_int(strtilenum, 'correct_pivot_y')

                if (configgetattrib_int(strtilenum, 'offscorrect') > 0):
                    g_offscorrect_remaining = configgetattrib_int(strtilenum, 'offscorrect') + 1
                    g_offscorrect_reference_tile = tilenum
                    g_offscorrect_mode = 0
                    g_offscorrect_mode = g_offscorrect_mode | configgetattrib_int(strtilenum, 'nocorrectx') << 0
                    g_offscorrect_mode = g_offscorrect_mode | configgetattrib_int(strtilenum, 'nocorrecty') << 1
                    g_offscorrect_pivot[2] = g_offscorrect_pivot[0]
                    g_offscorrect_pivot[3] = g_offscorrect_pivot[1]

                if g_offscorrect_remaining > 0:
                    prev_xofs = (g_art_picanms[g_offscorrect_reference_tile] & 0xFF00) >> 8
                    prev_yofs = (g_art_picanms[g_offscorrect_reference_tile] & 0xFF0000) >> 16
                    if g_offscorrect_reference_tile == tilenum:
                        prev_xofs = xofs >> 8
                        prev_yofs = yofs >> 16

                    if not g_offscorrect_mode & 1:
                        xofs = (correct_offset(old_size=g_art_tilesizex[g_offscorrect_reference_tile],
                                             new_size=g_art_tilesizex[tilenum],
                                             old_offset=prev_xofs,
                                             old_pivot=g_offscorrect_pivot[2],
                                             new_pivot=g_offscorrect_pivot[0]) << 8) & 0xFF00
                    #else:
                    #    xofs = prev_xofs << 8

                    if not g_offscorrect_mode & 2:
                        yofs = (correct_offset(old_size=g_art_tilesizey[g_offscorrect_reference_tile],
                                             new_size=g_art_tilesizey[tilenum],
                                             old_offset=prev_yofs,
                                             old_pivot=g_offscorrect_pivot[3],
                                             new_pivot=g_offscorrect_pivot[1]) << 16) & 0xFF0000
                    #else:
                    #    yofs = prev_yofs << 16

                    g_offscorrect_remaining -= 1
 
                g_art_picanms[tilenum] = ( animspeed | frames | animtype | xofs | yofs )
                g_art_tile_data[tilenum] = ImageToBytes(img, dither)

                if tilenum > g_art_lasttile:
                    g_art_lasttile = tilenum

    if overflow > 3:
        overflow -= 3
        print(f"...and {overflow} more!")

    write_art(Path(f"tiles{filep}.art"))

def write_art(filep: Path):
    "Assembles final ART file in cache, then writes to disc"
    global g_art_numtiles
    if filep.is_dir():
        print("how the hell did this happen?")
        sys.exit(1)

    g_art_numtiles = g_art_tilesend - g_art_tilesstart + 1

    write_long(ART_VERSION)
    write_long(g_art_lasttile)
    write_long(g_art_tilesstart)
    write_long(g_art_tilesend)
    for i in range(g_art_numtiles):
        write_short(g_art_tilesizex[i])
    for i in range(g_art_numtiles):
        write_short(g_art_tilesizey[i])
    for i in range(g_art_numtiles):
        write_long(g_art_picanms[i])
    write_bytearray(g_art_tile_data)

    f = open(filep, "wb")
    _ = f.write(g_export)
    f.close()

def main() -> None:
    if len(sys.argv) != 2:
        print_usage(False)

    workdir = Path(sys.argv[1])
    palfile = Path('PALETTE.DAT')

    reinit_globals(workdir)
    read_palette(palfile)
    build_art(workdir)

if __name__ == "__main__":
    main()

