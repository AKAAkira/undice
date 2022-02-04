import os
import sys
import argparse
import numpy as np
from PIL import Image
from itertools import chain as iterchain, product as iterprod

def _init_parser():
  # copied and edited from https://github.com/HearthSim/python-fsb5/blob/master/extract.py
  description = (
    "Some processing of images that may be needed after undicing"
    " for more natural viewing."
  )
  parser = argparse.ArgumentParser(description=description)
  parser.add_argument('fpath', default='out/', type=str, help=(
    'Path to folders that contain images needing processing '
    '(can be drag-and-dropped)\n'
  ))
  parser.add_argument(
    '-o', '--output-directory', type=str, default='processed/',
    help='output directory to write results into (default "processed/")'
  )
  parser.add_argument(
    '--verbose', action='store_true', help='be more verbose during extraction'
  )
  parser.add_argument('-t', '--process-type', type=str, help=processing_text)
  parser.add_argument(
    '-w', '--overwrite', action='store_true', 
    help="If output file already exists, don't skip and overwrite it."
  )

  return parser

processing_text = """
1: Alpha composite + trim (e.g. for MO -Innocent Fille)
   Layers base images together with their respective part images to make
   variant image set. Files must be PNG and be named in a pattern buildling
   off from previous base images. E.g. AA.png will be treated as base for
   AAA.png and AAB.png, while AAAA.png and AAAB.png will treat the former
   as base but not the latter.
a: Applies edge fuzz transparency (better trim, but may over-erase
   subtle art details starting from the edges)
b: Solid colour trim (rids edges with any uniform colour, not just
   transparent pixels; not for BG art, especially solid colour)
Any combination of valid number/letters works.
""".strip()

## image editing
def apply_edge_spread_transparency(im):
  transparents = set(); ignores = set()
  x, y = im.size
  
  def checktransparent(coor, store):
    if not coor in ignores and not coor in store:
      pixel = im.getpixel(coor)
      if 0 < pixel[3] < 64:
        return 1
      elif 64 <= pixel[3]:
        return 2
      else:
        ignores.add(coor)
    return 0
  
  for coor in iterchain(
    iterprod((0, x-1), range(y)), iterprod(range(x), (0, y-1))
  ):
    if coor in ignores:
      continue
    pix = im.getpixel(coor)
    if 0 < pix[3] < 64:
      # print('Found non-transparent pixel at', coor)
      solid = False
      store = {coor}; startpoints = [coor]
      while startpoints:
        workingpoints = set()
        for acoor in startpoints:
          for bcoor in iterprod(
            range(max(acoor[0] - 1, 0), min(acoor[0] + 2, x)),
            range(max(acoor[1] - 1, 0), min(acoor[1] + 2, y))
          ):
            res = checktransparent(bcoor, store)
            if res == 2:
              solid = True
              break
            elif res == 1:
              workingpoints.add(bcoor)
          if solid:
            break
        store.update(workingpoints)
        # print('Workingpoints: ', str(workingpoints)); # sleep(2)
        if solid:
          break
        startpoints = workingpoints
      if not solid:
        transparents.update(store)
        # print('Updated set to transparents')
      # not conditioning the below under only if solid, just in case
      # something unexpected happens
      ignores.update(store)
    elif 0 == pix[3]:
      ignores.add(coor)
  
  for coor in transparents:
    im.putpixel(coor, (0,0,0,0))

def alpha_composite_fnames_list(fnames_list, bank=dict()):
  key = fnames_list[0]
  if not key in bank:
    im = Image.open(key)
    bank[key] = im
  else:
    im = bank[key]
  for key in fnames_list[1:]:
    if not key in bank:
      subim = Image.open(key)
      bank[key] = subim
    else:
      subim = bank[key]
    im = Image.alpha_composite(im, subim)
  return im, bank

# first try, but thought a-composition could be saved till after checking file
# exists to save processing power, assuming it's applicable here
# note to self: check later if it's opening PIL Images or retaining PIL images
# that are more expensive, and whether either is notably expensive at all
# def alpha_composite_fnames_tree(dirpath, treedict):
  # composition_list = list()
  # for key in treedict:
    # if key == 'level_len?':
      # continue
    # im = Image.open(os.path.join(dirpath, key+'.png'))
    # if not treedict[key]:
      # composition_list.append((im.filename, im))
    # else:
      # composition_list.append(
        # (name, Image.alpha_composite(im, subim)) for name,
        # subim in alpha_composite_fnames_tree(dirpath, treedict[key])
      # )
  # return composition_list

