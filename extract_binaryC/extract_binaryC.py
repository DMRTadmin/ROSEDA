import numpy as np
import matplotlib.pyplot as plt
import PIL as pil
from scipy import stats
import cv2 as cv
from skimage.segmentation import watershed
from skimage.measure import regionprops
from sklearn.cluster import KMeans

# Test

def extract_cs(imageFile, imageName, patternFile, color_threshold=0.5, glare_est=0.1):


    image_raw = cv.imread(imageFile)
    
    image = cv.imread(imageFile,cv.IMREAD_GRAYSCALE)          # queryImage
    image_yExt = image.shape[0]
    image_xExt = image.shape[1]
    template = cv.imread(patternFile,cv.IMREAD_GRAYSCALE) # trainImage
    temp_yExt = template.shape[0]
    temp_xExt = template.shape[1]
    
    # Deal with perspective skewing NOT CURRENTLY HANDLED
    
    # Set limits for scaling the pattern for pattern matching
    max_perc = min(image_yExt/temp_yExt, image_xExt/temp_xExt) * 100 - 1
    pixel_limit = 50
    min_perc = max(pixel_limit/temp_yExt, pixel_limit/temp_xExt) * 100 +1
    
    prev_best = 0
    for scale in np.linspace(min_perc, max_perc, num=100):
        scale_percent = scale # percent of original size
        width = int(template.shape[1] * scale_percent / 100)
        height = int(template.shape[0] * scale_percent / 100)
        dim = (width, height)
        resized = cv.resize(template, dim, interpolation = cv.INTER_AREA)
        
        result = cv.matchTemplate(image, resized, cv.TM_CCOEFF_NORMED)
        (minVal, maxVal, minLoc, maxLoc) = cv.minMaxLoc(result)
        if maxVal > prev_best:
            bestLoc = maxLoc
            prev_best = maxVal
            best_shape = resized.shape
            # print(f"{scale=} {maxVal=}")
    
    
    (startX, startY) = bestLoc
    endX = startX + best_shape[1]
    endY = startY + best_shape[0]
    # draw the bounding box on the image
    cv.rectangle(image_raw, (startX, startY), (endX, endY), (255, 0, 0), 3)
    # show the output image
    plt.imshow(image_raw), plt.show() 
    
    image = cv.imread(imageFile)
    buffer = 5
    pix2 = image[startY-buffer:endY+buffer, startX-buffer:endX+buffer]
    
    pixels = pix2.shape[0] * pix2.shape[1]
    
    # Use kmean clustering to find foreground and backgroun colors

    global pix_test, pix_mid, buffer_id
    pix_test = np.zeros((pix2.shape[0],pix2.shape[1]))
    pix_mid = np.zeros((pix2.shape[0],pix2.shape[1]))
    flat_pix2=pix2.reshape((pix2.shape[1]*pix2.shape[0],3))
    kmeans=KMeans(n_clusters=2)
    s=kmeans.fit(flat_pix2)
    centroid=kmeans.cluster_centers_
    
    # Assign each pixel to its cluster while reserving the interminant pixels
    # for pix_mid.
    
    cluster_count = [0,0]
    threshold = color_threshold
    for y in range(pix2.shape[0]):
        for x in range(pix2.shape[1]):
            sqr_sum = [0,0]
            for n in range(3):
                sqr_sum[0] += (pix2[y,x,n] - centroid[0][n])**2
                sqr_sum[1] += (pix2[y,x,n] - centroid[1][n])**2
            # print(f"{sqr_sum}")
            if sqr_sum[0] < threshold * sqr_sum[1]:
                pix_test[y,x] = 0
                cluster_count[0] += 1
            elif sqr_sum[1] < threshold * sqr_sum[0]:
                pix_test[y,x] = 1
                cluster_count[1] += 1
            else:
                pix_mid[y,x] = 1
    
    # Us the buffer id to assign which cluster is the background
    buffer_id = round(sum(pix_test[:buffer].flatten())/buffer/pix_test.shape[1])
    
    if buffer_id == 1:
        pix3 = 1 - pix_test - pix_mid
    else:
        pix3 = pix_test
                    
    plt.imshow(pix3), plt.show() 
    
    # Glare removal
    kernel = np.ones((2,2),np.uint8)
    pix3array = np.array(pix3)
    feature_pixels = 0
    for y in range(pix3.shape[0]):
        for x in range(pix3.shape[1]):
            if pix3[y,x]:
                feature_pixels += 1
    iters = 1
    cur_feature_pixels = 0
    while feature_pixels * (1.0+glare_est) > cur_feature_pixels:
        pix3a=cv.morphologyEx(pix3array, cv.MORPH_CLOSE, kernel, iterations = iters)
        pix3ra = np.rot90(pix3a, 3)
        wslabels = watershed(pix3ra, mask=(1-pix3ra))
        regprops = regionprops(wslabels)
        for i in range(wslabels.max()):
            if regprops[i].area < pixels/5:
                pix3ra[wslabels == (i+1)] = 1
        cur_feature_pixels = 0
        for y in range(pix3ra.shape[0]):
            for x in range(pix3ra.shape[1]):
                if pix3ra[y,x]:
                    cur_feature_pixels += 1
        iters += 1
        # force exit with more than 8 iterations
        if iters > 20:
            cur_feature_pixels = feature_pixels * 3
    
    plt.imshow(pix3ra), plt.show() 
    
    # Segment the Cs into evens and odds
    
    max_threshold = round(feature_pixels / pixels / 10 * pix3ra.shape[1])
    threshold = 0
    count = 0
    while count != 2:
        sum_row = []
        up = False
        count = 0
        key_points = []
        for n in range(pix3ra.shape[0]):
            sum_row = sum(pix3ra[n,:])
            if sum_row > threshold:
                if not up:
                    up = True
                    key_points.append(n)
            elif up:
                up = False
                key_points.append(n)
                count += 1
        threshold += 1
        if threshold > max_threshold:
            raise Exception("Max count reached")
    
    evens = pix3ra[key_points[0]:key_points[1]]
    odds = pix3ra[key_points[2]:key_points[3]]
    plt.imshow(evens), plt.show() 
    plt.imshow(odds), plt.show() 
    
    # Find all the evens
    max_threshold = round(feature_pixels / pixels / 2 * evens.shape[0])
    threshold = 0
    count = 0
    while count != 5:
        up = False
        count = 0
        even_points = []
        for n in range(evens.shape[1]):
            sum_row = sum(evens[:,n])
            if sum_row > threshold:
                if not up:
                    up = True
                    even_points.append(n)
            elif up:
                up = False
                even_points.append(n)
                count += 1
        threshold += 1
        print(f"{count=}")
        if threshold > max_threshold:
            raise Exception("Max count reached")
    
    even_images = []
    for n in range(5):
        even_images.append(evens[:,even_points[2*n]:even_points[2*n+1]])
    
    # Find all the odds
    max_threshold = round(feature_pixels / pixels / 2 * odds.shape[0])
    threshold = 0
    count = 0
    while count != 5:
        up = False
        count = 0
        odd_points = []
        for n in range(odds.shape[1]):
            sum_row = sum(odds[:,n])
            if sum_row > threshold:
                if not up:
                    up = True
                    odd_points.append(n)
            elif up:
                up = False
                odd_points.append(n)
                count += 1
        threshold += 1
        if threshold > max_threshold:
            raise Exception("Max count reached")
    
    odd_images = []
    for n in range(5):
        odd_images.append(odds[:,odd_points[2*n]:odd_points[2*n+1]])
    
    # Compile them all together
    all_images = []
    
    for n in range(5):
        all_images.append(np.rot90(odd_images[n]))
        all_images.append(np.rot90(even_images[n]))
    
    # Clean images
    cleaned_all_images = []
    for image in all_images:
        up = False
        down = False
        for n in range(image.shape[1]):
            sum_n = sum(image[:,n])
            if sum_n > 0:
                if not up:
                    up = True
                    start = n
            elif up and not down:
                stop = n
                down = True
        cleaned_image = image[:,start:stop]
        cleaned_all_images.append(cleaned_image)
            
    
    # Save files
    file_list = []
    for i, cm in enumerate(cleaned_all_images):
        imName = f"{imageName}_C{i+1}.png"
        # cv.imwrite(imName, cm*255)
        plt.imsave(imName, cm*255, cmap=plt.cm.gray, vmin=0, vmax=255)
        file_list.append(imName)
    return file_list


if __name__ == '__main__':
    pattern_file_name = r"/jhardin-repos-1sud/local_extract_binaryC/pattern.png"
    # image_file_name = r"/jhardin-repos-1sud/local_extract_binaryC/rot_AFRL.png"
    # image_file_name = r"/jhardin-repos-1sud/local_extract_binaryC/PXL_20211005_204718781.jpg"
    # image_file_name = r"/jhardin-repos-1sud/RosedaData/fromRWeeks/fromPrinter/60P_SESY_10PSI_02-09-2020-S3UPLOAD_ME/Payload/Data/60P_SESY_10PSI_02-09-2020-S3.png"
    # image_file_name = r"/home/james_hardin_11/Downloads/final1.png"
    image_file_name = r"/home/james_hardin_11/Desktop/TestFiles/Data/final.png"
    # image_file_name = r"/home/james_hardin_11/Downloads/1635867339_067320b1_Data_final.png"
    imageName = "image"
    extract_cs(image_file_name, imageName, pattern_file_name, color_threshold=0.5, glare_est=0.1)