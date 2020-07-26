import numpy
import typing
import cv2
import colorsys
import scipy.spatial.distance as spsd

from .data import Image, ColorSpace

BLACK = (0, 0, 0)


def empty_like (image: Image, channels = 3):
    return numpy.zeros((image.height, image.width, channels), numpy.uint8)


def findBlobs(self, threshval = -1, minsize=10, maxsize=0, threshblocksize=0, threshconstant=5,appx_level=3):
        """

        **SUMMARY**
        Find blobs  will look for continuous
        light regions and return them as Blob features in a FeatureSet.  Parameters
        specify the binarize filter threshold value, and minimum and maximum size for blobs.
        If a threshold value is -1, it will use an adaptive threshold.  See binarize() for
        more information about thresholding.  The threshblocksize and threshconstant
        parameters are only used for adaptive threshold.
        **PARAMETERS**
        * *threshval* - the threshold as an integer or an (r,g,b) tuple , where pixels below (darker) than thresh are set to to max value,
          and all values above this value are set to black. If this parameter is -1 we use Otsu's method.
        * *minsize* - the minimum size of the blobs, in pixels, of the returned blobs. This helps to filter out noise.
        * *maxsize* - the maximim size of the blobs, in pixels, of the returned blobs.
        * *threshblocksize* - the size of the block used in the adaptive binarize operation. *TODO - make this match binarize*
        * *appx_level* - The blob approximation level - an integer for the maximum distance between the true edge and the
          approximation edge - lower numbers yield better approximation.
          .. warning::
            This parameter must be an odd number.
        * *threshconstant* - The difference from the local mean to use for thresholding in Otsu's method. *TODO - make this match binarize*
        **RETURNS**
        Returns a featureset (basically a list) of :py:class:`blob` features. If no blobs are found this method returns None.
        **EXAMPLE**
        >>> img = Image("lenna")
        >>> fs = img.findBlobs()
        >>> if( fs is not None ):
        >>>     fs.draw()
        **NOTES**
        .. Warning::
          For blobs that live right on the edge of the image OpenCV reports the position and width
          height as being one over for the true position. E.g. if a blob is at (0,0) OpenCV reports
          its position as (1,1). Likewise the width and height for the other corners is reported as
          being one less than the width and height. This is a known bug.
        **SEE ALSO**
        :py:meth:`threshold`
        :py:meth:`binarize`
        :py:meth:`invert`
        :py:meth:`dilate`
        :py:meth:`erode`
        :py:meth:`findBlobsFromPalette`
        :py:meth:`smartFindBlobs`
        """

        if (maxsize == 0):
            maxsize = self.width * self.height

        #create a single channel image, thresholded to parameters

        blobmaker = BlobMaker()
        blobs = blobmaker.extractFromBinary(self.binarize(threshval, 255, threshblocksize, threshconstant).invert(),
            self, minsize = minsize, maxsize = maxsize,appx_level=appx_level)

        if not len(blobs):
            return None

        return FeatureSet(blobs).sortArea()


def splitChannels(image: Image, grayscale: bool = True) -> typing.Tuple[Image, Image, Image]:
    """
    **SUMMARY**
    Split the channels of an image into RGB (not the default BGR)
    single parameter is whether to return the channels as grey images (default)
    or to return them as tinted color image
    **PARAMETERS**
    * *grayscale* - If this is true we return three grayscale images, one per channel.
        if it is False return tinted images.
    **RETURNS**
    A tuple of of 3 image objects.
    **EXAMPLE**
    >>> img = Image("lenna")
    >>> data = img.splitChannels()
    >>> for d in data:
    >>>    d.show()
    >>>    time.sleep(1)
    **SEE ALSO**
    :py:meth:`mergeChannels`
    """

    r, g, b = cv2.split(image.data)

    if (grayscale):
        red = cv2.merge((r, r, r))
        green = cv2.merge((g, g, g))
        blue = cv2.merge((b, b, b))
    else:
        red = cv2.merge((None, None, r))
        green = cv2.merge((None, g, None))
        blue = cv2.merge((b, None, None))

    return (
        Image(red, colorspace = ColorSpace.BGR), 
        Image(green, colorspace = ColorSpace.BGR), 
        Image(blue, colorspace = ColorSpace.BGR)
    )