def collate_fnames_tree(dirpath, treedict):
  composition_list = list()
  for key in treedict:
    if key == 'level_len?':
      continue
    if not treedict[key]:
      composition_list.append([os.path.join(dirpath, key)+'.png'])
    else:
      for fnames_list in collate_fnames_tree(dirpath, treedict[key]):
        fnames_list.append(os.path.join(dirpath, key)+'.png')
        composition_list.append(fnames_list)
  return composition_list

def get_fnames_tree(fnames):
  subtree = dict()
  for fname in fnames:
    fname = os.path.splitext(fname)[0]
    current_reference = subtree
    while (
      current_reference and
      fname[:current_reference['level_len?']] in current_reference
    ):
      current_reference = current_reference[
        fname[:current_reference['level_len?']]
      ]
    if not current_reference:
      current_reference['level_len?'] = len(fname)
      current_reference[fname] = dict()
    else:
      assert not fname[:current_reference['level_len?']] in current_reference,\
        f'somehow first few of {fname} still in {current_reference.keys()}'
      assert current_reference['level_len?'] == len(fname), \
        f'{fname} len not {current_reference["level_len?"]}'
      current_reference[fname] = dict()
  return subtree

def gettrimbox(im): # about fifteen seconds for one use of this one
  bounds = tuple(); a, b, c, d = [0, 0] + list(im.size)
  while bounds != (a, b, c, d):
    bounds = (a, b, c, d)
    while len(set(
      im.getpixel((x, b)) for x in range(c)
    )) == 1:
      b += 1
    while len(set(
      im.getpixel((x, d-1)) for x in range(c)
    )) == 1:
      d -= 1
    while len(set(
      im.getpixel((a, y)) for y in range(d)
    )) == 1:
      a += 1
    while len(set(
      im.getpixel((c-1, y)) for y in range(d)
    )) == 1:
      c -= 1
  return bounds

# from https://stackoverflow.com/questions/59669715/fastest-way-to-find-the-rgb-pixel-color-count-of-image
def gettrimbox2(im): # about one second for one use of this one
  bounds = tuple(); a, b, c, d = [0, 0] + list(im.size)
  while bounds != (a, b, c, d):
    bounds = (a, b, c, d)
    while b + 1 < d and len(np.unique(np.dot(
      np.array(im.crop((a, b, c, b+1))).astype(np.uint32),[1,256,256**2,256**3]
    ))) == 1:
      b += 1
    while b < d - 1 and len(np.unique(np.dot(
      np.array(im.crop((a, d-1, c, d))).astype(np.uint32),[1,256,256**2,256**3]
    ))) == 1:
      d -= 1
    while a + 1 < c and len(np.unique(np.dot(
      np.array(im.crop((a, b, a+1, d))).astype(np.uint32),[1,256,256**2,256**3]
    ))) == 1:
      a += 1
    while a < c - 1 and len(np.unique(np.dot(
      np.array(im.crop((c-1, b, c, d))).astype(np.uint32),[1,256,256**2,256**3]
    ))) == 1:
      c -= 1
  return bounds

if __name__ == '__main__':
  args = _init_parser().parse_args(sys.argv[1:])
  if not args.process_type:
    print('No process type inputted! Select among the following:')
    print(processing_text)
    args.process_type = input('Enter here (empty field will exit program): ')
  if args.process_type:
    if '1' in args.process_type:
      for dirpath, dirnames, fnames in os.walk(args.fpath):
        if fnames:
          treedict = get_fnames_tree(fnames); bank = dict()
          for fnames_list in collate_fnames_tree(dirpath, treedict):
            outpath = args.output_directory + fnames_list[0][len(args.fpath):]
            if not args.overwrite and os.path.isfile(outpath):
              print('Skipped', outpath)
              continue
            os.makedirs(os.path.dirname(outpath), exist_ok=True)
            im, bank = alpha_composite_fnames_list(fnames_list, bank)
            if 'b' in args.process_type:
              getboundary = gettrimbox2
            else:
              getboundary = lambda x: x.getbbox()
            im = im.crop(getboundary(im))
            if 'a' in args.process_type:
              apply_edge_spread_transparency(im)
              while getboundary(im) != (0, 0) + im.size:
                im = im.crop(getboundaary(im))
                apply_edge_spread_transparency(im)
            if args.verbose:
              print('Saving', outpath)
            im.save(outpath, optimize=True)

    # confirm = input('\nRemove recent outputs to out/ folder? y/n> ')
    # if confirm and confirm[0].lower() == 'y':
      # from shutil import rmtree
      # rmtree(outdir)
  # else:
    # print('No processing done.')
  # input('Finished! Press ENTER to exit program...')
