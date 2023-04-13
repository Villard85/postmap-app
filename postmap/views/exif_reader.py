#!/usr/bin/env python
# coding: utf-8

# In[4]:


from PIL import Image
from PIL import ExifTags


# In[8]:


def extract_coords(f_name):
    img = Image.open(f_name)
    exifDataRaw = img._getexif()
    if exifDataRaw is None:
#        print("Sorry, image has no exif data.")
        return -10
    else:
        exifData = {}
        for tag, value in exifDataRaw.items():
            decodedTag = ExifTags.TAGS.get(tag, tag)
            exifData[decodedTag] = value 
        if(exifData.has_key('GPSInfo')):
            gpsData = {}
            for tag, value in exifData['GPSInfo'].items():
                decodedTag = ExifTags.GPSTAGS.get(tag, tag)
                gpsData[decodedTag] = value
            lat = float(gpsData['GPSLatitude'][0][0])/gpsData['GPSLatitude'][0][1]                 +float(gpsData['GPSLatitude'][1][0])/gpsData['GPSLatitude'][1][1]/60                 +float(gpsData['GPSLatitude'][2][0])/gpsData['GPSLatitude'][2][1]/3600
            if(gpsData['GPSLatitudeRef'] != u'N'):
                lat = -lat
            lon = float(gpsData['GPSLongitude'][0][0])/gpsData['GPSLongitude'][0][1]                 +float(gpsData['GPSLongitude'][1][0])/gpsData['GPSLongitude'][1][1]/60                 +float(gpsData['GPSLongitude'][2][0])/gpsData['GPSLongitude'][2][1]/3600
            if(gpsData['GPSLongitudeRef'] != u'E'):
                lon = -lon
            return lat, lon
        else:
            return -20


# In[7]:


def extract_time(f_name):
    img = Image.open(f_name)
    exifDataRaw = img._getexif()
    if exifDataRaw is None:
        print("Sorry, image has no exif data.")
        return -10
    else:
        exifData = {}
        for tag, value in exifDataRaw.items():
            decodedTag = ExifTags.TAGS.get(tag, tag)
            exifData[decodedTag] = value
        return exifData['DateTime']


# In[18]:


def get_orientation(f_name):
    img = Image.open(f_name)
    (width, height) = img.size
    if height > width:
        #image = image.rotate(90)
        #image.save(f_name, quality=100)
        return 'v'
    else:
        return 'h'

