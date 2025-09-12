# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'settings.ui'
##
## Created by: Qt User Interface Compiler version 6.9.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QGridLayout, QLabel,
    QSizePolicy, QTabWidget, QVBoxLayout, QWidget)

class Ui_SettingsDialog(object):
    def setupUi(self, SettingsDialog):
        if not SettingsDialog.objectName():
            SettingsDialog.setObjectName(u"SettingsDialog")
        SettingsDialog.resize(360, 240)
        self.verticalLayout = QVBoxLayout(SettingsDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tabWidget = QTabWidget(SettingsDialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab_video = QWidget()
        self.tab_video.setObjectName(u"tab_video")
        self.gridLayout = QGridLayout(self.tab_video)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_device = QLabel(self.tab_video)
        self.label_device.setObjectName(u"label_device")

        self.gridLayout.addWidget(self.label_device, 0, 0, 1, 1)

        self.label_format = QLabel(self.tab_video)
        self.label_format.setObjectName(u"label_format")

        self.gridLayout.addWidget(self.label_format, 2, 0, 1, 1)

        self.combo_box_resolution = QComboBox(self.tab_video)
        self.combo_box_resolution.setObjectName(u"combo_box_resolution")

        self.gridLayout.addWidget(self.combo_box_resolution, 1, 1, 1, 1)

        self.combo_box_device = QComboBox(self.tab_video)
        self.combo_box_device.setObjectName(u"combo_box_device")
        self.combo_box_device.setMouseTracking(False)

        self.gridLayout.addWidget(self.combo_box_device, 0, 1, 1, 1)

        self.label_resolution = QLabel(self.tab_video)
        self.label_resolution.setObjectName(u"label_resolution")

        self.gridLayout.addWidget(self.label_resolution, 1, 0, 1, 1)

        self.combo_box_format = QComboBox(self.tab_video)
        self.combo_box_format.setObjectName(u"combo_box_format")

        self.gridLayout.addWidget(self.combo_box_format, 2, 1, 1, 1)

        self.tabWidget.addTab(self.tab_video, "")
        self.tab_controller = QWidget()
        self.tab_controller.setObjectName(u"tab_controller")
        self.gridLayout_2 = QGridLayout(self.tab_controller)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_controller_type = QLabel(self.tab_controller)
        self.label_controller_type.setObjectName(u"label_controller_type")

        self.gridLayout_2.addWidget(self.label_controller_type, 0, 0, 1, 1)

        self.combo_box_controller_type = QComboBox(self.tab_controller)
        self.combo_box_controller_type.addItem(u"ch9329")
        self.combo_box_controller_type.addItem(u"kvm-card-mini")
        self.combo_box_controller_type.setObjectName(u"combo_box_controller_type")

        self.gridLayout_2.addWidget(self.combo_box_controller_type, 0, 1, 1, 1)

        self.label_com_port = QLabel(self.tab_controller)
        self.label_com_port.setObjectName(u"label_com_port")

        self.gridLayout_2.addWidget(self.label_com_port, 1, 0, 1, 1)

        self.combo_box_com_port = QComboBox(self.tab_controller)
        self.combo_box_com_port.addItem("")
        self.combo_box_com_port.setObjectName(u"combo_box_com_port")
        self.combo_box_com_port.setEditable(True)

        self.gridLayout_2.addWidget(self.combo_box_com_port, 1, 1, 1, 1)

        self.label_baud_rate = QLabel(self.tab_controller)
        self.label_baud_rate.setObjectName(u"label_baud_rate")

        self.gridLayout_2.addWidget(self.label_baud_rate, 2, 0, 1, 1)

        self.combo_box_baud_rate = QComboBox(self.tab_controller)
        self.combo_box_baud_rate.addItem(u"9600")
        self.combo_box_baud_rate.addItem(u"14400")
        self.combo_box_baud_rate.addItem(u"19200")
        self.combo_box_baud_rate.addItem(u"38400")
        self.combo_box_baud_rate.addItem(u"57600")
        self.combo_box_baud_rate.addItem(u"115200")
        self.combo_box_baud_rate.setObjectName(u"combo_box_baud_rate")
        self.combo_box_baud_rate.setEditable(True)
        self.combo_box_baud_rate.setCurrentText(u"9600")

        self.gridLayout_2.addWidget(self.combo_box_baud_rate, 2, 1, 1, 1)

        self.tabWidget.addTab(self.tab_controller, "")
        self.tab_connection = QWidget()
        self.tab_connection.setObjectName(u"tab_connection")
        self.verticalLayout_2 = QVBoxLayout(self.tab_connection)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.check_box_auto_connect = QCheckBox(self.tab_connection)
        self.check_box_auto_connect.setObjectName(u"check_box_auto_connect")

        self.verticalLayout_2.addWidget(self.check_box_auto_connect)

        self.tabWidget.addTab(self.tab_connection, "")

        self.verticalLayout.addWidget(self.tabWidget)

        self.button_box = QDialogButtonBox(SettingsDialog)
        self.button_box.setObjectName(u"button_box")
        self.button_box.setOrientation(Qt.Orientation.Horizontal)
        self.button_box.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.button_box)


        self.retranslateUi(SettingsDialog)
        self.button_box.accepted.connect(SettingsDialog.accept)
        self.button_box.rejected.connect(SettingsDialog.reject)

        self.tabWidget.setCurrentIndex(0)
        self.combo_box_com_port.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(SettingsDialog)
    # setupUi

    def retranslateUi(self, SettingsDialog):
        SettingsDialog.setWindowTitle(QCoreApplication.translate("SettingsDialog", u"Settings", None))
        self.label_device.setText(QCoreApplication.translate("SettingsDialog", u"Device", None))
        self.label_format.setText(QCoreApplication.translate("SettingsDialog", u"Format", None))
        self.label_resolution.setText(QCoreApplication.translate("SettingsDialog", u"Resolution", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_video), QCoreApplication.translate("SettingsDialog", u"Video", None))
        self.label_controller_type.setText(QCoreApplication.translate("SettingsDialog", u"Controller type", None))

        self.label_com_port.setText(QCoreApplication.translate("SettingsDialog", u"COM port :", None))
        self.combo_box_com_port.setItemText(0, QCoreApplication.translate("SettingsDialog", u"auto", None))

        self.label_baud_rate.setText(QCoreApplication.translate("SettingsDialog", u"Baud rate:", None))

        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_controller), QCoreApplication.translate("SettingsDialog", u"Controller", None))
        self.check_box_auto_connect.setText(QCoreApplication.translate("SettingsDialog", u"Auto Connect", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_connection), QCoreApplication.translate("SettingsDialog", u"Connection", None))
    # retranslateUi

