from PyQt5 import QtCore, QtGui

import cv2
import imutils
import logging
from datetime import datetime
from pathlib import Path

# haar cascade
face_detector = cv2.CascadeClassifier("/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt.xml")
# face_detector = cv2.CascadeClassifier("/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt2.xml")

logger = logging.getLogger( __name__ )

class FaceDetectorSignal( QtCore.QObject ):
    result = QtCore.pyqtSignal( QtGui.QImage )

class FaceDetector( QtCore.QRunnable ):
    'A threaded class which attempts to detect faces from a frame'

    
    def __init__(  self, config={}, image=None ):
        QtCore.QThread.__init__(self)
        logger.debug( 'Launching face detector' )
        self.face_signal = FaceDetectorSignal()
        self.config = config
        self.image = image
        
    #def run( self ):
        
    
    def run( self ):
        logger.debug( 'Starting analysis' )
        frame = self.image
        grey_image = cv2.cvtColor( frame, cv2.COLOR_BGR2GRAY )
        # detect faces in the frame
        faces = face_detector.detectMultiScale(
            grey_image,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=tuple( self.config.get( 'minimum_detection_area', [30,30] ) ),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        logger.info( 'Found {faces} face(s)'.format( faces=len( faces ) ) )

        # extract and save each face
        if self.config.get( 'save_image', False ):
            for i, (x,y,h,w) in enumerate( faces ):
                face = frame[y:y+h, x:x+w]
                face = imutils.resize( face, width=self.config.get( 'rescale', 50 ), inter=cv2.INTER_LANCZOS4)
                self.save_face( face, i )
                self.emit( face )
    
    def save_face( self, face, index ):
        location = Path( self.config.get( 'save_image_location', 'faces' ) )
        if not location.exists():
            location.mkdir()
            
        ts_str = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        cv2.imwrite( '{}/face{}-{}.jpg'.format( location.cwd(), ts_str, index ), face )
        
        
    def emit( self, face ):
        rgb_face = cv2.cvtColor( face, cv2.COLOR_BGR2RGB )
        qimage = QtGui.QImage( rgb_face.data, 
                               rgb_face.shape[1],
                               rgb_face.shape[0],
                               QtGui.QImage.Format_RGB888 )
        self.face_signal.result.emit( qimage )
