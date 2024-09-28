# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'custom_key.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QHBoxLayout,
    QKeySequenceEdit, QPushButton, QSizePolicy, QWidget)

class Ui_CustomKeyDialog(object):
    def setupUi(self, CustomKeyDialog):
        if not CustomKeyDialog.objectName():
            CustomKeyDialog.setObjectName(u"CustomKeyDialog")
        CustomKeyDialog.setWindowModality(Qt.WindowModality.NonModal)
        CustomKeyDialog.resize(400, 145)
        CustomKeyDialog.setMinimumSize(QSize(400, 145))
        CustomKeyDialog.setMaximumSize(QSize(400, 145))
        self.gridLayout = QGridLayout(CustomKeyDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.push_button_ctrl = QPushButton(CustomKeyDialog)
        self.push_button_ctrl.setObjectName(u"push_button_ctrl")
        self.push_button_ctrl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.push_button_ctrl.setCheckable(True)
        self.push_button_ctrl.setChecked(False)
        self.push_button_ctrl.setAutoDefault(False)
        self.push_button_ctrl.setFlat(False)

        self.gridLayout.addWidget(self.push_button_ctrl, 0, 0, 1, 1)

        self.push_button_shift = QPushButton(CustomKeyDialog)
        self.push_button_shift.setObjectName(u"push_button_shift")
        self.push_button_shift.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.push_button_shift.setCheckable(True)
        self.push_button_shift.setAutoDefault(False)

        self.gridLayout.addWidget(self.push_button_shift, 0, 1, 1, 1)

        self.push_button_meta = QPushButton(CustomKeyDialog)
        self.push_button_meta.setObjectName(u"push_button_meta")
        self.push_button_meta.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.push_button_meta.setCheckable(True)
        self.push_button_meta.setAutoDefault(False)

        self.gridLayout.addWidget(self.push_button_meta, 1, 0, 1, 1)

        self.push_button_tab = QPushButton(CustomKeyDialog)
        self.push_button_tab.setObjectName(u"push_button_tab")
        self.push_button_tab.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.push_button_tab.setCheckable(True)
        self.push_button_tab.setAutoDefault(False)

        self.gridLayout.addWidget(self.push_button_tab, 1, 1, 1, 1)

        self.push_button_prtsc = QPushButton(CustomKeyDialog)
        self.push_button_prtsc.setObjectName(u"push_button_prtsc")
        self.push_button_prtsc.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.push_button_prtsc.setCheckable(True)
        self.push_button_prtsc.setChecked(False)
        self.push_button_prtsc.setAutoDefault(False)

        self.gridLayout.addWidget(self.push_button_prtsc, 1, 2, 1, 1)

        self.key_sequence_edit = QKeySequenceEdit(CustomKeyDialog)
        self.key_sequence_edit.setObjectName(u"key_sequence_edit")

        self.gridLayout.addWidget(self.key_sequence_edit, 2, 0, 1, 2)

        self.push_button_alt = QPushButton(CustomKeyDialog)
        self.push_button_alt.setObjectName(u"push_button_alt")
        self.push_button_alt.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.push_button_alt.setCheckable(True)
        self.push_button_alt.setAutoDefault(False)

        self.gridLayout.addWidget(self.push_button_alt, 0, 2, 1, 1)

        self.push_button_clear = QPushButton(CustomKeyDialog)
        self.push_button_clear.setObjectName(u"push_button_clear")
        self.push_button_clear.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.gridLayout.addWidget(self.push_button_clear, 2, 2, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.push_button_send = QPushButton(CustomKeyDialog)
        self.push_button_send.setObjectName(u"push_button_send")
        self.push_button_send.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.horizontalLayout_2.addWidget(self.push_button_send)

        self.push_button_save = QPushButton(CustomKeyDialog)
        self.push_button_save.setObjectName(u"push_button_save")
        self.push_button_save.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.horizontalLayout_2.addWidget(self.push_button_save)


        self.gridLayout.addLayout(self.horizontalLayout_2, 3, 0, 1, 3)

        QWidget.setTabOrder(self.push_button_ctrl, self.push_button_shift)
        QWidget.setTabOrder(self.push_button_shift, self.key_sequence_edit)

        self.retranslateUi(CustomKeyDialog)

        self.push_button_ctrl.setDefault(False)


        QMetaObject.connectSlotsByName(CustomKeyDialog)
    # setupUi

    def retranslateUi(self, CustomKeyDialog):
        CustomKeyDialog.setWindowTitle(QCoreApplication.translate("CustomKeyDialog", u"Custom Key", None))
        self.push_button_ctrl.setText(QCoreApplication.translate("CustomKeyDialog", u"Ctrl", None))
        self.push_button_shift.setText(QCoreApplication.translate("CustomKeyDialog", u"Shift", None))
        self.push_button_meta.setText(QCoreApplication.translate("CustomKeyDialog", u"Meta", None))
        self.push_button_tab.setText(QCoreApplication.translate("CustomKeyDialog", u"Tab", None))
        self.push_button_prtsc.setText(QCoreApplication.translate("CustomKeyDialog", u"Prt Sc", None))
        self.push_button_alt.setText(QCoreApplication.translate("CustomKeyDialog", u"Alt", None))
#if QT_CONFIG(tooltip)
        self.push_button_clear.setToolTip(QCoreApplication.translate("CustomKeyDialog", u"Clear Selection", None))
#endif // QT_CONFIG(tooltip)
        self.push_button_clear.setText(QCoreApplication.translate("CustomKeyDialog", u"Clear", None))
        self.push_button_send.setText(QCoreApplication.translate("CustomKeyDialog", u"Send", None))
        self.push_button_save.setText(QCoreApplication.translate("CustomKeyDialog", u"Save", None))
    # retranslateUi

