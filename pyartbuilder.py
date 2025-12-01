import struct, sys
from PIL import Image, ImageChops
from io import BufferedReader
from pathlib import Path
from array import array
import toml

# DO NOT CHANGE
ART_VERSION = 1
# I don't know what is actually the max tile size for BUILD (probably sizeof(short) ^ 2),
# but I feel like this is a sensible maximum from an aesthetic/size point of view
# TODO: Check if all of D3Ds tiles don't exceed this
MAX_TILE_SIZE = 256

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

# TOML config
# the sets aren't used anywhere, reference only
ART_CONFIG_OPTIONS: set[str] = { 'numtiles', 'starttile' }
TILE_CONFIG_OPTIONS: set[str] = { 'x', 'y', 'frames', 'animtype', 'speed', 'dither' }
g_config = dict()

# 241 color palette (excludes fullbright colors)
g_palette: Image.Image = Image.Image()

# Contains the tilesend-tilesstart+1
g_art_numtiles: int = 0
# Contains real amount of tiles
g_art_lasttile: int = 0

g_art_tilesstart: int = 0
g_art_tilesend: int = 255

g_art_tilesizex: array[int] = array('H', [0] * 256)
g_art_tilesizey: array[int] = array('H', [0] * 256)
g_art_picanms: array[int] = array('l', [0] * 256)
g_art_tile_data: list[bytes] = [bytes(0)] * 256
g_export: bytearray = bytearray(0)

# Not used anywhere, but should still be valid
g_export_offset: int = 0

def read_config(filep: Path) -> None:
    global g_config
    try:
        with open(filep, "r") as f:
            g_config = toml.load(f)
    except Exception as error:
        print(f"Couldn't find/parse config file: {filep}")
        print(error)

def read_palette(filep: Path):
    global g_palette
    tmp: list[int] = []
    try:
        with open(filep, "rb") as f:
            for i in range(241):
                r = read_unsigned_char(f) * 4
                g = read_unsigned_char(f) * 4
                b = read_unsigned_char(f) * 4
                tmp.extend([r, g, b])

        g_palette = Image.new('P', (16, 15))
        g_palette.putpalette(tmp)
    except Exception as error:
        print("Failed to read PALETTE.DAT")
        print("Error: ", error)

def read_short(file: BufferedReader) -> int:
    return C_SHORT_UNPACK(
            file.read(C_SHORT_LEN))[0]

def read_long(file: BufferedReader) -> int:
    return C_LONG_UNPACK(
            file.read(C_LONG_LEN))[0]

def read_unsigned_char(file: BufferedReader) -> int:
    return C_UCHAR_UNPACK(
            file.read(C_UCHAR_LEN))[0]

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
    if (image.size[0] * image.size[1]) > (MAX_TILE_SIZE * MAX_TILE_SIZE):
        width_ratio = MAX_TILE_SIZE / image.size[0]
        height_ratio = MAX_TILE_SIZE / image.size[1]
        
        # Use the smaller ratio to maintain aspect ratio and fit within bounds
        scale_ratio = min(width_ratio, height_ratio)
        
        new_width = int(image.size[0] * scale_ratio)
        new_height = int(image.size[1] * scale_ratio)

        if image.format == "JPEG":
            image2 = image.resize((new_width, new_height), Image.Resampling.BILINEAR)
        else:
            image2 = image.resize((new_width, new_height), Image.Resampling.NEAREST)
    return image2

def HandleTransparency(image: Image.Image) -> Image.Image:
    image2 = image.convert('RGBA')

    alpha = image2.split()[-1]
    alpha = ImageChops.invert(alpha)

    # Clamp between 255 and 0
    # This threshold works perfectly for my horribly rotoscoped foliage
    alpha = alpha.point(lambda a: 255 if a > 240 else 0)

    return alpha

def print_usage(error: bool) -> None:
    print("TODO: Add usage here!!!")

    if error:
        sys.exit(127)
    
    sys.exit(0)

def has_image_extension(filename: str) -> bool:
    filename = filename.lower()
    valid_extensions = {'.png', '.bmp', '.jpg', '.jpeg', '.tiff', '.j2p', '.jpx', '.jfif',
                        '.pcx', '.ppm', '.pgm', '.pbm', '.webp', '.xbm', '.dcx', '.ico',
                        '.icns', '.imt', '.pcd', '.psd', '.tga', '.xpm', '.im', '.eps'}
    return any(filename.endswith(extension) for extension in valid_extensions)

def configgetattrib(key: str, attrib: str) -> int:
    if key in g_config.keys():
        if attrib in g_config[key].keys():
            if isinstance(g_config[key][attrib], str):
                s_attrib = str(g_config[key][attrib]).lower()
                if attrib == 'dither':
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
                return 0
            return g_config[key][attrib]

    return 0

def build_art(filep: Path):
    global g_art_tile_data, g_art_tilesizex, g_art_tilesizey, g_art_picanms, g_art_lasttile
    if not filep.exists():
        print(f"The given path {filep} doesn't exist!")
        print_usage(True)

    if not filep.is_dir():
        print(f"The target is not a directory!")
        print_usage(True)

    if len(str(filep)) != 3:
        print(f"Warning! Directory name must be 3 digits!")

    read_config(filep / 'config.toml')

    for f in filep.iterdir():
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

            img = Image.open(f)
            img = CorrectImageSize(img)
            g_art_tilesizex[tilenum] = img.size[0]
            g_art_tilesizey[tilenum] = img.size[1]

            strtilenum = str(tilenum)
            dither = bool(configgetattrib(strtilenum, 'dither'))
            animspeed = ( configgetattrib(strtilenum, 'speed') << 24 ) & 0xF000000
            frames = configgetattrib(strtilenum, 'frames') & 0x3F
            animtype = ( configgetattrib(strtilenum, 'animtype') << 6 ) & 0xC0
            xofs = ( configgetattrib(strtilenum, 'x') << 8 ) & 0xFF00
            yofs = ( configgetattrib(strtilenum, 'y') << 16 ) & 0xFF0000
 
            g_art_picanms[tilenum] = ( animspeed | frames | animtype | xofs| yofs )
            g_art_tile_data[tilenum] = ImageToBytes(img, dither)

            if tilenum > g_art_lasttile:
                g_art_lasttile = tilenum

    build_art2(Path(f"tiles{filep}.art"))

def build_art2(filep: Path):
    global g_art_numtiles
    if filep.is_dir():
        print("how the hell did this happen?")
        sys.exit(127)

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

if __name__ == "__main__":
    read_palette(Path("PALETTE.DAT"))
    build_art(Path(sys.argv[1]))
