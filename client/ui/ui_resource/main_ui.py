# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.7.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QMainWindow, QMenu, QMenuBar,
    QSizePolicy, QStatusBar, QWidget)

class Ui_main_window(object):
    def setupUi(self, main_window):
        if not main_window.objectName():
            main_window.setObjectName(u"main_window")
        main_window.resize(960, 600)
        main_window.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.action_video_device_setup = QAction(main_window)
        self.action_video_device_setup.setObjectName(u"action_video_device_setup")
        self.action_video_device_connect = QAction(main_window)
        self.action_video_device_connect.setObjectName(u"action_video_device_connect")
        self.action_video_device_disconnect = QAction(main_window)
        self.action_video_device_disconnect.setObjectName(u"action_video_device_disconnect")
        self.action_exit = QAction(main_window)
        self.action_exit.setObjectName(u"action_exit")
        self.action_reload_keyboard = QAction(main_window)
        self.action_reload_keyboard.setObjectName(u"action_reload_keyboard")
        self.action_reload_mouse = QAction(main_window)
        self.action_reload_mouse.setObjectName(u"action_reload_mouse")
        self.action_minimize = QAction(main_window)
        self.action_minimize.setObjectName(u"action_minimize")
        self.action_device_reload = QAction(main_window)
        self.action_device_reload.setObjectName(u"action_device_reload")
        self.action_release_mouse = QAction(main_window)
        self.action_release_mouse.setObjectName(u"action_release_mouse")
        self.action_capture_mouse = QAction(main_window)
        self.action_capture_mouse.setObjectName(u"action_capture_mouse")
        self.action_custom_key = QAction(main_window)
        self.action_custom_key.setObjectName(u"action_custom_key")
        self.action_open_on_screen_keyboard = QAction(main_window)
        self.action_open_on_screen_keyboard.setObjectName(u"action_open_on_screen_keyboard")
        self.action_open_calculator = QAction(main_window)
        self.action_open_calculator.setObjectName(u"action_open_calculator")
        self.action_open_snipping_tool = QAction(main_window)
        self.action_open_snipping_tool.setObjectName(u"action_open_snipping_tool")
        self.action_open_notepad = QAction(main_window)
        self.action_open_notepad.setObjectName(u"action_open_notepad")
        self.action_indicator_light = QAction(main_window)
        self.action_indicator_light.setObjectName(u"action_indicator_light")
        self.action_fullscreen = QAction(main_window)
        self.action_fullscreen.setObjectName(u"action_fullscreen")
        self.action_fullscreen.setCheckable(True)
        self.action_resize_window = QAction(main_window)
        self.action_resize_window.setObjectName(u"action_resize_window")
        self.action_keep_ratio = QAction(main_window)
        self.action_keep_ratio.setObjectName(u"action_keep_ratio")
        self.action_keep_ratio.setCheckable(True)
        self.action_topmost = QAction(main_window)
        self.action_topmost.setObjectName(u"action_topmost")
        self.action_topmost.setCheckable(True)
        self.action_paste_board = QAction(main_window)
        self.action_paste_board.setObjectName(u"action_paste_board")
        self.action_hide_cursor = QAction(main_window)
        self.action_hide_cursor.setObjectName(u"action_hide_cursor")
        self.action_hide_cursor.setCheckable(True)
        self.action_capture_frame = QAction(main_window)
        self.action_capture_frame.setObjectName(u"action_capture_frame")
        self.action_quick_paste = QAction(main_window)
        self.action_quick_paste.setObjectName(u"action_quick_paste")
        self.action_quick_paste.setCheckable(True)
        self.action_open_windows_device_manager = QAction(main_window)
        self.action_open_windows_device_manager.setObjectName(u"action_open_windows_device_manager")
        self.action_num_keyboard = QAction(main_window)
        self.action_num_keyboard.setObjectName(u"action_num_keyboard")
        self.action_record_video = QAction(main_window)
        self.action_record_video.setObjectName(u"action_record_video")
        self.action_record_video.setCheckable(True)
        self.action_system_hook = QAction(main_window)
        self.action_system_hook.setObjectName(u"action_system_hook")
        self.action_system_hook.setCheckable(True)
        self.action_relative_mouse = QAction(main_window)
        self.action_relative_mouse.setObjectName(u"action_relative_mouse")
        self.action_relative_mouse.setCheckable(True)
        self.action_controller_device_setup = QAction(main_window)
        self.action_controller_device_setup.setObjectName(u"action_controller_device_setup")
        self.action_about_qt = QAction(main_window)
        self.action_about_qt.setObjectName(u"action_about_qt")
        self.action_about = QAction(main_window)
        self.action_about.setObjectName(u"action_about")
        self.action_device_reset = QAction(main_window)
        self.action_device_reset.setObjectName(u"action_device_reset")
        self.action_pause_keyboard = QAction(main_window)
        self.action_pause_keyboard.setObjectName(u"action_pause_keyboard")
        self.action_pause_keyboard.setCheckable(True)
        self.action_pause_mouse = QAction(main_window)
        self.action_pause_mouse.setObjectName(u"action_pause_mouse")
        self.action_pause_mouse.setCheckable(True)
        self.action_sync_indicator = QAction(main_window)
        self.action_sync_indicator.setObjectName(u"action_sync_indicator")
        self.centralwidget = QWidget(main_window)
        self.centralwidget.setObjectName(u"centralwidget")
        main_window.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(main_window)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 960, 33))
        self.menu_device_menu = QMenu(self.menubar)
        self.menu_device_menu.setObjectName(u"menu_device_menu")
        self.menu_keyboard = QMenu(self.menubar)
        self.menu_keyboard.setObjectName(u"menu_keyboard")
        self.menu_shortcut_keys = QMenu(self.menu_keyboard)
        self.menu_shortcut_keys.setObjectName(u"menu_shortcut_keys")
        self.menu_mouse = QMenu(self.menubar)
        self.menu_mouse.setObjectName(u"menu_mouse")
        self.menu_tools = QMenu(self.menubar)
        self.menu_tools.setObjectName(u"menu_tools")
        self.menu_video = QMenu(self.menubar)
        self.menu_video.setObjectName(u"menu_video")
        self.menu_about = QMenu(self.menubar)
        self.menu_about.setObjectName(u"menu_about")
        main_window.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(main_window)
        self.statusbar.setObjectName(u"statusbar")
        self.statusbar.setStyleSheet(u"padding: 0px;")
        self.statusbar.setSizeGripEnabled(False)
        main_window.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menu_device_menu.menuAction())
        self.menubar.addAction(self.menu_video.menuAction())
        self.menubar.addAction(self.menu_keyboard.menuAction())
        self.menubar.addAction(self.menu_mouse.menuAction())
        self.menubar.addAction(self.menu_tools.menuAction())
        self.menubar.addAction(self.menu_about.menuAction())
        self.menu_device_menu.addAction(self.action_video_device_setup)
        self.menu_device_menu.addAction(self.action_video_device_connect)
        self.menu_device_menu.addAction(self.action_video_device_disconnect)
        self.menu_device_menu.addSeparator()
        self.menu_device_menu.addAction(self.action_controller_device_setup)
        self.menu_device_menu.addAction(self.action_device_reload)
        self.menu_device_menu.addAction(self.action_device_reset)
        self.menu_device_menu.addSeparator()
        self.menu_device_menu.addAction(self.action_minimize)
        self.menu_device_menu.addAction(self.action_exit)
        self.menu_keyboard.addAction(self.action_pause_keyboard)
        self.menu_keyboard.addAction(self.action_reload_keyboard)
        self.menu_keyboard.addSeparator()
        self.menu_keyboard.addAction(self.menu_shortcut_keys.menuAction())
        self.menu_keyboard.addAction(self.action_custom_key)
        self.menu_keyboard.addSeparator()
        self.menu_keyboard.addAction(self.action_paste_board)
        self.menu_keyboard.addAction(self.action_quick_paste)
        self.menu_keyboard.addSeparator()
        self.menu_keyboard.addAction(self.action_system_hook)
        self.menu_keyboard.addSeparator()
        self.menu_keyboard.addAction(self.action_sync_indicator)
        self.menu_keyboard.addAction(self.action_indicator_light)
        self.menu_mouse.addAction(self.action_pause_mouse)
        self.menu_mouse.addAction(self.action_reload_mouse)
        self.menu_mouse.addSeparator()
        self.menu_mouse.addAction(self.action_capture_mouse)
        self.menu_mouse.addAction(self.action_release_mouse)
        self.menu_mouse.addSeparator()
        self.menu_mouse.addAction(self.action_relative_mouse)
        self.menu_mouse.addAction(self.action_hide_cursor)
        self.menu_tools.addAction(self.action_open_windows_device_manager)
        self.menu_tools.addAction(self.action_open_on_screen_keyboard)
        self.menu_tools.addAction(self.action_open_calculator)
        self.menu_tools.addAction(self.action_open_snipping_tool)
        self.menu_tools.addAction(self.action_open_notepad)
        self.menu_video.addAction(self.action_fullscreen)
        self.menu_video.addAction(self.action_resize_window)
        self.menu_video.addAction(self.action_topmost)
        self.menu_video.addSeparator()
        self.menu_video.addAction(self.action_keep_ratio)
        self.menu_video.addAction(self.action_capture_frame)
        self.menu_video.addAction(self.action_record_video)
        self.menu_about.addAction(self.action_about)
        self.menu_about.addSeparator()
        self.menu_about.addAction(self.action_about_qt)

        self.retranslateUi(main_window)

        QMetaObject.connectSlotsByName(main_window)
    # setupUi

    def retranslateUi(self, main_window):
        main_window.setWindowTitle(QCoreApplication.translate("main_window", u"USB KVM Client", None))
        self.action_video_device_setup.setText(QCoreApplication.translate("main_window", u"Video device setup", None))
