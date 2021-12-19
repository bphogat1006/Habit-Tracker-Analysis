from app import app, db
import os
from calendar import month_name
import cv2
import imutils
from imutils import contours
from imutils.perspective import four_point_transform
import numpy as np
from matplotlib import pyplot


class Tracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datecreated = db.Column(db.DateTime, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(255), nullable=False)

    def getMonth(self):
        month_name[self.month]

# CLASS DERIVED FROM:
# https://www.pyimagesearch.com/2016/10/03/bubble-sheet-multiple-choice-scanner-and-test-grader-using-omr-python-and-opencv/
class TrackerScanner:

    # whether or not to blur image before thresholding
    __useBlurredForThresholding = True

    # init class
    def __init__(self, path):
        self.__path = path
        self.__readImage()

    # runs all processing methods to extract bubble data
    def scanTracker(self):
        self.__prepareImage()
        self.__fourPointTransform()
        self.__resizeTransformedImage()
        self.__binarize()
        self.__getBubbleContours()
        # if self.numBubblesDetected != 434:
        #     raise Exception(f"Tracker was not scanned correctly. Number of bubbles detected: {self.numBubblesDetected}/434")
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
        cv2.drawContours(image, self.__bubblesPartial, -1, (0, 255, 255), 3)
        cv2.drawContours(image, self.__bubblesEmpty, -1, (0, 0, 255), 3)
        return image

    def __createHistogram(self, data, bucketsize=1):
        minVal = min(data)
        maxVal = max(data)
        a = np.array(data)
        pyplot.title("histogram")
        pyplot.hist(a, bins = np.arange(minVal, maxVal, step=bucketsize))
        pyplot.savefig("histogram.jpg")

    # methods for finding and scanning the bubbles
    def __prepareImage(self):
        # auto-level image
        self.__image = self.__original.copy()
        gray = cv2.cvtColor(self.__original, cv2.COLOR_BGR2GRAY)
        blurred = cv2.bilateralFilter(gray, 5, 50, 75)
        maxLuma = min(max(blurred.flatten()), 245)
        self.__image = cv2.bilateralFilter(self.__original, 5, 50, 75)
        if(maxLuma < 245):
            self.__image = self.__image.astype('float64')
            self.__image *= 245/maxLuma
            self.__image = self.__image.astype('uint8')
        # get grayscale version of image
        self.__gray = cv2.cvtColor(self.__image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.bilateralFilter(self.__gray, 5, 50, 75)
        if self.__useBlurredForThresholding:
            self.__gray = blurred.copy()
        # find edges
        self.__edged = cv2.Canny(blurred, 75, 200)
        # dilate edges slightly to assist in finding document
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3, 3))
        self.__edged = cv2.dilate(self.__edged, kernel)

    def __fourPointTransform(self):	
        # find contours in the edge map, then initialize
        # the contour that corresponds to the document
        cnts = cv2.findContours(self.__edged.copy(), cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        docCnt = None
        # ensure that at least one contour was found
        if len(cnts) > 0:
            # sort the contours according to their size in
            # descending order
            cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
            # loop over the sorted contours
            for c in cnts:
                # approximate the contour
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                # if our approximated contour has four points,
                # then we can assume we have found the paper
                if len(approx) == 4:
                    docCnt = approx
                    break
        if docCnt is None: raise Exception("No 4 point contour found")
        self.__pageContour = cv2.cvtColor(self.__edged.copy(), cv2.COLOR_GRAY2BGR)
        cv2.drawContours(self.__pageContour, [docCnt], 0, (0, 255, 0), 3)
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
                                                cv2.THRESH_BINARY_INV, 199, 10)
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
                "location": (x>460 and y>420),
                "aspect_ratio": abs(1-ar) < 0.3,
                "size": 30 < w < 50,
                "num_vertices": 6 < len(approxVerts) < 17,
                "area": 850 < area < 1200
            }
            if checks["location"] and checks["aspect_ratio"] and checks["size"] and checks["num_vertices"] and checks["area"]:
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
        ratios = []
        self.__bubblesFilled = []
        self.__bubblesPartial = []
        self.__bubblesEmpty = []
        self.data = [[] for i in range(14)]
        colordata = [[] for i in range(14)]
        thresh_inv = cv2.bitwise_not(self.__thresh.copy())
        for i in range(14):
            row = self.__bubbleCnts[i]
            for index, bubble in enumerate(row):
                mask = np.zeros(self.__thresh.shape, dtype="uint8")
                cv2.drawContours(mask, [bubble], -1, 255, -1)
                mask = cv2.bitwise_and(self.__thresh, self.__thresh, mask=mask)
                black = cv2.countNonZero(mask)

                mask2 = np.zeros(thresh_inv.shape, dtype="uint8")
                cv2.drawContours(mask2, [bubble], -1, 255, -1)
                mask2 = cv2.bitwise_and(thresh_inv, thresh_inv, mask=mask2)
                white = cv2.countNonZero(mask2)

                ratio = white/black*100
                ratios.append(ratio)
                # if 10<ratio<70:
                #     print(i+1, index+1, round(ratio))

                if ratio > 45:
                    self.data[i].append(0)
                    self.__bubblesEmpty.append(bubble)
                elif ratio > 20:
                    self.data[i].append(0.5)
                    self.__bubblesPartial.append(bubble)
                else:
                    self.data[i].append(1)
                    self.__bubblesFilled.append(bubble)
        
        self.__createHistogram(ratios)
