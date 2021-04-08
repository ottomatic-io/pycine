from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg

# backward compatibility default is col-major in pyqtgraph so change
pg.setConfigOptions(imageAxisOrder="row-major")


class Cine_viewer(QtWidgets.QMainWindow):
    def __init__(self, frame_readers):
        super(Cine_viewer, self).__init__()

        if not isinstance(frame_readers, list):
            frame_readers = [frame_readers]
        self.frame_readers = frame_readers
        self.n_readers = len(frame_readers)

        self.setWindowTitle("Cine viewer")
        size = (640 * self.n_readers, 480)
        self.resize(*size)

        layout = QtWidgets.QGridLayout()

        # check that all fullsizes are the same
        full_size = frame_readers[0].full_size
        for i in range(1, self.n_readers):
            assert full_size == frame_readers[i].full_size
        # use only the start_index of the first one
        start_frame = frame_readers[0].start_index + 1

        self.image_views = []
        for i in range(self.n_readers):
            image_view = pg.ImageView()
            self.image_views.append(image_view)
            layout.addWidget(image_view, 0, i)

        if full_size == 1:
            for i in range(self.n_readers):
                image = self.frame_readers[i][0]
                self.image_views[i].setImage(image)
        else:
            frame_slider = QtWidgets.QSlider()
            frame_slider.setOrientation(QtCore.Qt.Horizontal)
            frame_slider.setMinimum(1)  # maybe change to FirstImageNo in cine file
            frame_slider.setMaximum(full_size)
            frame_slider.setTracking(True)  # call update on mouse drag
            frame_slider.setSingleStep(1)
            frame_slider.setValue(start_frame)
            self.frame_slider = frame_slider
            layout.addWidget(frame_slider, 1, 0, 1, self.n_readers)

            slider_label_left = QtWidgets.QLabel()
            slider_label_left.setText("{}".format(frame_slider.minimum()))
            layout.addWidget(slider_label_left, 2, 0, 1, self.n_readers)

            slider_label = QtWidgets.QLabel()
            slider_label.setAlignment(QtCore.Qt.AlignCenter)
            self.slider_label = slider_label
            layout.addWidget(slider_label, 2, 0, 1, self.n_readers)

            slider_label_right = QtWidgets.QLabel()
            slider_label_right.setText("{}".format(self.frame_slider.maximum()))
            slider_label_right.setAlignment(QtCore.Qt.AlignRight)
            layout.addWidget(slider_label_right, 2, 0, 1, self.n_readers)

            for i in range(self.n_readers):
                self.update_frame(start_frame, auto=True)
            # do this last to avoid double update with slider setValue
            frame_slider.valueChanged.connect(self.update_frame)

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def set_frame(self, frame_index):
        # indirectly call update frame
        self.frame_slider.setValue(frame_index)

    def update_frame(self, frame_index, auto=False):
        for i in range(self.n_readers):
            # keep the transform when changing images
            transform = self.image_views[i].imageItem.transform() if auto else None
            image = self.frame_readers[i][frame_index - 1]
            self.image_views[i].setImage(image, autoRange=auto, autoLevels=auto, transform=transform)
        self.slider_label.setText("Frame: {}".format(frame_index))


def view_cine(frame_readers):
    """Start an interactive viewer for a cine file

    Parameters
    ----------
    frame_readers : pycine.raw.Frame_reader or list of Frame_readers
        Object(s) for the cine_file to be viewed

    Returns
    -------
    None
    """
    app = QtWidgets.QApplication([])
    window = Cine_viewer(frame_readers)
    window.show()

    # Start the event loop.
    app.exec_()
