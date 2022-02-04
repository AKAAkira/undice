import os
import sys
import json
import argparse
from math import ceil
from struct import unpack
# from time import sleep

try:
  from PIL import Image
except ImportError:
  print(
    "Please install Pil(low) module for image manipulation.\n"
    "(https://pypi.org/project/Pillow/)"
  )
  raise

unitypack_in_vogue = 'y'
# i.e. intention of unitypack being installed
# if not installed, terminates to give chance to install; otherwise
# given a chance to switch to 'n', which skips subsequent assetbundles

## initializers
def _init_parser():
  # copied and edited from https://github.com/HearthSim/python-fsb5/blob/master/extract.py
  description = (
    "Unscrambles diced textures found in assetbundle or MVL/JSON + image "
    "files."
  )
  parser = argparse.ArgumentParser(description=description)
  parser.add_argument(
    'fpath', nargs='*', type=str, help=(
      'File paths to be passed along to script that needs undicing'
      ' (can be drag-and-dropped).\n'
      'Each fpath should be a path to MVL, JSON, or assetbundle file; if MVL '
      'or JSON, the relevant image files must be in same folder.\n'
      'If MVL: the relevant image file is assumed to have the same name except'
      ' for extention and trailing underscore (_) (e.g. "son_ba_.mvl" looks '
      'for "son_ba.png" or "son_ba.jpg" in the same folder).\n'
      'If JSON: the image file must be named the same as it is in the JSON '
      'file.\n'
      'If assetbundle: need to use --use-unitypack switch.'
    )
  )
  parser.add_argument(
    '-o', '--output-directory', default='out/',
    help='output directory to write extracted samples into (default "out/")'
  )
  parser.add_argument(
    '--verbose', action='store_true', help='be more verbose during extraction'
  )
  parser.add_argument(
    '--use-unitypack', action='store_true', help=(
      'Use unitypack module for direct assetbundles manipulation '
      '(https://github.com/HearthSim/UnityPack) (false by default'
      ' as it has problems extracting certain images correctly)'
    )
  )

  return parser

## undicing
def get_assetbundle_items(f_obj):
  magic = f_obj.read(8); f_obj.seek(0)
  if magic != b'UnityFS\x00':
    raise Exception(
      f'Magic mismatch: {magic}; {f_obj.name} is not assetbundle!'
    )
  try:
    import unitypack
    assets = unitypack.load(f_obj).assets
  except ImportError:
    print(
      "Unitypack module could not be imported!\n"
      "You may wish to install the unitypack module for easier use, if the\n"
      "target files are compatible (https://github.com/HearthSim/UnityPack)"
      "\nElse you first need to export the dicing info MonoBehaviour object as"
      "\njson and the associated Texture2D object as image with external"
      "\nprogram like AssetStudio (https://github.com/Perfare/AssetStudio)"
    )
    unitypack_in_vogue = input('Exit and install before proceeding? [y/N]: ')
    if unitypack_in_vogue and unitypack_in_vogue[0].lower() == 'y':
      sys.exit(1)
    else:
      print('Skipping', f_obj.name + '...')
      return []
  except: # LZ4 compression error
    print('Asset loading failed, may be invalid version:')
    f_obj.seek(12)
    print(f_obj.name, f_obj.read(6), f_obj.read(14))
    print('Retry after extracting JSON and images with external application')
    print('like AssetStudio (https://github.com/Perfare/AssetStudio)')
    print('Skipping', f_obj.name + '...')
    return []
  # put below except block just in case assertion fail
  assert len(assets) == 1
  return assets[0].objects.items()

def get_dicentex_from_assetbundle(f_obj):
  textures = dict(); dicings = list()
  items = get_assetbundle_items(f_obj)
  for dictitem in items:
    if dictitem[1].type == 'Texture2D':
      # problems sometimes pop up here; if image read successful, they seem to
      # be upside-down while others like DXT5Crunched format are unsuccessful
      texture = dictitem[1].read()
      textures[texture.name] = texture.image.transpose(Image.FLIP_TOP_BOTTOM)
    elif dictitem[1].type == 'DicingTextures':
      dicings.append(dictitem[1].read())
  return dicings, textures

def get_jpg_or_png(dirname, basename):
  if os.path.isfile(os.path.join(dirname, basename + '.png')):
    ext = '.png'
  elif os.path.isfile(os.path.join(dirname, basename + '.jpg')):
    ext = '.jpg'
  else:
    raise FileNotFoundError(
      f'Cannot find corresponding {basename} image in {dirname}!'
    )
  return os.path.join(dirname, basename + ext)