def threshold(image: Image, value: int) -> Image:
    """
    **SUMMARY**
    We roll old school with this vanilla threshold function. It takes your image
    converts it to grayscale, and applies a threshold. Values above the threshold
    are white, values below the threshold are black. The resulting
    black and white image is returned.
    **PARAMETERS**
    * *value* - the threshold, goes between 0 and 255.
    **RETURNS**
    A black and white SimpleCV image.
    **EXAMPLE**
    >>> img = Image("purplemonkeydishwasher.png")
    >>> result = img.threshold(42)
    **SEE ALSO**
    :py:meth:`binarize`
    """
    gray = _getGrayscaleBitmap(image)
    retval, result = cv2.threshold(gray, value, 255, cv2.THRESH_BINARY)
    return Image(result, colorspace = ColorSpace.GRAY)

def erode(image: Image, iterations: int = 1, kernelsize: int = 3):
    """
    **SUMMARY**
    Apply a morphological erosion. An erosion has the effect of removing small bits of noise
    and smothing blobs.
    This implementation uses the default openCV 3X3 square kernel
    Erosion is effectively a local minima detector, the kernel moves over the image and
    takes the minimum value inside the kernel.
    iterations - this parameters is the number of times to apply/reapply the operation
    * See: http://en.wikipedia.org/wiki/Erosion_(morphology).
    * See: http://opencv2.willowgarage.com/documentation/cpp/image_filtering.html#cv-erode
    * Example Use: A threshold/blob image has 'salt and pepper' noise.
    * Example Code: /examples/MorphologyExample.py
    **PARAMETERS**
    * *iterations* - the number of times to run the erosion operation.
    **RETURNS**
    A SimpleCV image.
    **EXAMPLE**
    >>> img = Image("lenna")
    >>> derp = img.binarize()
    >>> derp.erode(3).show()
    **SEE ALSO**
    :py:meth:`dilate`
    :py:meth:`binarize`
    :py:meth:`morphOpen`
    :py:meth:`morphClose`
    :py:meth:`morphGradient`
    :py:meth:`findBlobsFromMask`
    """
    kernel = numpy.ones((kernelsize, kernelsize), numpy.uint8)
    eroded = cv2.erode(image.data, kernel, iterations)
    return Image(eroded, colorspace = image.colorspace)


def dilate(image: Image, iterations: int = 1, kernelsize: int = 3) -> Image:
    kernel = numpy.ones((kernelsize, kernelsize), numpy.uint8)
    dilated = cv2.dilate(image.data, kernel, iterations)
    return Image(dilated, colorspace = image.colorspace)


def invert(image: Image) -> Image:
    """
    **SUMMARY**
    Invert (negative) the image note that this can also be done with the
    unary minus (-) operator. For binary image this turns black into white and white into black (i.e. white is the new black).
    **RETURNS**
    The opposite of the current image.
    **EXAMPLE**
    >>> img  = Image("polar_bear_in_the_snow.png")
    >>> img.invert().save("black_bear_at_night.png")
    **SEE ALSO**
    :py:meth:`binarize`
    """
    return Image(-image.data, image.colorspace)

def colorDistance(image: Image, color = BLACK) -> Image:
    """
    **SUMMARY**
    Returns an image representing the distance of each pixel from a given color
    tuple, scaled between 0 (the given color) and 255.  Pixels distant from the
    given tuple will appear as brighter and pixels closest to the target color
    will be darker.
    By default this will give image intensity (distance from pure black)
    **PARAMETERS**
    * *color*  - Color object or Color Tuple
    **RETURNS**
    A SimpleCV Image.
    **EXAMPLE**
    >>> img = Image("logo")
    >>> img2 = img.colorDistance(color=Color.BLACK)
    >>> img2.show()
    **SEE ALSO**
    :py:meth:`binarize`
    :py:meth:`hueDistance`
    :py:meth:`findBlobsFromMask`
    """
    pixels = image.data.reshape((-1, 3))   #reshape our matrix to 1xN
    distances = spsd.cdist(pixels, [color]) #calculate the distance each pixel is
    distances *= (255.0 / distances.max()) #normalize to 0 - 255
    return Image(distances.reshape((image.width, image.height)), colorspace = image.colorspace) #return an Image

