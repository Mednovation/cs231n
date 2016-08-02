#!/usr/bin/env python

#based upon the code:
#https://github.com/matthewearl/deep-anpr/blob/master/gen.py

""" 
    Generates an image which contrain an affine transformed 
    Licence Plate.
"""

from __future__ import print_function

import math
import os
import random
import sys

import cv2
import numpy as np

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import utils.common as common

OUTPUT_SHAPE = (64,128)
FONT_HEIGHT = 32
FONT_PATH   = "UKNumberPlate.ttf"

CHARS = common.CHARS + " "

ld_code = { 'L' : common.LETTERS, 'D' : common.DIGITS, 'S' : ' ',
            'X' : 'd',
            'Q' : 'q',
            'W' : 'w'}

def make_character_images(output_height):
    font_size = output_height * 4
    font   = ImageFont.truetype(FONT_PATH, font_size)
    height = max(font.getsize(c)[1] for c in CHARS)
    #require the height to always be the same

    for c in CHARS:
        width = font.getsize(c)[0]
        im = Image.new("RGBA", (width, height), (0, 0, 0))

        draw = ImageDraw.Draw(im)
        draw.text((0, 0), c, (255, 255, 255), font=font)
        scale = float(output_height) / height
        im = im.resize((int(width * scale), output_height), Image.ANTIALIAS)
        yield c, np.array(im)[:, :, 0].astype(np.float32) / 255.

    #double space
    wide_space = "d"
    width = font.getsize(' ')[0]
    im = Image.new("RGBA", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.text((0, 0), c, (255, 255, 255), font=font)
    scale = float(output_height) / height
    im = im.resize((int(width * scale * 2.0), output_height), Image.ANTIALIAS)
    yield wide_space, np.array(im)[:, :, 0].astype(np.float32) / 255.

    #wide space
    wide_space = "w"
    width = font.getsize(' ')[0]
    im = Image.new("RGBA", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.text((0, 0), c, (255, 255, 255), font=font)
    scale = float(output_height) / height
    im = im.resize((int(width * scale * 1.5), output_height), Image.ANTIALIAS)
    yield wide_space, np.array(im)[:, :, 0].astype(np.float32) / 255.

    #quad space
    wide_space = "q"
    width = font.getsize(' ')[0]
    im = Image.new("RGBA", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.text((0, 0), c, (255, 255, 255), font=font)
    scale = float(output_height) / height
    im = im.resize((int(width * scale * 4.0), output_height), Image.ANTIALIAS)
    yield wide_space, np.array(im)[:, :, 0].astype(np.float32) / 255.

    #CAN add extra characters after the fact here
    #(1) for example wide space would take ' ' and widen it to have some
    #    some larger width np.zeros(size=(y,x))
    #(2) characters like '-' might also be available

def generate_code(lp_code = None):
    """
    generate_code(lp_code = None) generate a simple "RANDOM" license plate code

      takes either a string descriptor
      with the following format:
        "L", "D", "S": L corresponds to letters;
                       D corresponds to digits;
                       S corresponds to spaces;
      there is no length requirement;

      if None (or nothing is passed in):
        it defaults to "LLDDSLL"
      returns a string of characters of the correct format;
    """
    #licence descriptor
    ld = lp_code
    if lp_code is None:
        ld = "LLDDSLLL"

    #join together a comprehension
    plate = ''.join([ random.choice(ld_code[c]) for c in ld ])
    return plate


#the code below can be updated in the following manner:
# (1) add the ability to define the padding (pad_left, pad_right, pad_top, pad_bottom)
# (2) add the ability to left, right align relative to a fixed size 'plate'
#     or maximum sized plate:
#     AB33 ABAC
#     GREG
#          KING
# CENTRAL alignment should be neglected (for now)
# (3) alpha channel? (letters would have alpha = 1)
#     background could then be textured/shadowed gradient in addition to colored;
# (4) additional fonts (i.e. each plate might have a font);
# (5) additional information on the plate.
# (6) addition of filtering the plate (i.e. smoothing out the edges, blurring etc.)
#

def generate_plate(char_to_img, code = None):
    h_padding = random.uniform(0.2, 0.4) * FONT_HEIGHT
    v_padding = random.uniform(0.1, 0.3) * FONT_HEIGHT
    spacing = FONT_HEIGHT * random.uniform(-0.05, 0.05)
    radius = 1 + int(FONT_HEIGHT * 0.1 * random.random())
    if code is None:
        code = generate_code()

    text_width = np.sum([char_to_img[c].shape[1] for c in code])
    text_width += (len(code) - 1) * spacing

    out_shape = (int(FONT_HEIGHT + v_padding * 2),
                 int(text_width + h_padding * 2))

    text_mask = np.zeros(out_shape)

    x = h_padding
    y = v_padding

    for c in code:
        char_im = char_to_img[c]
        ix, iy = int(x), int(y)
        text_mask[iy:iy + char_im.shape[0], ix:ix + char_im.shape[1]] = char_im
        x += char_im.shape[1] + spacing

    #case (1): simple colors, just change the number and allow for the broadcast
    #           rules to take over
    #case (2): color can be sampled from texture of the same size and shape
    #
    #Options: create the plate later (just create masks);
    #color can be changed here -----------------------v
    plate = (np.ones(out_shape)[:,:,np.newaxis] * (1.,0.,0.) * ( 1 - text_mask)[:,:,np.newaxis] +
             np.ones(out_shape)[:,:,np.newaxis] * (0.,1.,0.) * (text_mask)[:,:,np.newaxis])
    return plate
    #this generates a plate

def euler_matrix(yaw, pitch, roll):
    """Construct an Euler Rotation Matrix from yaw, pitch and roll"""
    # z-y'-x'' (or z-y-x), intrinsic rotations are known as: yaw, pitch, roll

    # roll is a counter-clockwise rotation (alpha) about the x-axis
    cos_a, sin_a = np.cos(roll), np.sin(roll)
    roll_mat = np.array([[ 1,      0,      0],
                         [ 0,  cos_g, -sin_g],
                         [ 0,  sin_g,  cos_g]])

    #pitch is a counter-clockwise rotation (beta) about the y-axis
    cos_b, sin_b = np.cos(pitch), np.sin(pitch)
    pitch_mat = np.array([[ cos_b, 0, sin_b],
                          [     0, 1,     0],
                          [-sin_b, 0, cos_b]])

    #yaw is a counter-clockwise rotation (gamma) about the z-axis
    cos_g, sin_g = np.cos(yaw), np.sin(yaw)
    yaw_mat = np.array([[cos_a, -sin_a, 0],
                        [sin_a,  cos_a, 0],
                        [    0,      0, 1]])

    rotation_matrix = np.matmul(np.matmul(yaw_mat, pitch_mat), roll_mat)
    #rotate first about the x-axis, then y-axis, and finally about z-axis
    #note: if this fails might be due to numpy version
    #      (1) np.linalg.matmul(x,y)
    return rotation_matrix

def main():
    char_ims = dict(make_character_images(FONT_HEIGHT))
    print(char_ims.keys())
    for i in range(10):
        print(generate_code())
    print(generate_code("LLDDXLLL"))
    print(generate_code("LLDDQLLL"))
    print(generate_code("LLDDWLLL"))
    generate_plate(char_ims)
    print(euler_matrix(1.,1.,1.))
    print(np.matmul(euler_matrix(np.pi,0,0.), np.array([1.,0.,0.])))
    #
    exit(0)

if __name__ == '__main__':
    main()