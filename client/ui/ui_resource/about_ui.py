# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'about.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
    QSizePolicy, QTextEdit, QVBoxLayout, QWidget)

class Ui_AboutDialog(object):
    def setupUi(self, AboutDialog):
        if not AboutDialog.objectName():
            AboutDialog.setObjectName(u"AboutDialog")
        AboutDialog.resize(400, 320)
        self.verticalLayout = QVBoxLayout(AboutDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_1 = QHBoxLayout()
        self.horizontalLayout_1.setObjectName(u"horizontalLayout_1")
        self.label_project_name_key = QLabel(AboutDialog)
        self.label_project_name_key.setObjectName(u"label_project_name_key")

        self.horizontalLayout_1.addWidget(self.label_project_name_key)

        self.label_project_name_value = QLabel(AboutDialog)
        self.label_project_name_value.setObjectName(u"label_project_name_value")
        self.label_project_name_value.setText(u"<a href=\"https://github.com/wevsty/KVM-over-USB\">KVM-over-USB</a>")
        self.label_project_name_value.setWordWrap(False)
        self.label_project_name_value.setOpenExternalLinks(True)

        self.horizontalLayout_1.addWidget(self.label_project_name_value)


        self.verticalLayout.addLayout(self.horizontalLayout_1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_project_description_value = QLabel(AboutDialog)
        self.label_project_description_value.setObjectName(u"label_project_description_value")

        self.horizontalLayout_2.addWidget(self.label_project_description_value)

        self.label_project_description_key = QLabel(AboutDialog)
        self.label_project_description_key.setObjectName(u"label_project_description_key")

        self.horizontalLayout_2.addWidget(self.label_project_description_key)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_project_fork_from_key = QLabel(AboutDialog)
        self.label_project_fork_from_key.setObjectName(u"label_project_fork_from_key")

        self.horizontalLayout_3.addWidget(self.label_project_fork_from_key)

        self.label_project_fork_from_value = QLabel(AboutDialog)
        self.label_project_fork_from_value.setObjectName(u"label_project_fork_from_value")
        self.label_project_fork_from_value.setText(u"<a href=\"https://github.com/ElluIFX/KVM-Card-Mini-PySide6\">ElluIFX: KVM-Card-Mini-PySide6</a>")
        self.label_project_fork_from_value.setOpenExternalLinks(True)

        self.horizontalLayout_3.addWidget(self.label_project_fork_from_value)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_client_version_key = QLabel(AboutDialog)
        self.label_client_version_key.setObjectName(u"label_client_version_key")

        self.horizontalLayout_4.addWidget(self.label_client_version_key)

        self.label_client_version_value = QLabel(AboutDialog)
        self.label_client_version_value.setObjectName(u"label_client_version_value")
        self.label_client_version_value.setText(u"v2024.10.10")

        self.horizontalLayout_4.addWidget(self.label_client_version_value)


        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_python_version_key = QLabel(AboutDialog)
        self.label_python_version_key.setObjectName(u"label_python_version_key")

        self.horizontalLayout_5.addWidget(self.label_python_version_key)

        self.label_python_version_value = QLabel(AboutDialog)
        self.label_python_version_value.setObjectName(u"label_python_version_value")
        self.label_python_version_value.setText(u"3.12.0")

        self.horizontalLayout_5.addWidget(self.label_python_version_value)


        self.verticalLayout.addLayout(self.horizontalLayout_5)

        self.label_dependencies = QLabel(AboutDialog)
        self.label_dependencies.setObjectName(u"label_dependencies")

        self.verticalLayout.addWidget(self.label_dependencies)

        self.text_edit_info = QTextEdit(AboutDialog)
        self.text_edit_info.setObjectName(u"text_edit_info")
        self.text_edit_info.setReadOnly(True)

        self.verticalLayout.addWidget(self.text_edit_info)


        self.retranslateUi(AboutDialog)

        QMetaObject.connectSlotsByName(AboutDialog)
    # setupUi

    def retranslateUi(self, AboutDialog):
        AboutDialog.setWindowTitle(QCoreApplication.translate("AboutDialog", u"About", None))
        self.label_project_name_key.setText(QCoreApplication.translate("AboutDialog", u"Project name:", None))
        self.label_project_description_value.setText(QCoreApplication.translate("AboutDialog", u"Project description:", None))
        self.label_project_description_key.setText(QCoreApplication.translate("AboutDialog", u"A simple USB KVM solution", None))
        self.label_project_fork_from_key.setText(QCoreApplication.translate("AboutDialog", u"Project fork from:", None))
        self.label_client_version_key.setText(QCoreApplication.translate("AboutDialog", u"Client version:", None))
        self.label_python_version_key.setText(QCoreApplication.translate("AboutDialog", u"Python version:", None))
        self.label_dependencies.setText(QCoreApplication.translate("AboutDialog", u"Dependencies:", None))
    # retranslateUi