def hueDistance(image: Image, color = BLACK, minsaturation = 20, minvalue = 20, maxvalue = 255) -> Image:
    """
    **SUMMARY**
    Returns an image representing the distance of each pixel from the given hue
    of a specific color.  The hue is "wrapped" at 180, so we have to take the shorter
    of the distances between them -- this gives a hue distance of max 90, which we'll
    scale into a 0-255 grayscale image.
    The minsaturation and minvalue are optional parameters to weed out very weak hue
    signals in the picture, they will be pushed to max distance [255]
    **PARAMETERS**
    * *color* - Color object or Color Tuple.
    * *minsaturation*  - the minimum saturation value for color (from 0 to 255).
    * *minvalue*  - the minimum hue value for the color (from 0 to 255).
    **RETURNS**
    A simpleCV image.
    **EXAMPLE**
    >>> img = Image("logo")
    >>> img2 = img.hueDistance(color=Color.BLACK)
    >>> img2.show()
    **SEE ALSO**
    :py:meth:`binarize`
    :py:meth:`hueDistance`
    :py:meth:`morphOpen`
    :py:meth:`morphClose`
    :py:meth:`morphGradient`
    :py:meth:`findBlobsFromMask`
    """
    if isinstance(color,  (float,int)):
        color_hue = color
    else:
        hsv_float = colorsys.rgb_to_hsv(*color)
        color_hue = hsv_float[0] * 180

    vsh_matrix = _getHSVBitmap(image).reshape((-1, 3)) #again, gets transposed to vsh
    hue_channel = numpy.cast['int'](vsh_matrix[:,2])

    if color_hue < 90:
        hue_loop = 180
    else:
        hue_loop = -180
    #set whether we need to move back or forward on the hue circle

    distances = numpy.minimum(numpy.abs(hue_channel - color_hue), numpy.abs(hue_channel - (color_hue + hue_loop)))
    #take the minimum distance for each pixel


    distances = numpy.where(
        numpy.logical_and(vsh_matrix[:,0] > minvalue, vsh_matrix[:,1] > minsaturation),
        distances * (255.0 / 90.0), #normalize 0 - 90 -> 0 - 255
        255.0) #use the maxvalue if it false outside of our value/saturation tolerances

    return Image(distances.reshape((image.width, image.height)), colorspace = image.colorspace)


