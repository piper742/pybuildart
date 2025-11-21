import struct, os, sys
from PIL import Image, ImageFilter, ImageChops
from io import BufferedReader, BufferedWriter
from pathlib import Path
from array import array

ART_VERSION = 1
MAX_TILE_SIZE = 512
C_SHORT = "<h"
C_SHORT_LEN = struct.calcsize(C_SHORT)
C_SHORT_UNPACK = struct.Struct(C_SHORT).unpack_from
C_LONG = "<l"
C_LONG_LEN = struct.calcsize(C_LONG)
C_LONG_UNPACK = struct.Struct(C_LONG).unpack_from
C_UCHAR = "<B"
C_UCHAR_LEN = struct.calcsize(C_UCHAR)
C_UCHAR_UNPACK = struct.Struct(C_UCHAR).unpack_from

g_palette: Image.Image = Image.Image()

#g_art_header: bytes = bytes()
# Contains the tilesend-tilesstart+1
g_art_numtiles: int = 0
# Contains real amount of tiles
g_art_lasttile: int = 0
g_art_tilesstart: int = 0
g_art_tilesend: int = 255
#g_art_numtiles: array[int] = array('L', [0] * 256)
g_art_tilesizex: array[int] = array('H', [0] * 256)
g_art_tilesizey: array[int] = array('H', [0] * 256)
g_art_picanms: array[int] = array('l', [0] * 256)
g_art_tile_data: list[bytes] = [bytes()] * 256
g_export: bytearray = bytearray(0) #bytearray(C_LONG_LEN * 4 + C_SHORT_LEN * 2 * 256 + C_LONG_LEN * 256)
g_export_offset: int = 0

def read_palette(filep: Path):
    global g_palette
    tmp: list[int] = []
    with open(filep, "rb") as f:
        for i in range(241):
            r = read_unsigned_char(f) * 4
            g = read_unsigned_char(f) * 4
            b = read_unsigned_char(f) * 4
            tmp.extend([r, g, b])

    g_palette = Image.new('P', (16, 15))
    g_palette.putpalette(tmp)

 
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
    #struct.pack_into(C_SHORT, g_export, g_export_offset, data)
    g_export.extend(struct.pack(C_SHORT, data))
    g_export_offset += C_SHORT_LEN

def write_long(data: int) -> None:
    global g_export, g_export_offset
    #struct.pack_into(C_LONG, g_export, g_export_offset, data)
    g_export.extend(struct.pack(C_LONG, data))
    g_export_offset += C_LONG_LEN

def write_unsigned_char(data: int) -> None:
    global g_export, g_export_offset
    #struct.pack_into(C_UCHAR, g_export, g_export_offset, data)
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
    Converts Image to tile, has no picanms set. Operation is destructive to the image input
    """
    # Deal with transparency
    mask = HandleTransparency(image)
    fullytransp = Image.new('L', image.size, color=(0xff))

    if image.mode != "RGB":
        image = image.convert("RGB")

    #result = image.convert('P', dither, palette.get_lookup())
    result = image.quantize(colors= 256, method=Image.Quantize.MEDIANCUT, palette=g_palette, dither=Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE)
    result = Image.composite(fullytransp, result, mask)

    #result = image.convert('P', dither=None, palette=g_palette, colors = 256)
    result = result.transpose(Image.Transpose.TRANSPOSE)

    return result.tobytes()

#def ImageToPalImage(image: Image.Image, dither: bool) -> Image.Image:
#    return image.quantize(colors = 256,
#                   method = None,
#                   kmeans = 0,
#                   palette = g_palette)

def CorrectImageSize(image: Image.Image) -> Image.Image:
    image2 = image
    if image.size[0] > MAX_TILE_SIZE or image.size[1] > MAX_TILE_SIZE:
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
    #width, height = image.size
    image2 = image.convert('RGBA')
    alpha = image2.split()[-1]
    alpha = ImageChops.invert(alpha)
    #print("HandleTransparency called!")
    #alpha.show()
    return alpha



def print_usage(error: bool) -> None:
    print("TODO: Add usage here!!!")

    if error:
        sys.exit(127)
    
    sys.exit(0)

def has_image_extension(filename: str) -> bool:
    filename = filename.lower()
    if filename.endswith('.png') or filename.endswith('.bmp') or filename.endswith('.jpg') or filename.endswith('.tiff') or filename.endswith('.jpeg'):
        return True

    return False

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

    for f in filep.iterdir():
        if has_image_extension(str(f)):
            tilenum = str(f).split(sep='.')[0]
            tilenum = tilenum.split(sep='/')[1]
            # valid file!
            if not tilenum.isdigit():
                print(tilenum)
                print("Error wrongly named file!")
                print_usage(True)
            
            tilenum = int(tilenum)

            img = Image.open(f)
            img = CorrectImageSize(img)
            g_art_tilesizex[tilenum] = img.size[0]
            g_art_tilesizey[tilenum] = img.size[1]
            g_art_picanms[tilenum] = 0
            g_art_tile_data[tilenum] = ImageToBytes(img, False)

            if tilenum > g_art_lasttile:
                g_art_lasttile = tilenum

    build_art2(Path(f"tiles{filep}.art"))

def build_art2(filep: Path):
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
    f.write(g_export)
    f.close()

if __name__ == "__main__":
    read_palette(Path("PALETTE.DAT"))
    build_art(Path(sys.argv[1]))
