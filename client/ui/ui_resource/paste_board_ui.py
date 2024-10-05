# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'paste_board.ui'
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
    QLabel, QLineEdit, QPlainTextEdit, QProgressBar,
    QPushButton, QSizePolicy, QSpacerItem, QTabWidget,
    QVBoxLayout, QWidget)

class Ui_PasteBoardDialog(object):
    def setupUi(self, PasteBoardDialog):
        if not PasteBoardDialog.objectName():
            PasteBoardDialog.setObjectName(u"PasteBoardDialog")
        PasteBoardDialog.setWindowModality(Qt.WindowModality.WindowModal)
        PasteBoardDialog.resize(400, 364)
        PasteBoardDialog.setMaximumSize(QSize(999999, 999999))
        self.gridLayout = QGridLayout(PasteBoardDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, 5, -1, -1)
        self.push_button_send = QPushButton(PasteBoardDialog)
        self.push_button_send.setObjectName(u"push_button_send")
        self.push_button_send.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.horizontalLayout_2.addWidget(self.push_button_send)

        self.push_button_stop = QPushButton(PasteBoardDialog)
        self.push_button_stop.setObjectName(u"push_button_stop")
        self.push_button_stop.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.horizontalLayout_2.addWidget(self.push_button_stop)


        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)

        self.tab_widget = QTabWidget(PasteBoardDialog)
        self.tab_widget.setObjectName(u"tab_widget")
        self.tab_widget.setAcceptDrops(True)
        self.tab_text = QWidget()
        self.tab_text.setObjectName(u"tab_text")
        self.verticalLayout = QVBoxLayout(self.tab_text)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.plain_text_edit = QPlainTextEdit(self.tab_text)
        self.plain_text_edit.setObjectName(u"plain_text_edit")

        self.verticalLayout.addWidget(self.plain_text_edit)

        self.tab_widget.addTab(self.tab_text, "")
        self.tab_file_transfer = QWidget()
        self.tab_file_transfer.setObjectName(u"tab_file_transfer")
        self.tab_file_transfer.setAcceptDrops(True)
        self.verticalLayout_10 = QVBoxLayout(self.tab_file_transfer)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.label_note = QLabel(self.tab_file_transfer)
        self.label_note.setObjectName(u"label_note")
        self.label_note.setAcceptDrops(True)
        self.label_note.setTextFormat(Qt.TextFormat.MarkdownText)
        self.label_note.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self.label_note.setMargin(0)
        self.label_note.setIndent(0)

        self.verticalLayout_10.addWidget(self.label_note)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_10.addItem(self.verticalSpacer)

        self.label_target_file = QLabel(self.tab_file_transfer)
        self.label_target_file.setObjectName(u"label_target_file")
        font = QFont()
        font.setBold(True)
        self.label_target_file.setFont(font)
        self.label_target_file.setAcceptDrops(True)

        self.verticalLayout_10.addWidget(self.label_target_file)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(-1, 4, -1, 4)
        self.line_edit_file_path = QLineEdit(self.tab_file_transfer)
        self.line_edit_file_path.setObjectName(u"line_edit_file_path")

        self.horizontalLayout.addWidget(self.line_edit_file_path)

        self.push_button_file_select = QPushButton(self.tab_file_transfer)
        self.push_button_file_select.setObjectName(u"push_button_file_select")

        self.horizontalLayout.addWidget(self.push_button_file_select)


        self.verticalLayout_10.addLayout(self.horizontalLayout)

        self.progress_bar = QProgressBar(self.tab_file_transfer)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)

        self.verticalLayout_10.addWidget(self.progress_bar)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_10.addItem(self.verticalSpacer_2)

        self.tab_widget.addTab(self.tab_file_transfer, "")

        self.gridLayout.addWidget(self.tab_widget, 0, 0, 1, 1)


        self.retranslateUi(PasteBoardDialog)

        self.tab_widget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(PasteBoardDialog)
    # setupUi

    def retranslateUi(self, PasteBoardDialog):
        PasteBoardDialog.setWindowTitle(QCoreApplication.translate("PasteBoardDialog", u"Paste board", None))
        self.push_button_send.setText(QCoreApplication.translate("PasteBoardDialog", u"Send", None))
        self.push_button_stop.setText(QCoreApplication.translate("PasteBoardDialog", u"Stop", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_text), QCoreApplication.translate("PasteBoardDialog", u"Text", None))
        self.label_note.setText(QCoreApplication.translate("PasteBoardDialog", u"<html><head/><body><p><span style=\" font-weight:700;\">This function can only be used in Linux Terminal</span></p><p>1. Open a terminal, chdir(cd) to target dir.</p><p>2. Keep focus on terminal, select a file on this page.</p><p>3. Click send, wait and see.</p><p>Note: Filename must be ascii, check hash after transfer.</p></body></html>", None))
        self.label_target_file.setText(QCoreApplication.translate("PasteBoardDialog", u"Target File:", None))
        self.push_button_file_select.setText(QCoreApplication.translate("PasteBoardDialog", u"Select", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_file_transfer), QCoreApplication.translate("PasteBoardDialog", u"File Transfer", None))
    # retranslateUi

