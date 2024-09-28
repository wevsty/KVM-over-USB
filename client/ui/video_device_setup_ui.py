# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'video_device_setup.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QSizePolicy, QWidget)

class Ui_dialog(object):
    def setupUi(self, dialog):
        if not dialog.objectName():
            dialog.setObjectName(u"dialog")
        dialog.setWindowModality(Qt.NonModal)
        dialog.resize(340, 300)
        dialog.setMaximumSize(QSize(16777215, 300))
        dialog.setLayoutDirection(Qt.LeftToRight)
        self.formLayout = QFormLayout(dialog)
        self.formLayout.setObjectName(u"formLayout")
        self.label_device = QLabel(dialog)
        self.label_device.setObjectName(u"label_device")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.label_device)

        self.combo_box_device = QComboBox(dialog)
        self.combo_box_device.setObjectName(u"combo_box_device")
        self.combo_box_device.setMouseTracking(False)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.combo_box_device)

        self.label_resolution = QLabel(dialog)
        self.label_resolution.setObjectName(u"label_resolution")

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.label_resolution)

        self.combo_box_resolution = QComboBox(dialog)
        self.combo_box_resolution.setObjectName(u"combo_box_resolution")

        self.formLayout.setWidget(3, QFormLayout.FieldRole, self.combo_box_resolution)

        self.label_format = QLabel(dialog)
        self.label_format.setObjectName(u"label_format")

        self.formLayout.setWidget(4, QFormLayout.LabelRole, self.label_format)

        self.combo_box_format = QComboBox(dialog)
        self.combo_box_format.setObjectName(u"combo_box_format")

        self.formLayout.setWidget(4, QFormLayout.FieldRole, self.combo_box_format)

        self.label_audio_in = QLabel(dialog)
        self.label_audio_in.setObjectName(u"label_audio_in")

        self.formLayout.setWidget(5, QFormLayout.LabelRole, self.label_audio_in)

        self.combo_box_audio_in = QComboBox(dialog)
        self.combo_box_audio_in.setObjectName(u"combo_box_audio_in")
        self.combo_box_audio_in.setMouseTracking(False)

        self.formLayout.setWidget(5, QFormLayout.FieldRole, self.combo_box_audio_in)

        self.label_audio_out = QLabel(dialog)
        self.label_audio_out.setObjectName(u"label_audio_out")

        self.formLayout.setWidget(6, QFormLayout.LabelRole, self.label_audio_out)

        self.combo_box_audio_out = QComboBox(dialog)
        self.combo_box_audio_out.setObjectName(u"combo_box_audio_out")
        self.combo_box_audio_out.setMouseTracking(False)

        self.formLayout.setWidget(6, QFormLayout.FieldRole, self.combo_box_audio_out)

        self.label_tips = QLabel(dialog)
        self.label_tips.setObjectName(u"label_tips")

        self.formLayout.setWidget(7, QFormLayout.SpanningRole, self.label_tips)

        self.check_box_auto_connect = QCheckBox(dialog)
        self.check_box_auto_connect.setObjectName(u"check_box_auto_connect")

        self.formLayout.setWidget(8, QFormLayout.SpanningRole, self.check_box_auto_connect)

        self.check_box_audio_support = QCheckBox(dialog)
        self.check_box_audio_support.setObjectName(u"check_box_audio_support")

        self.formLayout.setWidget(9, QFormLayout.SpanningRole, self.check_box_audio_support)

        self.button_box = QDialogButtonBox(dialog)
        self.button_box.setObjectName(u"button_box")
        self.button_box.setOrientation(Qt.Horizontal)
        self.button_box.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.formLayout.setWidget(10, QFormLayout.SpanningRole, self.button_box)


        self.retranslateUi(dialog)
        self.button_box.accepted.connect(dialog.accept)
        self.button_box.rejected.connect(dialog.reject)

        QMetaObject.connectSlotsByName(dialog)
    # setupUi

    def retranslateUi(self, dialog):
        dialog.setWindowTitle(QCoreApplication.translate("dialog", u"Device setup", None))
        self.label_device.setText(QCoreApplication.translate("dialog", u"Device", None))
        self.label_resolution.setText(QCoreApplication.translate("dialog", u"Resolution", None))
        self.label_format.setText(QCoreApplication.translate("dialog", u"Format", None))
        self.label_audio_in.setText(QCoreApplication.translate("dialog", u"Audio IN", None))
        self.label_audio_out.setText(QCoreApplication.translate("dialog", u"Audio OUT", None))
        self.label_tips.setText(QCoreApplication.translate("dialog", u"* Audio routing only work in video recording", None))
        self.check_box_auto_connect.setText(QCoreApplication.translate("dialog", u"Auto Connect on startup", None))
        self.check_box_audio_support.setText(QCoreApplication.translate("dialog", u"Audio support", None))
    # retranslateUi