def crop(self, x , y = None, w = None, h = None, centered=False, smart=False):
        """
        
        **SUMMARY**
        
        Consider you want to crop a image with the following dimension::
            (x,y)
            +--------------+
            |              |
            |              |h
            |              |
            +--------------+
                  w      (x1,y1)
        
        Crop attempts to use the x and y position variables and the w and h width
        and height variables to crop the image. When centered is false, x and y
        define the top and left of the cropped rectangle. When centered is true
        the function uses x and y as the centroid of the cropped region.
        You can also pass a feature into crop and have it automatically return
        the cropped image within the bounding outside area of that feature
        Or parameters can be in the form of a
         - tuple or list : (x,y,w,h) or [x,y,w,h]
         - two points : (x,y),(x1,y1) or [(x,y),(x1,y1)]
        **PARAMETERS**
        * *x* - An integer or feature.
              - If it is a feature we crop to the features dimensions.
              - This can be either the top left corner of the image or the center cooridnate of the the crop region.
              - or in the form of tuple/list. i,e (x,y,w,h) or [x,y,w,h]
              - Otherwise in two point form. i,e [(x,y),(x1,y1)] or (x,y)
        * *y* - The y coordinate of the center, or top left corner  of the crop region.
              - Otherwise in two point form. i,e (x1,y1)
        * *w* - Int - the width of the cropped region in pixels.
        * *h* - Int - the height of the cropped region in pixels.
        * *centered*  - Boolean - if True we treat the crop region as being the center
          coordinate and a width and height. If false we treat it as the top left corner of the crop region.
        * *smart* - Will make sure you don't try and crop outside the image size, so if your image is 100x100 and you tried a crop like img.crop(50,50,100,100), it will autoscale the crop to the max width.
        
        **RETURNS**
        A SimpleCV Image cropped to the specified width and height.
        **EXAMPLE**
        >>> img = Image('lenna')
        >>> img.crop(50,40,128,128).show()
        >>> img.crop((50,40,128,128)).show() #roi
        >>> img.crop([50,40,128,128]) #roi
        >>> img.crop((50,40),(178,168)) # two point form
        >>> img.crop([(50,40),(178,168)]) # two point form
        >>> img.crop([x1,x2,x3,x4,x5],[y1,y1,y3,y4,y5]) # list of x's and y's
        >>> img.crop([(x,y),(x,y),(x,y),(x,y),(x,y)] # list of (x,y)
        >>> img.crop(x,y,100,100, smart=True)
        **SEE ALSO**
        :py:meth:`embiggen`
        :py:meth:`regionSelect`
        """

        if smart:
          if x > self.width:
            x = self.width
          elif x < 0:
            x = 0
          elif y > self.height:
            y = self.height
          elif y < 0:
            y = 0
          elif (x + w) > self.width:
            w = self.width - x
          elif (y + h) > self.height:
            h = self.height - y
          
        if(isinstance(x,numpy.ndarray)):
            x = x.tolist()
        if(isinstance(y,numpy.ndarray)):
            y = y.tolist()

        #If it's a feature extract what we need
        if(isinstance(x, Feature)):
            theFeature = x
            x = theFeature.points[0][0]
            y = theFeature.points[0][1]
            w = theFeature.width()
            h = theFeature.height()

        elif(isinstance(x, (tuple,list)) and len(x) == 4 and isinstance(x[0],(int, long, float))
             and y == None and w == None and h == None):
                x,y,w,h = x
        # x of the form [(x,y),(x1,y1),(x2,y2),(x3,y3)]
        # x of the form [[x,y],[x1,y1],[x2,y2],[x3,y3]]
        # x of the form ([x,y],[x1,y1],[x2,y2],[x3,y3])
        # x of the form ((x,y),(x1,y1),(x2,y2),(x3,y3))
        # x of the form (x,y,x1,y2) or [x,y,x1,y2]            
        elif( isinstance(x, (list,tuple)) and
              isinstance(x[0],(list,tuple)) and
              (len(x) == 4 and len(x[0]) == 2 ) and
              y == None and w == None and h == None):
            if (len(x[0])==2 and len(x[1])==2 and len(x[2])==2 and len(x[3])==2):
                xmax = numpy.max([x[0][0],x[1][0],x[2][0],x[3][0]])
                ymax = numpy.max([x[0][1],x[1][1],x[2][1],x[3][1]])
                xmin = numpy.min([x[0][0],x[1][0],x[2][0],x[3][0]])
                ymin = numpy.min([x[0][1],x[1][1],x[2][1],x[3][1]])
                x = xmin
                y = ymin
                w = xmax-xmin
                h = ymax-ymin
            else:
                logger.warning("x should be in the form  ((x,y),(x1,y1),(x2,y2),(x3,y3))")
                return None
 
        # x,y of the form [x1,x2,x3,x4,x5....] and y similar
        elif(isinstance(x, (tuple,list)) and
             isinstance(y, (tuple,list)) and
             len(x) > 4 and len(y) > 4 ):
            if(isinstance(x[0],(int, long, float)) and isinstance(y[0],(int, long, float))):
                xmax = numpy.max(x)
                ymax = numpy.max(y)
                xmin = numpy.min(x)
                ymin = numpy.min(y)
                x = xmin
                y = ymin
                w = xmax-xmin
                h = ymax-ymin
            else:
                logger.warning("x should be in the form x = [1,2,3,4,5] y =[0,2,4,6,8]")
                return None

        # x of the form [(x,y),(x,y),(x,y),(x,y),(x,y),(x,y)]
        elif(isinstance(x, (list,tuple)) and
             len(x) > 4 and len(x[0]) == 2 and y == None and w == None and h == None):
            if(isinstance(x[0][0],(int, long, float))):
                xs = [pt[0] for pt in x]
                ys = [pt[1] for pt in x]
                xmax = numpy.max(xs)
                ymax = numpy.max(ys)
                xmin = numpy.min(xs)
                ymin = numpy.min(ys)
                x = xmin
                y = ymin
                w = xmax-xmin
                h = ymax-ymin
            else:
                logger.warning("x should be in the form [(x,y),(x,y),(x,y),(x,y),(x,y),(x,y)]")
                return None

        # x of the form [(x,y),(x1,y1)]
        elif(isinstance(x,(list,tuple)) and len(x) == 2 and isinstance(x[0],(list,tuple)) and isinstance(x[1],(list,tuple)) and y == None and w == None and h == None):
            if (len(x[0])==2 and len(x[1])==2):
                xt = numpy.min([x[0][0],x[1][0]])
                yt = numpy.min([x[0][0],x[1][0]])
                w = numpy.abs(x[0][0]-x[1][0])
                h = numpy.abs(x[0][1]-x[1][1])
                x = xt
                y = yt
            else:
                logger.warning("x should be in the form [(x1,y1),(x2,y2)]")
                return None

        # x and y of the form (x,y),(x1,y2)
        elif(isinstance(x, (tuple,list)) and isinstance(y,(tuple,list)) and w == None and h == None):
            if (len(x)==2 and len(y)==2):
                xt = numpy.min([x[0],y[0]])
                yt = numpy.min([x[1],y[1]])
                w = numpy.abs(y[0]-x[0])
                h = numpy.abs(y[1]-x[1])
                x = xt
                y = yt
                
            else:
                logger.warning("if x and y are tuple it should be in the form (x1,y1) and (x2,y2)")
                return None



        if(y == None or w == None or h == None):
            print ("Please provide an x, y, width, height to function")

        if( w <= 0 or h <= 0 ):
            logger.warning("Can't do a negative crop!")
            return None

        retVal = cv2.CreateImage((int(w),int(h)), cv2.IPL_DEPTH_8U, 3)
        if( x < 0 or y < 0 ):
            logger.warning("Crop will try to help you, but you have a negative crop position, your width and height may not be what you want them to be.")


        if( centered ):
            rectangle = (int(x-(w/2)), int(y-(h/2)), int(w), int(h))
        else:
            rectangle = (int(x), int(y), int(w), int(h))

        (topROI, bottomROI) = self._rectOverlapROIs((rectangle[2],rectangle[3]),(self.width,self.height),(rectangle[0],rectangle[1]))

        if( bottomROI is None ):
            logger.warning("Hi, your crop rectangle doesn't even overlap your image. I have no choice but to return None.")
            return None

        retVal = numpy.zeros((bottomROI[3],bottomROI[2],3),dtype='uint8')

        retVal= self.getNumpyCv2()[bottomROI[1]:bottomROI[1] + bottomROI[3],bottomROI[0]:bottomROI[0] + bottomROI[2],:] 
        
        img = Image(retVal, colorSpace=self._colorSpace,cv2image = True)

        #Buffering the top left point (x, y) in a image.
        img._uncroppedX = self._uncroppedX + int(x)
        img._uncroppedY = self._uncroppedY + int(y)
        return img