#if QT_CONFIG(statustip)
        self.action_video_device_setup.setStatusTip(QCoreApplication.translate("main_window", u"Video device setup", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(shortcut)
        self.action_video_device_setup.setShortcut("")
#endif // QT_CONFIG(shortcut)
        self.action_video_device_connect.setText(QCoreApplication.translate("main_window", u"Connect", None))
#if QT_CONFIG(statustip)
        self.action_video_device_connect.setStatusTip(QCoreApplication.translate("main_window", u"Connect device", None))
#endif // QT_CONFIG(statustip)
        self.action_video_device_disconnect.setText(QCoreApplication.translate("main_window", u"Disconnect", None))
#if QT_CONFIG(statustip)
        self.action_video_device_disconnect.setStatusTip(QCoreApplication.translate("main_window", u"Disconnect device", None))
#endif // QT_CONFIG(statustip)
        self.action_exit.setText(QCoreApplication.translate("main_window", u"Exit", None))
#if QT_CONFIG(statustip)
        self.action_exit.setStatusTip(QCoreApplication.translate("main_window", u"Exit program", None))
#endif // QT_CONFIG(statustip)
        self.action_reload_keyboard.setText(QCoreApplication.translate("main_window", u"Reload", None))
        self.action_reload_mouse.setText(QCoreApplication.translate("main_window", u"Reload", None))
        self.action_minimize.setText(QCoreApplication.translate("main_window", u"Minimize", None))
#if QT_CONFIG(statustip)
        self.action_minimize.setStatusTip(QCoreApplication.translate("main_window", u"Minimize Window", None))
#endif // QT_CONFIG(statustip)
        self.action_device_reload.setText(QCoreApplication.translate("main_window", u"Reload", None))
#if QT_CONFIG(statustip)
        self.action_device_reload.setStatusTip(QCoreApplication.translate("main_window", u"Reload device", None))
#endif // QT_CONFIG(statustip)
        self.action_release_mouse.setText(QCoreApplication.translate("main_window", u"Release mouse", None))
#if QT_CONFIG(statustip)
        self.action_release_mouse.setStatusTip(QCoreApplication.translate("main_window", u"Press Ctrl+Alt+F12 release mouse", None))
#endif // QT_CONFIG(statustip)
        self.action_capture_mouse.setText(QCoreApplication.translate("main_window", u"Capture mouse", None))
        self.action_custom_key.setText(QCoreApplication.translate("main_window", u"Custom key", None))
        self.action_open_on_screen_keyboard.setText(QCoreApplication.translate("main_window", u"On-screen Keyboard", None))
        self.action_open_calculator.setText(QCoreApplication.translate("main_window", u"Calculator", None))
        self.action_open_snipping_tool.setText(QCoreApplication.translate("main_window", u"SnippingTool", None))
        self.action_open_notepad.setText(QCoreApplication.translate("main_window", u"Notepad", None))
        self.action_indicator_light.setText(QCoreApplication.translate("main_window", u"Indicator light", None))
        self.action_fullscreen.setText(QCoreApplication.translate("main_window", u"Fullscreen", None))
        self.action_resize_window.setText(QCoreApplication.translate("main_window", u"Resize window", None))
        self.action_keep_ratio.setText(QCoreApplication.translate("main_window", u"Keep aspect ratio", None))
        self.action_topmost.setText(QCoreApplication.translate("main_window", u"Topmost", None))
        self.action_paste_board.setText(QCoreApplication.translate("main_window", u"Pasteboard", None))
        self.action_hide_cursor.setText(QCoreApplication.translate("main_window", u"Hide cursor", None))
        self.action_capture_frame.setText(QCoreApplication.translate("main_window", u"Capture frame", None))
        self.action_quick_paste.setText(QCoreApplication.translate("main_window", u"Quick paste", None))
#if QT_CONFIG(statustip)
        self.action_quick_paste.setStatusTip(QCoreApplication.translate("main_window", u"Press Ctrl+Alt+V to quickly send clipboard contents", None))
#endif // QT_CONFIG(statustip)
        self.action_open_windows_device_manager.setText(QCoreApplication.translate("main_window", u"Windows Device Manager", None))
        self.action_num_keyboard.setText(QCoreApplication.translate("main_window", u"Num Keyboard", None))
        self.action_record_video.setText(QCoreApplication.translate("main_window", u"Record video", None))
        self.action_system_hook.setText(QCoreApplication.translate("main_window", u"System hook", None))
#if QT_CONFIG(statustip)
        self.action_system_hook.setStatusTip(QCoreApplication.translate("main_window", u"Blocks the system from responding to user input", None))
#endif // QT_CONFIG(statustip)
        self.action_relative_mouse.setText(QCoreApplication.translate("main_window", u"Relative mouse", None))
        self.action_controller_device_setup.setText(QCoreApplication.translate("main_window", u"Controller device setup", None))
#if QT_CONFIG(statustip)
        self.action_controller_device_setup.setStatusTip(QCoreApplication.translate("main_window", u"Controller setup", None))
#endif // QT_CONFIG(statustip)
        self.action_about_qt.setText(QCoreApplication.translate("main_window", u"About Qt", None))
        self.action_about.setText(QCoreApplication.translate("main_window", u"About", None))
        self.action_device_reset.setText(QCoreApplication.translate("main_window", u"Reset", None))
#if QT_CONFIG(statustip)
        self.action_device_reset.setStatusTip(QCoreApplication.translate("main_window", u"Reset device", None))
#endif // QT_CONFIG(statustip)
        self.action_pause_keyboard.setText(QCoreApplication.translate("main_window", u"Pause", None))
        self.action_pause_mouse.setText(QCoreApplication.translate("main_window", u"Pause", None))
        self.action_sync_indicator.setText(QCoreApplication.translate("main_window", u"Sync indicator", None))
        self.menu_device_menu.setTitle(QCoreApplication.translate("main_window", u"Device", None))
        self.menu_keyboard.setTitle(QCoreApplication.translate("main_window", u"Keyboard", None))
        self.menu_shortcut_keys.setTitle(QCoreApplication.translate("main_window", u"Shortcut keys", None))
        self.menu_mouse.setTitle(QCoreApplication.translate("main_window", u"Mouse", None))
        self.menu_tools.setTitle(QCoreApplication.translate("main_window", u"Tools", None))
        self.menu_video.setTitle(QCoreApplication.translate("main_window", u"Video", None))
        self.menu_about.setTitle(QCoreApplication.translate("main_window", u"About", None))
    # retranslateUi
