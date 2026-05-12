# ffmpeg_utils.py
import os

def ffmpeg_convert(infile):
    outfile = infile + ".tmp.mp3"
    ret = os.system(f'ffmpeg -i "{infile}" "{outfile}"')
    if ret == 0:
        os.remove(infile)
        os.rename(outfile, infile)
        return True
    return False