def _image_or_number (other: typing.Union[Image, int, float]) -> typing.Union[numpy.ndarray, int, float]:
    if isinstance(other, Image):
        return other.data
    else:
        return other

def __sub__(image: Image, other: typing.Union[Image, int, float]) -> Image:
    return Image(image.data - _image_or_number(other.data), colorspace = image.colorspace)

def __add__(image: Image, other: typing.Union[Image, int, float]) -> Image:
    return Image(image.data + _image_or_number(other.data), colorspace = image.colorspace)

def __and__(image: Image, other: typing.Union[Image, int, float]) -> Image:
    return Image(numpy.logical_and(image.data, _image_or_number(other.data)), colorspace = image.colorspace)

def __or__(image: Image, other: typing.Union[Image, int, float]) -> Image:
    return Image(numpy.logical_or(image.data, _image_or_number(other.data)), colorspace = image.colorspace)

def __div__(image: Image, other: typing.Union[Image, int, float]) -> Image:
    return Image(image.data / _image_or_number(other.data), colorspace = image.colorspace)

def __mul__(image: Image, other: typing.Union[Image, int, float]) -> Image:
    return Image(image.data * _image_or_number(other.data), colorspace = image.colorspace)

def __pow__(image: Image, other: typing.Union[int, float]) -> Image:
    return Image(numpy.power(image.data, other), colorspace = image.colorspace)

