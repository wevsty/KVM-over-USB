# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'controller_device_setup.ui'
##
## Created by: Qt User Interface Compiler version 6.7.3
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialog,
    QDialogButtonBox, QHBoxLayout, QLabel, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_ControllerDeviceSetupDialog(object):
    def setupUi(self, ControllerDeviceSetupDialog):
        if not ControllerDeviceSetupDialog.objectName():
            ControllerDeviceSetupDialog.setObjectName(u"ControllerDeviceSetupDialog")
        ControllerDeviceSetupDialog.resize(240, 100)
        self.verticalLayout = QVBoxLayout(ControllerDeviceSetupDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_com_select = QLabel(ControllerDeviceSetupDialog)
        self.label_com_select.setObjectName(u"label_com_select")

        self.horizontalLayout.addWidget(self.label_com_select)

        self.combobox_com_port = QComboBox(ControllerDeviceSetupDialog)
        self.combobox_com_port.setObjectName(u"combobox_com_port")

        self.horizontalLayout.addWidget(self.combobox_com_port)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_baud_rate = QLabel(ControllerDeviceSetupDialog)
        self.label_baud_rate.setObjectName(u"label_baud_rate")

        self.horizontalLayout_4.addWidget(self.label_baud_rate)

        self.combobox_baud = QComboBox(ControllerDeviceSetupDialog)
        self.combobox_baud.addItem("")
        self.combobox_baud.addItem("")
        self.combobox_baud.addItem("")
        self.combobox_baud.addItem("")
        self.combobox_baud.addItem("")
        self.combobox_baud.addItem("")
        self.combobox_baud.setObjectName(u"combobox_baud")
        self.combobox_baud.setEditable(True)

        self.horizontalLayout_4.addWidget(self.combobox_baud)


        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.buttonBox = QDialogButtonBox(ControllerDeviceSetupDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(ControllerDeviceSetupDialog)
        self.buttonBox.accepted.connect(ControllerDeviceSetupDialog.accept)
        self.buttonBox.rejected.connect(ControllerDeviceSetupDialog.reject)

        QMetaObject.connectSlotsByName(ControllerDeviceSetupDialog)
    # setupUi

    def retranslateUi(self, ControllerDeviceSetupDialog):
        ControllerDeviceSetupDialog.setWindowTitle(QCoreApplication.translate("ControllerDeviceSetupDialog", u"Controller device setup", None))
        self.label_com_select.setText(QCoreApplication.translate("ControllerDeviceSetupDialog", u"Select COM port :", None))
        self.label_baud_rate.setText(QCoreApplication.translate("ControllerDeviceSetupDialog", u"Baud :", None))
        self.combobox_baud.setItemText(0, QCoreApplication.translate("ControllerDeviceSetupDialog", u"9600", None))
        self.combobox_baud.setItemText(1, QCoreApplication.translate("ControllerDeviceSetupDialog", u"14400", None))
        self.combobox_baud.setItemText(2, QCoreApplication.translate("ControllerDeviceSetupDialog", u"19200", None))
        self.combobox_baud.setItemText(3, QCoreApplication.translate("ControllerDeviceSetupDialog", u"38400", None))
        self.combobox_baud.setItemText(4, QCoreApplication.translate("ControllerDeviceSetupDialog", u"57600", None))
        self.combobox_baud.setItemText(5, QCoreApplication.translate("ControllerDeviceSetupDialog", u"115200", None))

    # retranslateUi

