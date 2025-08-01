# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'indicator_lights.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
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
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QHBoxLayout,
    QPushButton, QSizePolicy, QWidget)

class Ui_IndicatorLightsDialog(object):
    def setupUi(self, IndicatorLightsDialog):
        if not IndicatorLightsDialog.objectName():
            IndicatorLightsDialog.setObjectName(u"IndicatorLightsDialog")
        IndicatorLightsDialog.setWindowModality(Qt.WindowModality.WindowModal)
        IndicatorLightsDialog.resize(400, 45)
        IndicatorLightsDialog.setMinimumSize(QSize(400, 45))
        IndicatorLightsDialog.setMaximumSize(QSize(400, 45))
        self.gridLayout = QGridLayout(IndicatorLightsDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.push_button_num_lock = QPushButton(IndicatorLightsDialog)
        self.push_button_num_lock.setObjectName(u"push_button_num_lock")
        self.push_button_num_lock.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.push_button_num_lock.setCheckable(True)

        self.horizontalLayout.addWidget(self.push_button_num_lock)

        self.push_button_caps_lock = QPushButton(IndicatorLightsDialog)
        self.push_button_caps_lock.setObjectName(u"push_button_caps_lock")
        self.push_button_caps_lock.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.push_button_caps_lock.setCheckable(True)

        self.horizontalLayout.addWidget(self.push_button_caps_lock)

        self.push_button_scroll_lock = QPushButton(IndicatorLightsDialog)
        self.push_button_scroll_lock.setObjectName(u"push_button_scroll_lock")
        self.push_button_scroll_lock.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.push_button_scroll_lock.setCheckable(True)

        self.horizontalLayout.addWidget(self.push_button_scroll_lock)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)


        self.retranslateUi(IndicatorLightsDialog)

        QMetaObject.connectSlotsByName(IndicatorLightsDialog)
    # setupUi

    def retranslateUi(self, IndicatorLightsDialog):
        IndicatorLightsDialog.setWindowTitle(QCoreApplication.translate("IndicatorLightsDialog", u"Indicator Lights", None))
        self.push_button_num_lock.setText(QCoreApplication.translate("IndicatorLightsDialog", u"Num Lock", None))
        self.push_button_caps_lock.setText(QCoreApplication.translate("IndicatorLightsDialog", u"Caps Lock", None))
        self.push_button_scroll_lock.setText(QCoreApplication.translate("IndicatorLightsDialog", u"Scroll Lock", None))
    # retranslateUi