def __neg__(image: Image) -> Image:
    return Image(-image.data, colorspace = image.colorspace)

__invert__ = __neg__

def max(image: Image, other: typing.Union[int, Image]) -> Image:
    """
    **SUMMARY**
    The maximum value of my image, and the other image, in each channel
    If other is a number, returns the maximum of that and the number
    **PARAMETERS**
    * *other* - Image of the same size or a number.
    **RETURNS**
    A SimpelCV image.
    """

    if type(other) is int:
        result = numpy.max(image.data, other)

    else:
        if (image.width, image.height) != (other.width, other.height):
            warnings.warn("Both images should have same sizes. Returning None.")
            return None

        result = cv2.max(image.data, other.data)
    
    return Image(result, colorspace = image.colorspace)


def min(image: Image, other: typing.Union[int, Image]):
    """
    **SUMMARY**
    The minimum value of my image, and the other image, in each channel
    If other is a number, returns the minimum of that and the number
    **Parameter**
    * *other* - Image of the same size or number
    **Returns**
    IMAGE
    """

    if type(other) is int:
        result = numpy.min(image.data, other)

    else:
        if (image.width, image.height) != (other.width, other.height):
            warnings.warn("Both images should have same sizes. Returning None.")
            return None

        result = cv2.min(image.data, other.data)
    
    return Image(result, colorspace = image.colorspace)


def _getGrayscaleBitmap(image: Image) -> numpy.ndarray:
    if (image.colorspace == ColorSpace.BGR or
            image.colorspace == ColorSpace.UNKNOWN):
        return cv2.cvtColor(image.data, cv2.COLOR_BGR2GRAY)
    elif (image.colorspace == ColorSpace.RGB):
        return cv2.cvtColor(image.data, cv2.COLOR_RGB2GRAY)
    elif (image.colorspace == ColorSpace.HLS):
        return cv2.cvtColor(cv2.cvtColor(image.data, cv2.COLOR_HLS2RGB), cv2.COLOR_RGB2GRAY)
    elif (image.colorspace == ColorSpace.HSV):
        return cv2.cvtColor(cv2.cvtColor(image.data, cv2.COLOR_HSV2RGB), cv2.COLOR_RGB2GRAY)
    elif (image.colorspace == ColorSpace.XYZ):
        return cv2.cvtColor(cv2.cvtColor(image.data, cv2.COLOR_XYZ2RGB), cv2.COLOR_RGB2GRAY)
    elif (image.colorspace == ColorSpace.GRAY):
        return cv2.split(image.data)[0]
    else:
        logger.warning("_getGrayscaleBitmap: There is no supported conversion to gray colorspace")
        return None

def _getHSVBitmap(image: Image) -> numpy.ndarray:
    if (image.colorspace == ColorSpace.BGR or
            image.colorspace == ColorSpace.UNKNOWN):
        return cv2.cvtColor(image.data, cv2.COLOR_BGR2HSV)
    elif (image.colorspace == ColorSpace.RGB):
        return cv2.cvtColor(image.data, cv2.COLOR_RGB2HSV)
    elif (image.colorspace == ColorSpace.HLS):
        return cv2.cvtColor(cv2.cvtColor(image.data, cv2.COLOR_HLS2RGB), cv2.COLOR_RGB2HSV)
    elif (image.colorspace == ColorSpace.HSV):
        return image.data
    elif (image.colorspace == ColorSpace.XYZ):
        return cv2.cvtColor(cv2.cvtColor(image.data, cv2.COLOR_XYZ2RGB), cv2.COLOR_RGB2HSV)
    elif (image.colorspace == ColorSpace.GRAY):
        return cv2.cvtColor(cv2.cvtColor(image.data, cv2.COLOR_GRAY2RGB), cv2.COLOR_RGB2HSV)
    else:
        logger.warning("_getHSVBitmap: There is no supported conversion to HSV colorspace")
        return None