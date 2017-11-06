import argparse
import json
import logging

from detector.face_detector import FaceDetector
from detector.motion_detector import MotionDetector


from PyQt5 import QtWidgets, QtGui, QtCore
import sys
import mainwindow

from PyQt5.QtWidgets import QMainWindow

logger = logging.getLogger( __name__ )

class Security( QMainWindow, mainwindow.Ui_MainWindow ):
    def __init__(self, config={} ):
        super( Security, self ).__init__()

        # Set up the user interface from Designer.
        self.setupUi(self)
        
        self.face_model = QtGui.QStandardItemModel( self.face_list_view )
        self.face_list_view.setModel( self.face_model )
        
        self.face_detector_threadpool = QtCore.QThreadPool()
        logger.info( 'Starting face detector threadpool with {threads} thread(s)'.format( threads=self.face_detector_threadpool.maxThreadCount() ) )
        
        self.motion_detector = MotionDetector( config=configuration.get( 'motion_detector', {} ) )
        self.motion_detector.start()
        self.motion_detector.frame_signal.connect( self.handle_frame_trigger )
        self.motion_detector.motion_signal.connect( self.handle_motion_trigger )

    def handle_frame_trigger( self, qimage ):
        qpm = QtGui.QPixmap.fromImage( qimage )
        self.image_label.setPixmap( qpm )
        
    def handle_motion_trigger( self, image ):
        face_detector = FaceDetector( config=configuration.get( 'face_detector', {} ), image=image )
        face_detector.face_signal.result.connect( self.handle_face_trigger )
        self.face_detector_threadpool.start( face_detector )
        
    def handle_face_trigger( self, face ):
        logger.info( 'Face detector reports face present' )
        list_item_icon = QtGui.QIcon( QtGui.QPixmap.fromImage( face ) )
        list_item = QtGui.QStandardItem( list_item_icon, 'Motion' )
        self.face_model.insertRow( 0, list_item )
        



def main( configuration ):
    app = QtWidgets.QApplication( sys.argv )
    security = Security( config=configuration )
    security.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    logging.basicConfig( level=logging.DEBUG )
    logger = logging.getLogger( __name__ )
    
    # parse the command line arguments
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument( '-c', 
                             '--conf', 
                             required=True,
                             help='path to the JSON configuration file')
    arguments = vars( arg_parser.parse_args() )

    # load the configuration file -- json format
    configuration = json.load( open( arguments['conf'] ) )
    main( configuration )
