import glob
import numpy as np
from skimage.io import imread, imsave
import os
from skimage.transform import rescale

### Padding
m,n = 300,300
top_min = 75
bottom_max = 225

def flip_c(original_filename, new_filename, m, n):
    img = imread(original_filename)[:,:,0]
    pad_t = (m-img.shape[0])//2
    pad_b = m - pad_t - img.shape[0]
    pad_l = (n-img.shape[1])//2
    pad_r = n - pad_l - img.shape[1]
    img = np.pad(img, [(pad_t,pad_b),(pad_l,pad_r)],mode='constant')

    # Take the mean index of the centerline of image for orientation
    if np.mean(np.argwhere(img[m//2]>=1)) > n//2:
        # Flip to C is correctly oriented
        img = np.fliplr(img)
    imsave(new_filename, img)

def resize_c(original_filename, new_filename, top_min, bottom_max):
    img = imread(original_filename)
    filament = np.argwhere(img[:,n//2]).flatten()
    top,bottom = np.split(filament,np.argwhere(filament>np.mean(filament))[0])
    top_axis = top[len(top)//2]
    bottom_axis = bottom[len(bottom)//2]
    top_move = top_min - np.array(top_axis)
    bottom_move = bottom_max - np.array(bottom_axis)
    centerline = (top_axis+bottom_axis)//2
    new_img = np.zeros((m,n)).astype("uint8")
    top_height = centerline + top_move
    bottom_height = (m-centerline) - bottom_move
    new_img[:top_height,:] +=  img[np.abs(top_move):centerline,:]
    new_img[-bottom_height:,:] +=  img[centerline:centerline+bottom_height,:]
    new_img[top_height:-bottom_height,:] += img[centerline,:]
    new_img = rescale(new_img, (224/300), anti_aliasing=True)
    new_img = np.uint8(new_img*255)
    imsave(new_filename, new_img)
