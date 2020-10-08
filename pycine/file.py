import datetime
import os
import struct
from contextlib import contextmanager
import ctypes as ct
import numpy as np

from pycine import cine


def read_header(cine_file):
    with open(cine_file, "rb") as f:
        header = {
            "cinefileheader": cine.CINEFILEHEADER(),
            "bitmapinfoheader": cine.BITMAPINFOHEADER(),
            "setup": cine.SETUP(),
        }
        f.readinto(header["cinefileheader"])
        f.readinto(header["bitmapinfoheader"])
        f.readinto(header["setup"])

        # header_length = ctypes.sizeof(header['cinefileheader'])
        # bitmapinfo_length = ctypes.sizeof(header['bitmapinfoheader'])

        f.seek(header["cinefileheader"].OffImageOffsets)
        header["pImage"] = struct.unpack(
            "{}q".format(header["cinefileheader"].ImageCount), f.read(header["cinefileheader"].ImageCount * 8)
        )
        
        header = taggedBlock(cine_file, header)    #add tagged block to header dict
        
    return header


def read_chd_header(chd_file):
    """
    read the .chd header file created when Vision Research software saves the images in a file format other than .cine
    """

    with open(chd_file, "rb") as f:
        header = {
            "cinefileheader": cine.CINEFILEHEADER(),
            "bitmapinfoheader": cine.BITMAPINFOHEADER(),
            "setup": cine.SETUP(),
        }
        f.readinto(header["cinefileheader"])
        f.readinto(header["bitmapinfoheader"])
        f.readinto(header["setup"])

    return header

def taggedBlock(cine_file, header):
    #with help of https://raw.githubusercontent.com/soft-matter/pims/master/pims/cine.py
    with open(cine_file, "rb") as f:
        header_length = ct.sizeof(header['cinefileheader'])
        bitmapinfo_length = ct.sizeof(header['bitmapinfoheader'])
        if not header['cinefileheader'].OffSetup + header['setup'].Length < header["cinefileheader"].OffImageOffsets:
            print('no tagged block available')
            return header
        
        position = header_length + bitmapinfo_length + header['setup'].Length
        f.seek(position)
        
        while position < header["cinefileheader"].OffImageOffsets:
            
            blocksize = np.frombuffer(f.read(4), dtype='uint32')[0]
            tagtype = np.frombuffer(f.read(2), dtype='uint16')[0]

            f.seek(2, 1)    #reserved bits
            
            #tagtype 1000 and 1001 are outdated
            
            if tagtype == 1002:    #Time only block
                #Every element of the array is a TIME64 structure (32.32). 
                #The time is stored only for the images saved in this file; the count of time items is ImageCount (even if you recorded in camera a larger range – TotalImageCount).
                
                temp = np.frombuffer(f.read(blocksize-8), dtype='uint32').reshape(header["cinefileheader"].ImageCount, -1)
                
                header['timestamp'] = temp[:,1] + (((2**32-1) & temp[:,0]) / (2**32))
                
            elif tagtype == 1003:    #Exposure only block
                #This block is needed because the exposure length can be different for different imges (for example when using Autoexposure). 
                #Every element of the array is a uint32_t that represents a fixed point 0.32 number. 
                #You have to divide it by 2**32 to get the real exposure in seconds. 
                #The exposures are stored only for the images saved in this file; the count of exposure items is ImageCount.

                header['exposuretime'] = np.frombuffer(f.read(blocksize-8), dtype='uint32')*2**-32
                
            elif tagtype == 1004:    #Range data block
                #This block will contain information about camera orientation and distance to the subject.
                #There are SETUP.RangeSize bytes per image and their meaning is described by SETUP.RangeCode and is customer dependent. 
                #The standard cine viewer should skip this block.
                # print('tagged block type {0} not implemented'.format(tagtype))
                f.seek(blocksize-8, 1)
            elif tagtype == 1005:    #BinSig block
                #It stores binary signals acquired with the SAM3 module, multichannel and multisample per image. 
                #The signals are stored 8 samples per byte; only for the images stored in the file.
                #Information about the number of channels and samples per image are stored in the SETUP structure.
                # print('tagged block type {0} not implemented'.format(tagtype))
                f.seek(blocksize-8, 1)
            elif tagtype == 1006:    #AnaSig block
                #It stores analog signals acquired with the SAM3 module, multichannel and multisample per image. 
                #The signals are stored at 16 bit per sample; only for the images stored in the file.
                #Information about the number of channels and samples per image are stored in the SETUP structure
                # print('tagged block type {0} not implemented'.format(tagtype))
                f.seek(blocksize-8, 1)
            elif tagtype ==1007:    #TimeCode block
                #It stores the time code for every image based on the trigger time code and thetime code frequency, both read from the camera.                
                # print('tagged block type {0} not implemented'.format(tagtype))
                f.seek(blocksize-8, 1)
            position += blocksize
    return header

def write_header(cine_file, header, backup=True):
    if backup:
        backup_header(cine_file)

    with open_ignoring_read_only(cine_file, "rb+") as f:
        f.write(header["cinefileheader"])
        f.write(header["bitmapinfoheader"])
        f.write(header["setup"])


def backup_header(cine_file):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    header = read_header(cine_file)
    with open(cine_file + f"_metadata_backup_{now}", "xb") as f:
        f.write(header["cinefileheader"])
        f.write(header["bitmapinfoheader"])
        f.write(header["setup"])


@contextmanager
def open_ignoring_read_only(file_path, mode):
    mode_before = os.stat(file_path).st_mode
    os.chmod(file_path, 0o600)

    with open(file_path, mode) as f:
        yield f

    os.chmod(file_path, mode_before)
