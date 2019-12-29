import sys
from collections import namedtuple
from PyQt5.QtGui import qRgb
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QColor, QImage, QPalette
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, qApp, QMessageBox
from PyQt5.QtWidgets import QFileDialog, QLabel, QPushButton, QSlider, QCheckBox
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import Qt, QSize, QByteArray, QBuffer, QIODevice

from utils.targetbuild import *
from utils.metafile import *
from configs.conf import *

import os
import json
import requests
import random
import base64
#import pdb


# TODO: make a Singleton
class ImageClickEvents(QMainWindow):
    '''
    ImageClickEvents: set points
    init:
        recep_field_size - receptive field size of neural network in pixels
            it defines the size of square on target image
        screen_width: screen width of cell image in application's window
        screen_height: screen height of cell image in application's window
        isImageLoaded: is cell image loaded?
    '''

    def __init__(self, recep_field_size, screen_width, screen_height, isImageLoaded=False):
        super(ImageClickEvents, self).__init__()

        self.server_port = 1106
        self.server_url = 'http://localhost:' + str(self.server_port) + '/jsonrpc'
        self.metafileobj = None#meta file class

        self.Coord = namedtuple('Coordinates', ['x', 'y'])
        self.isImageLoaded = False
        self.isDrawingRect = False
        self.newRectCoord = None

        self.isNeuralImage = False#показываем ли мы сейчас изображение от нейронки
        self.haveWeNeuralImage = False#чтобы каждый раз не запрашивать изображение
        self.neuralImage = None

        self.isDraged = False
        self.isMoving = False
        self.x0 = 0
        self.y0 = 0
        self.xScaled = 1.0
        self.isNeedResize = False
        # местоположения курсора мыши для drag
        self.cursorX = 0
        self.cursorY = 0

        self.recFieldSize = recep_field_size

        self.lbl = QLabel(self)
        #self.cellPixmap = QPixmap(screen_width, screen_height)
        self.cellPixmapUnscaled = QPixmap(screen_width // 1.25, screen_height)
        self.pixmapHolder =QPixmap(screen_width // 1.25, screen_height)

        self.pointsArray = []

        self.imageWidth = screen_width // 1.25
        self.imageHeight = screen_height
        self.resize(QSize(screen_width, screen_height))
        self.min_widget_size = 110

        # const codes of button in qt
        # here's mouse buttons:
        self.NoneButton = 0x00000000
        self.LeftButton = 0x00000001
        self.RightButton = 0x00000002
        self.AllButtons = 0x07ffffff

        self.initGUI()

    def initGUI(self):
        self.resizableWidgets = []
        self.lbl.setGeometry(0, 0, self.imageWidth, self.imageHeight)

        #vbox = QVBoxLayout()
        #vbox.addStretch(1)
        #hbox = QHBoxLayout()

        self.openImageBtn = QPushButton('&Открыть изображение', self)
        self.openImageBtn.setGeometry(self.imageWidth+20, 50, 150, 25)
        self.openImageBtn.clicked.connect(self.showOpenFileDialog)
        self.resizableWidgets.append(self.openImageBtn)
        #vbox.addWidget(self.openImageBtn)

        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.move(self.imageWidth+20, 100)
        self.slider.setMinimum(0)
        self.slider.setMaximum(500)
        self.slider.setValue(self.recFieldSize)
        self.slider.valueChanged.connect(self.changeSliderValueEvent)
        self.resizableWidgets.append(self.slider)
        #vbox.addWidget(self.slider)

        self.showReceptiveFieldsCheckBox = QCheckBox('&Show mask', self)
        self.showReceptiveFieldsCheckBox.move(self.imageWidth+20, 135)
        self.showReceptiveFieldsCheckBox.stateChanged.connect(self.changeMaskShowing)
        self.resizableWidgets.append(self.showReceptiveFieldsCheckBox)
        #vbox.addWidget(self.showReceptiveFieldsCheckBox)

        self.saveImageBtn = QPushButton('&Сохранить изображение', self)
        self.saveImageBtn.setGeometry(self.imageWidth+20, 175, 130, 25)
        self.saveImageBtn.clicked.connect(self.showSaveFileDialog)
        self.resizableWidgets.append(self.saveImageBtn)
        #vbox.addWidget(self.saveImageBtn)

        self.sendImagesBtn = QPushButton('&Отправить изображение', self)
        self.sendImagesBtn.setGeometry(self.imageWidth+20, 225, 130, 25)
        self.sendImagesBtn.clicked.connect(self.sendOneImage)
        self.resizableWidgets.append(self.sendImagesBtn)
        #vbox.addWidget(self.sendImagesBtn)

        self.neuralnetworkBtn = QPushButton('&Запросить изображение', self)#from nn
        self.neuralnetworkBtn.setGeometry(self.imageWidth+20, 275, 130, 25)
        self.neuralnetworkBtn.clicked.connect(self.sendNNrequest)
        self.resizableWidgets.append(self.neuralnetworkBtn)

        self.neuralCellCount = QLabel('Предсказанное количество: 0', self)
        self.neuralCellCount.setGeometry(self.imageWidth+20, 325, 130, 25)
        self.resizableWidgets.append(self.neuralCellCount)

        #vbox.addStretch(5)

        self.lbl.setGeometry(0, 0, self.imageWidth, self.imageHeight)
        #hbox.addStretch(1)
        #hbox.addWidget(self.lbl)
        #hbox.addStretch(1)
        #hbox.addLayout(vbox)

        #widget = QWidget()
        #widget.setLayout(hbox)
        #self.setCentralWidget(widget)

        self.update()
        self.show()

    def resizeEvent(self, event):
        if self.isNeedResize:
            newsize = event.size()
            oldsize = event.oldSize()
            if oldsize.height() == 10 or oldsize.width() == 10:
                return
            if oldsize.width() == newsize.width() and oldsize.height() == newsize.height():
                return

            self.imageWidth = newsize.width() // 1.25
            self.imageHeight = newsize.height() - 18

            widget_size = newsize.width()-self.imageWidth-50
            widget_size = widget_size if widget_size >= self.min_widget_size else self.min_widget_size
            if newsize.width() < self.imageWidth + widget_size + 50:
                self.resize(self.imageWidth + widget_size + 50, newsize.height())

            dw = newsize.width() - oldsize.width()
            dh =  newsize.height() - oldsize.height()


            #print(self.imageWidth, self.imageHeight)
            ind = 1
            for w in self.resizableWidgets:
                w.setGeometry(self.imageWidth+25, w.y(),
                              widget_size, w.height())
                #w.move(self.imageWidth+25, int(self.imageHeight*0.125*ind))
                ind += 1
                #w.move(self.imageWidth+25, w.y())
        else:
            self.isNeedResize = True

    def wheelEvent(self, event):
        numPixels = event.pixelDelta()
        numDegrees = event.angleDelta()
        dxs = 0.0
        if not numPixels.isNull():
            dxs = 0.1*signum(numPixels.y())
        elif not numDegrees.isNull():
            dxs = 0.1*signum(numDegrees.y())
        #if self.xScaled < 0.5:
        #    self.xScaled = 0.5
        if self.cellPixmapUnscaled.width() * (self.xScaled + dxs) >= self.imageWidth:
            self.xScaled += dxs
        elif self.xScaled >= 10.0:
            self.xScaled = 10.0

        print(self.xScaled)
        #self.lbl.setPixmap(QPixmap(1, 1))


    def mousePressEvent(self, event):
        btn = event.button()
        if self.isImageLoaded and btn == self.LeftButton:
            self.isDraged = True
            self.cursorX = event.x()
            self.cursorY = event.y()

    def mouseMoveEvent(self, event):
        if self.isDraged and self.isImageLoaded:
            self.isMoving = True
            self.x0 -= event.x() - self.cursorX
            if self.x0 < 0:
                self.x0 = 0
            else:
                if self.x0 + self.imageWidth > self.cellPixmap.width():
                    self.x0 = self.cellPixmap.width() - self.imageWidth


            self.y0 -= event.y() - self.cursorY
            if self.y0 < 0:
                self.y0 = 0
            else:
                if self.y0 + self.imageHeight > self.cellPixmap.height():
                    self.y0 = self.cellPixmap.height() - self.imageHeight

            self.cursorX = event.x()
            self.cursorY = event.y()

    def mouseReleaseEvent(self, QMouseEvent):
        if not self.isImageLoaded:
            return

        #pdb.set_trace()
        mx, my = QMouseEvent.pos().x(), QMouseEvent.pos().y()
        if mx > self.imageWidth or my > self.imageHeight:
            return

        pressedButton = QMouseEvent.button()

        if not self.isImageLoaded:
            return
        if self.isDraged and self.isMoving:
            self.isDraged = False
            self.isMoving = False
            return
        if not self.isDrawingRect:
            self.isDraged = False

        imgX = (self.x0 + mx) // self.xScaled
        imgY = (self.y0 + my) // self.xScaled

        if pressedButton == self.LeftButton:
            self.pointsArray.append(self.Coord(imgX, imgY))
            self.newRectCoord = self.Coord(x=mx, y=my)

            #update time of last changes
            self.metafileobj.newIimeChanged()

        elif pressedButton == self.RightButton:
            ind = get_nearest(self.Coord(imgX, imgY), self.pointsArray, self.recFieldSize // 2)
            if ind == -1:
                return

            del self.pointsArray[ind]
            self.update()


    def showOpenFileDialog(self):
        file_name = QFileDialog.getOpenFileName(self, 'Open image', '.')[0]
        print(file_name)
        if file_name == '':
            return

        file_name, self.metafileobj = getOpeningFilename(file_name)
        self.pointsArray = []
        for coord in self.metafileobj.pointsList:
            self.pointsArray.append(self.Coord(x=coord[0], y=coord[1]))

        self.cellPixmapUnscaled = QPixmap(file_name)
        self.cellPixmap = self.cellPixmapUnscaled.copy()
        self.isNeuralImage = False
        self.haveWeNeuralImage = False

        self.isImageLoaded = True
        self.x0 = 0
        self.y0 = 0
        self.xe = min(self.cellPixmap.width(), self.imageWidth)
        self.ye = min(self.cellPixmap.height(), self.imageHeight)
        self.xScaled = 1.0

        self.min_widget_size = self.width() * 0.2 - 50

        self.update()

    def showSaveFileDialog(self):
        if not self.isImageLoaded:
            nope = QMessageBox()
            nope.setText("Зарузите избражение")
            nope.exec()
            return

        file_name = QFileDialog.getSaveFileName(self, 'Save image', '.')[0]
        if file_name == '':
            return

        if file_name[-5:] != '.tiff':
            file_name += '.tiff'

        saving_image = self.getMarkedImage()

        saving_image.save(file_name, 'PNG')
        self.metafileobj.setOutFilename(file_name)
        self.metafileobj.setPoints(self.pointsArray)
        self.metafileobj.toJSON()

    def changeMaskShowing(self, event):
        self.isDrawingRect = not self.isDrawingRect

    def changeSliderValueEvent(self, value):
        self.recFieldSize = value

    def getMarkedImage(self):
        marked_image = QPixmap.toImage(self.cellPixmapUnscaled)
        # draw dots on saving image
        green = qRgb(0, 255, 0)
        for point in self.pointsArray:
            marked_image.setPixel(point.x, point.y, green)

        return marked_image

    def makeErrMessage(text):
        nope = QMessageBox()
        nope.setText(text)
        nope.exec()

    def paintEvent(self, event):
        unscaledWidth = self.cellPixmapUnscaled.width()
        unscaledHeight = self.cellPixmapUnscaled.height()

        painter = QPainter()

        #get unscaled pixmap without green rectangles
        self.cellPixmap = self.cellPixmapUnscaled.copy()
        #draw rectangles
        painter.begin(self.cellPixmap)
        if self.isDrawingRect:
            painter.setBrush(QColor(0, 255, 0, 100))
            halfRFS = self.recFieldSize // 2
            for point in self.pointsArray:
                painter.drawRect(point.x - halfRFS, point.y - halfRFS,
                                 self.recFieldSize, self.recFieldSize)
            # self.isDrawingRect = True

        painter.end()

        self.cellPixmap = self.cellPixmap.scaled(self.xScaled * unscaledWidth,
                                                 self.xScaled * unscaledHeight,
                                                 Qt.KeepAspectRatioByExpanding)

        #self.pixmapHolder = self.pixmapHolder.scaled(self.imageWidth, self.imageHeight)
        self.pixmapHolder = QPixmap(self.imageWidth, self.imageHeight)
        painter.begin(self.pixmapHolder)
        right_w = min(self.imageWidth, self.cellPixmap.width())
        right_h = min(self.imageHeight, self.cellPixmap.height())

        #because of asynchronous painting condition assignment
        # at the mouseMoveEvent func wouldn't keeps out
        self.x0 = self.x0 if self.x0 >= 0 else 0
        self.y0 = self.y0 if self.y0 >= 0 else 0

        screenPartWidth = min(self.imageWidth, self.cellPixmap.width())#*self.xScaled)
        screenPartHeight = min(self.imageHeight, self.cellPixmap.height())#*self.xScaled)

        painter.drawPixmap(0, 0, screenPartWidth, screenPartHeight, self.cellPixmap,
                           self.x0, self.y0, right_w, right_h)
        painter.end()

        #set pixmap, and resize Label
        if self.isImageLoaded:
            self.lbl.resize(self.imageWidth, self.imageHeight)
            self.lbl.setPixmap(self.pixmapHolder)
            height = self.pixmapHolder.height()
            width = self.pixmapHolder.width()
            #self.lbl.resize(min(width, self.imageWidth), min(height, self.imageHeight))

            '''
            #move label to the center of screen
            start_x = 0
            start_y = 0
            if width < self.imageWidth:
                start_x = (self.imageWidth - width) / 2
            if height < self.imageHeight:
                start_y = (self.imageHeight - height) / 2

            self.lbl.move(start_x, start_y)
            '''
        super().paintEvent(event)

    def sendOneImage(self):
        if not self.isImageLoaded:
            self.makeErrMessage("Зарузите избражение")

        #get pixamp bytes in tiff extension
        original_img_bytes = QByteArray()
        original_img_buff = QBuffer(original_img_bytes)
        original_img_buff.open(QIODevice.WriteOnly)
        extention = os.path.splitext(self.metafileobj.origFilename)[1][1:]
        self.cellPixmapUnscaled.save(original_img_buff, extention)
        original_img_buff.close()
        #marked image
        mmarked_img_bytes = QByteArray()
        marked_img_buff = QBuffer(mmarked_img_bytes)
        marked_img_buff.open(QIODevice.WriteOnly)
        marked_img = self.getMarkedImage()
        marked_img.save(marked_img_buff, extention)
        marked_img_buff.close()

        self.metafileobj.setPoints(self.pointsArray)

        payload = {
            'id': str(client_config['id']),
            'code': ReqCodes.NEW_IMAGES._value_,
            'count': 1,
            'data': [{
                'metafile': str(self.metafileobj.getDict()),
                'originalImage': str(base64.b64encode(original_img_bytes.data()), 'utf-8'),
                'markedImage': str(base64.b64encode(mmarked_img_bytes.data()), 'utf-8')
            }],
            'random_seed': random.randint(0, 999999999)
        }

        json_data = json.dumps(payload)
        try:
            response = requests.post(client_config['url'], data=json_data, headers=client_config['headers']).json()
            print(response)
        except:
            self.makeErrMessage("Произшала ошибка при взаимодействии с сервером, попробуйте позже")
        finally:
            del original_img_bytes
            del original_img_buff
            del marked_img
            del mmarked_img_bytes
            del marked_img_buff
            del json_data

    def sendNNrequest(self):
        # get pixamp bytes in tiff extension
        original_img_bytes = QByteArray()
        original_img_buff = QBuffer(original_img_bytes)
        original_img_buff.open(QIODevice.WriteOnly)
        extention = os.path.splitext(self.metafileobj.origFilename)[1][1:]
        self.cellPixmapUnscaled.save(original_img_buff, extention)
        original_img_buff.close()

        payload = {
            'id': str(client_config['id']),
            'code': ReqCodes.GET_NN_PREDICTION._value_,
            'image': str(base64.b64encode(original_img_bytes.data()), 'utf-8'),
            'random_seed': random.randint(0, 999999999)
        }

        json_data = json.dumps(payload)
        try:
            response = requests.post(client_config['url'], data=json_data, headers=client_config['headers'])
            pred_cells_num = response['cells_count']
            self.neuralCellCount.setText('Предсказанное количество: ' + pred_cells_num)
            self.neuralCellCount.show()
            neural_image_bytes = base64.b64decode(response['image'])
            self.neuralImage.loadFromData(neural_image_bytes, 'TIFF')
            self.isNeuralImage = True
            self.neuralImage.setText('Спрятать изображение')
            self.haveWeNeuralImage = True
        except:
            self.makeErrMessage("Произшала ошибка при взаимодействии с сервером, попробуйте позже.")
        finally:
            del original_img_bytes
            del original_img_buff
            del payload
            del json_data





if __name__ == '__main__':
    if not os.path.isfile(os.path.join('config.json')):
        print('config')
        req = {
            'code': ReqCodes.GET_ID._value_,
            'random_seed': random.randint(0, 999999999)
        }

        json_request = json.dumps(req)
        resp = requests.post(client_config['url'], data=json_request,
                             headers=client_config['headers']).json()
        client_config['id'] = resp['id']

        with open(os.path.join('config.json'), 'w') as config_file:
            config_file.write(json.dumps(client_config))
    else:
        with open(os.path.join('config.json'), 'r') as config_file:
            client_config = json.load(config_file)

    app = QApplication(sys.argv)
    image_click = ImageClickEvents(53, 875, 400, False)

    sys.exit(app.exec_())