import os
import sys
import datetime

from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from project_vars import *
from query_db import *

from brush_settings_dialog import BrushSettingsDialog
from figure_settings_dialog import FigureSettingsDialog
from files_history import FilesHistoryDialog


class BrushTool:
    def __init__(self, color, size):
        super(BrushTool, self).__init__()
        self.color = color
        self.size = size

    def set_color(self, color):
        self.color = color

    def set_size(self, size):
        self.size = size

    def get_as_dict(self):
        return {
            'color': self.color,
            'size': self.size
        }


class FigureTool:
    def __init__(self, name, color, outline_color):
        super(FigureTool, self).__init__()
        self.color = color
        self.outline_color = outline_color
        self.name = name

    def get_as_dict(self):
        return {
            'color': self.color,
            'outline_color': self.outline_color,
        }


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('main.ui', self)
        self.fill_tool_bar()
        self.setMouseTracking(False)

        self.action_save.triggered.connect(self.save)
        self.action_open.triggered.connect(self.open)
        self.action_clear.triggered.connect(self.clear_canvas)
        self.action_full_screen.triggered.connect(self.showFullScreen)
        self.action_show_as_window.triggered.connect(self.showNormal)
        self.action_quit.triggered.connect(self.close)
        self.action_files_history.triggered.connect(self.open_files_history)

        self.image = QImage(self.size(), QImage.Format_RGB32)
        self.image.fill(Qt.white)
        self.previous_image = self.image.copy()

        self.drawing = True
        self.last_point = None

        self.drawing_figure = False
        self.drawing_figure_begin = QPoint()
        self.drawing_figure_end = QPoint()

        self.brush_settings = {
            'size': 12,
            'color': QColor(0, 0, 0)
        }
        self.figure_settings = {
            'color': QColor(0, 0, 0),
            'outline_color': QColor(0, 0, 0),
        }

        self.current_tool = BrushTool(self.brush_settings.get('color'), self.brush_settings.get('size'))

    def open_files_history(self):
        files_history_dialog = FilesHistoryDialog()
        files_history_dialog.exec_()

        selected_file_path = files_history_dialog.get_selected_file()
        if selected_file_path:
            self.open(selected_file_path)

    def resizeEvent(self, event):
        new_image = QImage(event.size(), QImage.Format_RGB32)
        new_image.fill(Qt.white)

        painter = QPainter(new_image)
        painter.drawImage(0, 0, self.image, 0, 0)

        self.image = new_image
        self.update()

    def fill_tool_bar(self):
        for icon_alias, icon_file_name in ICONS.items():
            action = QAction(QIcon(os.path.join(ICONS_DIR, icon_file_name)), icon_alias, self)
            self.tool_bar.addAction(action)
            action.triggered.connect(self.select_tool)

    def select_tool(self):
        tool_name = self.sender().text()

        if tool_name == 'brush':
            self.current_tool = BrushTool(self.brush_settings.get('color'), self.brush_settings.get('size'))
        elif tool_name in ['circle', 'square']:
            self.current_tool = FigureTool(tool_name, **self.figure_settings)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()

            if not self.drawing_figure and isinstance(self.current_tool, FigureTool):
                # Start drawing sub figure
                self.drawing_figure = True
                self.drawing_figure_begin = event.pos()
                self.drawing_figure_end = event.pos()

                self.update()
        if event.button() == Qt.RightButton:
            if isinstance(self.current_tool, BrushTool):
                brush_settings_dialog_ = BrushSettingsDialog(event.pos(), self.current_tool.get_as_dict())
                brush_settings_dialog_.exec_()
                self.current_tool = BrushTool(**brush_settings_dialog_.get_settings())
            elif isinstance(self.current_tool, FigureTool):
                figure_settings_dialog_ = FigureSettingsDialog(event.pos(), self.figure_settings)
                figure_settings_dialog_.exec_()
                self.current_tool = FigureTool(self.current_tool.name, **figure_settings_dialog_.get_settings())
                self.figure_settings = self.current_tool.get_as_dict()

    def mouseMoveEvent(self, event):
        if event.buttons() and Qt.LeftButton and self.drawing:
            if isinstance(self.current_tool, BrushTool):
                self.previous_image = self.image.copy()
                painter = QPainter(self.image)
                painter.setPen(QPen(self.current_tool.color, self.current_tool.size, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(self.last_point, event.pos())
                self.last_point = event.pos()
                self.update()

        if self.drawing_figure and isinstance(self.current_tool, FigureTool):
            # Update figure ghost
            self.drawing_figure_end = event.pos()
            self.update()

    def draw_figure_by_name_and_rect(self, name, rect):
        if isinstance(self.current_tool, FigureTool):
            self.previous_image = self.image.copy()

            painter = QPainter(self.image)
            painter.setPen(QPen(self.current_tool.outline_color, Qt.SolidLine))
            painter.setBrush(QBrush(self.current_tool.color, Qt.SolidPattern))

            if name == 'circle':
                painter.drawEllipse(rect)
            elif name == 'square':
                painter.drawRect(rect)

            painter.end()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.drawing_figure and isinstance(self.current_tool, FigureTool):
            # End of creating figure
            self.drawing_figure_end = event.pos()
            self.drawing_figure = False

            self.draw_figure_by_name_and_rect(self.current_tool.name,
                                              QRect(self.drawing_figure_begin, self.drawing_figure_end))

    def paintEvent(self, event):
        canvas_painter = QPainter(self)
        canvas_painter.drawImage(0, 0, self.image, 0, 0)

        if self.drawing_figure and isinstance(self.current_tool, FigureTool):
            color = QColor(self.current_tool.color)
            color.setAlpha(40)
            canvas_painter.setBrush(QBrush(color))
            canvas_painter.setPen(QPen(self.current_tool.outline_color))

            # drawing figure ghost
            ghost_figure_rect = QRect(self.drawing_figure_begin, self.drawing_figure_end)
            if self.current_tool.name == 'circle':
                canvas_painter.drawEllipse(ghost_figure_rect)
            elif self.current_tool.name == 'square':
                canvas_painter.drawRect(ghost_figure_rect)

            canvas_painter.end()

            self.update()

    def save(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Open Image", "",
                                                   "Image(*.png *.jpg *.jpeg);;All Files(*.*)")
        if not file_path:
            QMessageBox().critical(self, 'Ошибка!', 'Не выбрано название файла')
            return

        self.image.save(file_path)
        self.save_to_history(file_path)
        self.previous_image = self.image.copy()

    def save_to_history(self, file_path):
        save_to_history(file_path, str(datetime.datetime.now()), os.path.basename(file_path))

    def open(self, file_path=None):
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "",
                                                       "Image(*.png *.jpg *.jpeg);;All Files(*.*)")

            if not file_path:
                QMessageBox.critical(self, 'Ошибка!', 'Не выбрано название файла')
                return

        self.clear_canvas()

        pixmap = self.scaled_pixmap_if_bigger_than_screen(QPixmap(file_path))

        self.image = pixmap.toImage()
        self.previous_image = self.image.copy()

        self.resize(pixmap.width(), pixmap.height())
        self.update()

    @staticmethod
    def scaled_pixmap_if_bigger_than_screen(pixmap):
        screen_size = QApplication.primaryScreen().size()

        if pixmap.width() > screen_size.width() and pixmap.height() > screen_size.height():
            if pixmap.height() > pixmap.width():
                return pixmap.scaledToHeight(screen_size.height())
            else:
                return pixmap.scaledToWidth(screen_size.width())
        elif pixmap.height() > screen_size.height():
            return pixmap.scaledToHeight(screen_size.height())
        elif pixmap.width() > screen_size.width():
            return pixmap.scaledToWidth(screen_size.width())
        else:
            return pixmap

    def clear_canvas(self):
        self.image.fill(Qt.white)
        self.update()

    def is_image_saved(self):
        if self.image != self.previous_image:
            return False

        return True

    def closeEvent(self, event):
        is_file_saved = self.is_image_saved()

        if not is_file_saved:
            ans = QMessageBox().question(self, 'Сохранить?', 'Вы не сохранили изменения в файле.\nСохранить?')

            if ans == QMessageBox().Yes:
                self.save()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    app.exec()
