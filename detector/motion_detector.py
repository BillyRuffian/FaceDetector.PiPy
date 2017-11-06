from PyQt5 import QtCore, QtGui
import time
import cv2
import imutils
import logging
from  copy import copy

from picamera.array import PiRGBArray
from picamera import PiCamera

logger = logging.getLogger( __name__ )

class MotionDetector( QtCore.QThread ):
    
    frame_signal = QtCore.pyqtSignal( QtGui.QImage )
    motion_signal = QtCore.pyqtSignal( object )
    
    def __init__( self, config={} ):
        QtCore.QThread.__init__(self)
        self.config = config
        

    def run( self ):
        logger.debug( 'Motion detector started' )
        camera = self.get_camera()
        self.prepare_camera( camera )
        
        raw_capture = PiRGBArray( camera, size=tuple( self.config['resolution'] ) )
        self.background_average = None
        motion_frame_count = 0
        # capture frames 
        for f in camera.capture_continuous( raw_capture, format='bgr', use_video_port=True ):
            
            # boolean set if motion is detected
            triggered = False
            frame = f.array
            
            greyscale_frame = self.greyscale_and_blur( frame )

            if self.background_model_needs_initialising( frame=greyscale_frame ):
                raw_capture.truncate( 0 )                
                continue

            cv2.accumulateWeighted( greyscale_frame, self.background_average, 0.5 )
            frameDelta = cv2.absdiff( greyscale_frame, cv2.convertScaleAbs( self.background_average) )


            # apply threshold
            threshold = cv2.threshold( frameDelta, self.config['delta_threshold'], 255, cv2.THRESH_BINARY )[1]
            threshold = cv2.dilate( threshold, None, iterations=2 )
            contours = cv2.findContours( threshold.copy(), 
                                         cv2.RETR_EXTERNAL, 
                                         cv2.CHAIN_APPROX_SIMPLE )
            # grab the right contour depending on whether we are using OpenCV2 or OpenCV3
            contours = contours[0] if imutils.is_cv2() else contours[1]
            bounding_rectangles = self.contours_to_rectangles( contours=contours )
            triggered = len( bounding_rectangles ) > 0
            

            if triggered:
                #bounding_rectangles = self.contours_to_rectangles( contours=contours )
                motion_frame_count += 1
                if motion_frame_count >= self.config['minimum_motion_frames']:
                    logger.debug( 'Motion trigger' )
                    motion_frame_count = 0
                    (x,y,w,h) = self.enclosing_bounds( rects=bounding_rectangles )
                    area_of_interest = frame[y:h, x:w]
                    self.motion_signal.emit( area_of_interest )
                    # self.queue.put( area_of_interest )
            else:
                motion_frame_count = 0
            
            if self.config['show_video']:
                frame_to_show = frame if not triggered else self.annotate_frame( frame=frame, rects=bounding_rectangles ) 
                resized_frame = imutils.resize( frame_to_show, width = 640 )
                #resized_frame = frame_to_show
                rgb_frame = cv2.cvtColor( resized_frame, cv2.COLOR_BGR2RGB )
                qimage = QtGui.QImage( rgb_frame.data, 
                                       rgb_frame.shape[1],
                                       rgb_frame.shape[0],
                                       QtGui.QImage.Format_RGB888 )
                self.frame_signal.emit( qimage )

            raw_capture.truncate( 0 )
            

    def contours_to_rectangles( self, contours=[] ):
        rects = []
        for c in contours:
            if cv2.contourArea(c) < self.config['minimum_area']:
                continue
            rects.append( cv2.boundingRect( c ) )
        return rects
            

    def enclosing_bounds( self, rects=[] ):
        top_x, top_y, bottom_x, bottom_y = None, None, None, None
        for r in rects:
            (x, y, w, h ) = r
            top_x = x if top_x is None or x < top_x else top_x
            top_y = y if top_y is None or y < top_y else top_y
            bottom_x = x+w if bottom_x is None or x+w > bottom_x else bottom_x
            bottom_y = y+h if bottom_y is None or y+h > bottom_y else bottom_y
        return (top_x, top_y, bottom_x, bottom_y)


    def annotate_frame( self, frame=None, rects=[] ):
        # loop over the contours
        annotated_frame = copy( frame )
        (x1, y1, x2, y2) = self.enclosing_bounds( rects=rects )
        cv2.rectangle( annotated_frame,
                       (x1, y1),
                       (x2, y2),
                       (255, 0, 0),
                       4 )
        for r in rects:
            # compute the bounding box for the contour
            (x, y, w, h) = r
            cv2.rectangle( annotated_frame,
                           (x, y),
                           (x + w, y + h),
                           (0, 255, 0),
                           1 )
        return annotated_frame


    def background_model_needs_initialising( self, frame=None ):
        if frame is None:
            return True
        elif self.background_average is None:
            logger.info( 'Building background model' )
            self.background_average = frame.copy().astype( 'float' )
            logger.debug( 'Built background model' )
            return True
        else:
            return False
        
    def greyscale_and_blur( self, frame ):
        '''Resize and convert to greyscale then apply gaussian blur'''
        grey = cv2.cvtColor( imutils.resize( frame, width=500 ), cv2.COLOR_BGR2GRAY )
        grey = cv2.cvtColor( frame, cv2.COLOR_BGR2GRAY )
        grey = cv2.GaussianBlur( grey, (21, 21), 0 )
        return grey
        
    def get_camera( self ):
        logger.debug( 'Preparing camera' )
        camera = PiCamera()
        camera.resolution = tuple( self.config['resolution'] )
        camera.framerate = self.config['frames_per_second']
        camera.hflip = self.config['flip_horizontal']
        camera.vflip = self.config['flip_vertical'] 
        return camera
        
    def prepare_camera( self, camera ):
        logger.info( 'Warming camera' )
        time.sleep( self.config['camera_warmup_time'] )
        logger.debug( 'Camera warm' )