def produce_undiced(
  infile_path, outfold='out/', verbose=False, use_unitypack=False
):
  names = list(); ims = list()
  with open(infile_path, 'rb') as f:
    if verbose:
      print('Undicing:', infile_path)
    magic = f.read(8); f.seek(0)
    if magic == b'UnityFS\x00':
      if unitypack_in_vogue == 'y' and use_unitypack:
        dicings, textures = get_dicentex_from_assetbundle(f)
        for dicing in dicings:
          name, im = undice_json(dicing, textures)
          names.extend(name); ims.extend(im)
    elif magic[:4] == b'MVL1':
      basename = os.path.splitext(os.path.basename(infile_path))[0]
      if basename[-1] == '_':
        basename = basename[:-1]
      img_path = get_jpg_or_png(os.path.dirname(infile_path), basename)
      names, ims = undice_mvl(Image.open(img_path), f)
      outfold = os.path.join(outfold, basename)
    elif magic[0] == 123: # i.e. starts with '{'
      dicing = json.load(f)
      names, ims = undice_json(dicing, os.path.dirname(infile_path))
    elif verbose:
      print(infile_path, 'not valid MVL/JSON/assetbundle!')
    assert len(set(names)) == len(ims)
    for name, im in zip(names, ims):
      os.makedirs(os.path.dirname(os.path.join(outfold, name)), exist_ok=True)
      if os.path.isfile(os.path.join(outfold, name + '.png')):
        n = 1
        while os.path.isfile(os.path.join(outfold, name + f' ({n}).png')):
          n += 1
        final_name = os.path.join(outfold, name + f' ({n}).png')
      else:
        final_name = os.path.join(outfold, name + '.png')
      im.save(final_name, optimize=True)
      if verbose:
        print(final_name, 'saved!')

def undice_json(dicing, textures):
  names = list(); ims = list()
  assert dicing['m_Enabled'] == 1
  cellSize = dicing['cellSize']; padding = dicing['padding']
  for textureData in dicing['textureDataList']:
    texturename = textureData['atlasName']
    if type(textures) == str:
      img_path = get_jpg_or_png(textures, texturename)
      baseTexture = Image.open(img_path)
    elif type(textures) == dict:
      baseTexture = textures[texturename]
    else:
      raise TypeError('arg "textures" must be str of folder or dict of PILimg')
    name, im = undice_texture_data(baseTexture, textureData, cellSize, padding)
    names.append(name); ims.append(im)
  return names, ims

