import cv2
import imutils
from imutils import contours
from imutils.perspective import four_point_transform
import numpy as np
from matplotlib import pyplot

# DERIVED FROM https://www.pyimagesearch.com/2016/10/03/bubble-sheet-multiple-choice-scanner-and-test-grader-using-omr-python-and-opencv/
class TrackerScanner:
    
    # init class
    def __init__(self, path):
        self.__path = path
        self.__readImage()
        
    # runs all processing methods to extract bubble data
    def scanTracker(self, docCoords):
        self.__prepareImage()
        self.__docCoords = docCoords
        self.__fourPointTransform()
        self.__resizeTransformedImage()
        self.__binarize()
        self.__getBubbleContours()
        if self.numBubblesDetected != 434:
            self.__saveImage(self.__thresh, "thresh")
            self.__saveImage(self.__bubblesFound, "bubblesFound")
            raise Exception(f"Tracker was not scanned correctly. Number of bubbles detected: {self.numBubblesDetected}/434")
        self.__sortContours()
        self.__scanBubbles()
        self.__saveImage(self.__paper, draw_contours=True)

    # misc methods for reading/saving/analyzing images
    def __readImage(self):
        try:
            self.__original = cv2.imread(self.__path)
        except Exception as e:
            print(f"Error while loader tracker image to scan bubbles.\nPath: {self.__path}")
            print(e)
    def __saveImage(self, image, filename="", draw_contours=False):
        path = self.__path
        if draw_contours:
            image = self.__drawBubbleContours(image)
        if filename != "":
            parts = self.__path.split(".")
            parts[-2] += "_"+filename
            path = '.'.join(parts)
        cv2.imwrite(path, image)
    def __drawBubbleContours(self, image):
        if(len(image.shape)<3):
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        cv2.drawContours(image, self.__bubblesFilled, -1, (0, 255, 0), 3)
        cv2.drawContours(image, self.__bubblesPartial, -1, (255, 0, 0), 3)
        cv2.drawContours(image, self.__bubblesEmpty, -1, (0, 0, 255), 3)
        return image
    def __createHistogram(self, data, bucketsize=1, logScaleX=False, logScaleY=False):
        minVal = min(data)
        maxVal = max(data)
        a = np.array(data)
        pyplot.title("histogram")
        pyplot.hist(a, bins = np.arange(minVal, maxVal, step=bucketsize))
        if logScaleX:
            pyplot.xscale('log')
        if logScaleY:
            pyplot.yscale('log')
        pyplot.savefig("histogram.jpg")

    # methods for finding and scanning the bubbles
    def __prepareImage(self):
        # auto white point image
        self.__image = self.__original.copy()
        self.__image = cv2.bilateralFilter(self.__original, 5, 50, 75)
        maxLuma = max(self.__image.flatten())
        self.__image = self.__image.astype('float64')
        self.__image *= 255/maxLuma
        self.__image = self.__image.astype('uint8')
        # get grayscale version of image
        self.__gray = cv2.cvtColor(self.__image, cv2.COLOR_BGR2GRAY)
    def __fourPointTransform(self):	
        # get document contour using coordinates of the corners
        height, width, channels = self.__image.shape
        docCnt = []
        for key in self.__docCoords:
            xy = self.__docCoords.get(key)
            x = xy.get('x')*width
            y = xy.get('y')*height
            docCnt.append([x, y])
        docCnt = np.array(docCnt).reshape((-1,1,2)).astype(np.int32)
        self.__docContour = self.__image.copy()
        cv2.drawContours(self.__docContour, [docCnt], 0, (0, 255, 0), 3)
        # apply a four point perspective transform to both the
        # original image and grayscale image to obtain a top-down
        # birds eye view of the paper
        self.__paper = four_point_transform(self.__image, docCnt.reshape(4, 2))
        self.__warped = four_point_transform(self.__gray, docCnt.reshape(4, 2))
    def __resizeTransformedImage(self):
        dim = (2000, 1545)
        self.__paper = cv2.resize(self.__paper, dim, interpolation = cv2.INTER_AREA)
        self.__warped = cv2.resize(self.__warped, dim, interpolation = cv2.INTER_AREA)
    def __binarize(self):
        # apply Otsu's thresholding method to binarize the warped
        # piece of paper
        self.__thresh = cv2.adaptiveThreshold(self.__warped, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                cv2.THRESH_BINARY_INV, 135, 3)
        # slight adjustment with morphological operation to close any open bubble contours
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3, 3))
        self.__thresh = cv2.dilate(self.__thresh, kernel)
    def __getBubbleContours(self):
        # find contours in the thresholded image, then initialize
        # the list of contours that correspond to bubbles
        cnts = cv2.findContours(self.__thresh.copy(), cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        self.__bubbleCnts = []
        # loop over the contours
        for c in cnts:
            # compute the bounding box of the contour, then use the
            # bounding box to derive the aspect ratio
            (x, y, w, h) = cv2.boundingRect(c)
            ar = w / float(h)
            # calculate approx contour to get the number of vertices
            # for the contour, as well as the area of the contour
            approxVerts = cv2.approxPolyDP(c,0.01*cv2.arcLength(c,True),True)
            area = cv2.contourArea(c)

            # cv2.rectangle(final,(x,y),(x+w,y+h),(0,255,0),2)
            # in order to label the contour as a question, region
            # should be sufficiently wide, sufficiently tall, and
            # have an aspect ratio approximately equal to 1
            checks = {
                "location": 460<x<1910 and 420<y<1340,
                "aspect_ratio": abs(1-ar) < 0.3,
                "num_vertices": 6 < len(approxVerts) < 20,
                "area": 850 < area < 1300
            }
            if checks["location"] and checks["aspect_ratio"] and checks["num_vertices"] and checks["area"]:
                self.__bubbleCnts.append(c)
        self.numBubblesDetected = len(self.__bubbleCnts)
        self.__bubblesFound = cv2.cvtColor(self.__thresh.copy(), cv2.COLOR_GRAY2BGR)
        cv2.drawContours(self.__bubblesFound, self.__bubbleCnts, -1, (0, 255, 0), 3)
    def __sortContours(self):
        # sort the question contours top-to-bottom
        self.__bubbleCnts = contours.sort_contours(self.__bubbleCnts,
            method="top-to-bottom")[0]
        # each habit has 31 bubbles for each day, so loop over the
        # question in batches of 31
        sortedBubbles = []
        for i in range(14):
            i*=31
            row = self.__bubbleCnts[i:i+31]
            # sort each row of bubbles from left to right
            row = contours.sort_contours(row, method="left-to-right")[0]
            sortedBubbles.append(row)
        self.__bubbleCnts = sortedBubbles
    def __scanBubbles(self):
        histogram = []
        self.__bubblesFilled = []
        self.__bubblesPartial = []
        self.__bubblesEmpty = []
        self.data = [[] for i in range(14)]
        colordata = [[] for i in range(14)]
        thresh_inv = cv2.bitwise_not(self.__thresh.copy())
        for activityIndex in range(14):
            activityBubbles = self.__bubbleCnts[activityIndex]
            for day, bubble in enumerate(activityBubbles):
                mask = np.zeros(self.__thresh.shape, dtype="uint8")
                cv2.drawContours(mask, [bubble], -1, 255, -1)
                mask = cv2.bitwise_and(self.__thresh, self.__thresh, mask=mask)
                filledArea = cv2.countNonZero(mask)+1

                mask2 = np.zeros(thresh_inv.shape, dtype="uint8")
                cv2.drawContours(mask2, [bubble], -1, 255, -1)
                mask2 = cv2.bitwise_and(thresh_inv, thresh_inv, mask=mask2)
                unfilledArea = cv2.countNonZero(mask2)+1

                ratioFilled = unfilledArea/filledArea*100
                histogram.append(ratioFilled)

                if ratioFilled > 55:
                    self.data[activityIndex].append(0)
                    self.__bubblesEmpty.append(bubble)
                elif ratioFilled > 16:
                    self.data[activityIndex].append(0.5)
                    self.__bubblesPartial.append(bubble)
                else:
                    self.data[activityIndex].append(1)
                    self.__bubblesFilled.append(bubble)
        
        self.__createHistogram(histogram, logScaleY=True)