def undice_texture_data(PILImage, textureData, cellSize=64, padding=3):
  assert PILImage.size[0] % cellSize == 0 and PILImage.size[1] % cellSize == 0
  pasteSize = cellSize - 2*padding
  newBlocksAcross = ceil(textureData['width'] / pasteSize)
  newBlocksDown = ceil(textureData['height'] / pasteSize)
  assert newBlocksAcross * newBlocksDown == len(textureData['cellIndexList'])
  baseBlocksAcross = PILImage.size[0] // cellSize
  newTexture = Image.new(
    'RGBA', (textureData['width'], textureData['height'])
  )
  for n, cellNum in enumerate(textureData['cellIndexList']):
    x = (cellNum % baseBlocksAcross) * cellSize + padding
    y = PILImage.size[1] - (cellNum // baseBlocksAcross + 1)*cellSize + padding
    block = PILImage.crop((x, y, x+pasteSize, y+pasteSize))
    x2 = (n % newBlocksAcross) * pasteSize
    y2 = textureData['height'] - (n // newBlocksAcross + 1) * pasteSize
    newTexture.paste(block, (x2, y2))
  return textureData['name'], newTexture

def _assert_makes_rect(a, b, c, d, basew, baseh):
  assert (
    a[0] == c[0] and a[3] == c[3] and b[0] == d[0] and b[3] == d[3] and
    a[1] == b[1] and a[4] == b[4] and c[1] == d[1] and c[4] == d[4]
  ), 'Coordinates don\'t make rect:\n' + "\n".join(currbank[a:d])
  assert (
    round(b[0] - a[0]) == round(b[3] * basew - a[3] * basew)
  ) and (
    round(c[1] - a[1]) == round(c[4] * baseh - a[4] * baseh)
  ), 'Coordinates don\'t make same rect:\n' + "\n".join(currbank[a:d+1])

def process_mvl_data(mvl_fobj):
  magic = mvl_fobj.read(4); mvl_fname = mvl_fobj.name
  assert magic == b'MVL1', f'{mvl_fname} incorrect magic: {magic}'
  entrycount = unpack('<i', mvl_fobj.read(4))[0]
  assert mvl_fobj.read(24) == b'\x00\x10' + 22 * b'\x00', \
    f'{mvl_fname} begin 1 part inconsistent!'
  assert mvl_fobj.read(10) == b'XFYF0FUFVF', \
    f'{mvl_fname} XFYF part inconsistent!'
  assert mvl_fobj.read(54) == 54 * b'\x00', \
    f'{mvl_fname} begin part 3 inconsistent!'
  entries = []; banks = dict()
  for x in range(entrycount):
    # '<' in the unpack arg is for little-endian; unknown if game source file
    # will change endianness if the machine's endianness changes
    # (only worked with Memories Off -Innocent Fille- assets)
    entry = dict()
    entry['width'], entry['height'] = unpack('<2i', mvl_fobj.read(8))
    unk1 = mvl_fobj.read(8)
    assert unk1 == b'\x04\x01\x00\x01\x00\x00\x00\x00', \
      f'{mvl_fname} entry {x} unk1 inconsistent: {unk1}'
    # bank entry count, bank start address
    bank = unpack('<2i', mvl_fobj.read(8)) # count + address
    entry['bank_address'] = bank[1]
    entry['entrylen'], entry['address'] = unpack('<2i', mvl_fobj.read(8))
    entry['name'] = mvl_fobj.read(32).strip(b'\x00').decode()
    assert entry['entrylen'] % 6 == 0, \
      f'Image {entry["name"]} entrylen not divisible by six!'
    if not bank[1] in banks:
      banks[bank[1]] = bank[0]
    else:
      assert banks[bank[1]] == bank[0], \
        f'Image {entry["name"]} has bank address that starts same but has ' \
        f'different entry count! Expected len & add: {bank}, actual len: ' \
        f'{banks[bank[1]]}'
    entries.append(entry)
  for _ in range(len(banks)):
    bankaddress = mvl_fobj.tell()
    assert bankaddress in banks, f'{mvl_fname} position {bankaddress} ' \
      f'slipped from possible bank start address(es) {banks.keys()}'
    bankcount = banks[bankaddress]
    banks[bankaddress] = list()
    for y in range(bankcount):
      # for each coordinates: 1st and 2nd are x and y for paste, 3rd is 0, and
      # 4th and 5th are %x and %y for cut
      corresp_coor = unpack('<5f', mvl_fobj.read(20))
      assert corresp_coor[2] == 0, \
        f'{mvl_fname} bank had 3rd item of coor entry not 0: {corresp_coor}' \
        f' (at {mvl_fobj.tell()})'
      banks[bankaddress].append(corresp_coor)
  for entry in entries:
    currbank = banks[entry['bank_address']]
    assert entry['address'] == mvl_fobj.tell(), \
      f'Address mismatch: currently at {mvl_fobj.tell()}, expected to be' \
      f' at {entry["address"]}! (Entry: {entry["name"]})'
    entry['coors'] = list()
    for x in range(entry['entrylen'] // 6):
      a, b, c = unpack('<3h', mvl_fobj.read(6))
      assert c - b == 1 and b - a == 1 and \
        b == unpack('<h', mvl_fobj.read(2))[0], \
        f"Image {entry['name']} {x}th set of 6 isn't 012132 pattern!"
      d = unpack('<h', mvl_fobj.read(2))[0]
      assert d - c == 1 and c == unpack('<h', mvl_fobj.read(2))[0], \
        f"Image {entry['name']} {x}th set of 6 isn't 012132 pattern!"
      # print(len(currbank), a, b, c, d)
      a = currbank[a]; b = currbank[b]; c = currbank[c]; d = currbank[d]
      entry['coors'].append((a, b, c, d))
  return entries #, banks

def undice_mvl(PILimage, mvl_fobj):
  names = list(); ims = list()
  entries = process_mvl_data(mvl_fobj)
  for entry in entries:
    name, im = undice_mvl_data(PILimage, entry)
    names.append(name); ims.append(im)
  return names, ims

def undice_mvl_data(PILimage, entry):
  basew, baseh = PILimage.size
  im = Image.new('RGBA', (entry['width'], entry['height']))
  adjust = entry['width'] // 2 # i.e. center is middle top
  for coor in entry['coors']:
    a, b, c, d = coor
    _assert_makes_rect(a, b, c, d, basew, baseh)
    im.paste(
      PILimage.crop((
        round(a[3] * basew), round(a[4] * baseh),
        round(d[3] * basew), round(d[4] * baseh)
      )),
      (round(a[0]) + adjust, round(a[1]))
    )
  return entry['name'], im

if __name__ == '__main__':
  # if len(sys.argv) > 1:
  args = _init_parser().parse_args(sys.argv[1:])
  for discrete_path in args.fpath:
    if os.path.isfile(discrete_path):
      produce_undiced(discrete_path, args.output_directory, args.verbose)
    elif os.path.isdir(discrete_path):
      for dpath, dnames, fnames in os.walk(discrete_path):
        for fname in fnames:
          produce_undiced(
            os.path.join(dpath, fname),
            args.output_directory,
            args.verbose
          )
    else:
      print(discrete_path, 'does not exist!')
  # else:
    # arg = input('Input path to .mvl file: ')
    # basename = os.path.splitext(os.path.basename(arg))[0]
    # if basename[0][-1] == '_':
      # basename[0] = basename[0][:-1]
    # todo[basename[0]]['mvl'] = arg
