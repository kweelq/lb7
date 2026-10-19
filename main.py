"""
main.py
Главное окно приложения PyQt5.
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QGroupBox, QLineEdit,
    QSpinBox, QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt

from editor_widget import RoadMapEditor
from data_processor import generate_sample_sensor_csv
from neural_net import TrafficTrainer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Редактор дорожной карты и Обучение нейросети (PyQt5)")
        self.resize(1300, 880)

        # 1. Подготовка датасета ЛР6 и инициализация тренера
        csv_file = generate_sample_sensor_csv()
        self.trainer = TrafficTrainer(csv_file)

        # 2. Инициализация UI
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # ========================================================
        # 1. ВЕРХНЯЯ ПАНЕЛЬ: 3 КНОПКИ ОБУЧЕНИЯ
        # ========================================================
        top_group = QGroupBox("Панель управления обучением нейросети")
        top_layout = QHBoxLayout(top_group)
        top_layout.setContentsMargins(10, 10, 10, 10)
        top_layout.setSpacing(12)

        self.btn_train_epoch = QPushButton("Начать обучение (1 эпоха)")
        self.btn_train_epoch.setStyleSheet("padding: 7px 16px; font-weight: bold; background-color: #2563eb; color: white;")
        self.btn_train_epoch.clicked.connect(self.on_train_epoch_click)

        self.btn_show_process = QPushButton("Процесс обучения")
        self.btn_show_process.setStyleSheet("padding: 7px 16px;")
        self.btn_show_process.clicked.connect(self.on_focus_process_table)

        self.btn_show_logs = QPushButton("Журнал событий")
        self.btn_show_logs.setStyleSheet("padding: 7px 16px;")
        self.btn_show_logs.clicked.connect(self.on_focus_logs_table)

        top_layout.addWidget(self.btn_train_epoch)
        top_layout.addWidget(self.btn_show_process)
        top_layout.addWidget(self.btn_show_logs)
        top_layout.addStretch()

        main_layout.addWidget(top_group)

        # ========================================================
        # 2. СРЕДНЯЯ ЗОНА: [объекты] | [карта 11х11] | [свойства]
        # ========================================================
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(10)

        # --- КОЛОНКА 1 (СЛЕВА): "объекты" ---
        group_objects = QGroupBox("объекты")
        layout_objects = QVBoxLayout(group_objects)
        self.list_objects = QListWidget()
        self.populate_objects_library()
        self.list_objects.itemClicked.connect(self.on_object_selected_from_library)
        layout_objects.addWidget(self.list_objects)
        middle_layout.addWidget(group_objects, stretch=2)

        # --- КОЛОНКА 2 (ЦЕНТР): "карта" ---
        group_map = QGroupBox("карта (11х11 квадратиков)")
        layout_map = QVBoxLayout(group_map)
        
        # Кнопки: Запуск, Стоп, В точку А, Удалить элемент
        map_tools_layout = QHBoxLayout()
        self.btn_run_sim = QPushButton("▶ Запуск (А → Б)")
        self.btn_run_sim.setStyleSheet("background-color: #15803d; color: white; font-weight: bold; padding: 6px 12px;")
        self.btn_run_sim.clicked.connect(self.start_sim)

        self.btn_stop_sim = QPushButton("⏹ Стоп")
        self.btn_stop_sim.clicked.connect(self.stop_sim)

        self.btn_reset_car = QPushButton("⏮ В точку А")
        self.btn_reset_car.clicked.connect(self.reset_sim)

        self.btn_delete_element = QPushButton("🗑️ Удалить элемент")
        self.btn_delete_element.setStyleSheet("background-color: #991b1b; color: white; font-weight: bold; padding: 6px 12px;")
        self.btn_delete_element.clicked.connect(self.delete_element)

        map_tools_layout.addWidget(self.btn_run_sim)
        map_tools_layout.addWidget(self.btn_stop_sim)
        map_tools_layout.addWidget(self.btn_reset_car)
        map_tools_layout.addWidget(self.btn_delete_element)
        layout_map.addLayout(map_tools_layout)

        self.map_editor = RoadMapEditor(rows=11, cols=11)
        self.map_editor.object_selected.connect(self.on_map_object_selected)
        layout_map.addWidget(self.map_editor)
        middle_layout.addWidget(group_map, stretch=5)

        # --- КОЛОНКА 3 (СПРАВА): "свойства" ---
        group_props = QGroupBox("свойства")
        layout_props = QVBoxLayout(group_props)
        layout_props.setSpacing(10)

        self.prop_name = QLineEdit()
        self.prop_name.setPlaceholderText("Название объекта")
        self.prop_name.setReadOnly(True)
        layout_props.addWidget(self.prop_name)

        coord_layout = QHBoxLayout()
        self.prop_x = QSpinBox()
        self.prop_x.setRange(0, 10)
        self.prop_y = QSpinBox()
        self.prop_y.setRange(0, 10)
        coord_layout.addWidget(self.prop_x)
        coord_layout.addWidget(self.prop_y)
        layout_props.addLayout(coord_layout)

        self.prop_direction = QComboBox()
        self.prop_direction.addItems(["Вниз (180°)", "Вверх (0°)", "Вправо (90°)", "Влево (270°)"])
        layout_props.addWidget(self.prop_direction)

        self.prop_extra = QLineEdit()
        self.prop_extra.setPlaceholderText("Скорость или ID датчика")
        layout_props.addWidget(self.prop_extra)

        layout_props.addStretch()

        self.btn_save_props = QPushButton("Сохранить свойства")
        self.btn_save_props.setStyleSheet("padding: 7px 14px; font-weight: bold; background-color: #2563eb; color: white;")
        self.btn_save_props.clicked.connect(self.on_save_properties_clicked)
        layout_props.addWidget(self.btn_save_props)

        self.btn_delete_prop = QPushButton("🗑️ Удалить этот объект")
        self.btn_delete_prop.setStyleSheet("padding: 5px; color: #ef4444;")
        self.btn_delete_prop.clicked.connect(self.on_delete_selected_from_props)
        layout_props.addWidget(self.btn_delete_prop)

        middle_layout.addWidget(group_props, stretch=2)
        main_layout.addLayout(middle_layout, stretch=4)

        # ========================================================
        # 3. НИЖНЯЯ ЗОНА: ДВЕ ТАБЛИЦЫ
        # [Журнал событий] | [Процесс обучения]
        # ========================================================
        bottom_tables_layout = QHBoxLayout()
        bottom_tables_layout.setSpacing(10)

        # Таблица слева: Журнал событий
        self.table_logs = QTableWidget(0, 6)
        self.table_logs.setHorizontalHeaderLabels([
            "время начала", "Номер эпохи", "потери", "точность", "файл модели", "статус"
        ])
        self.table_logs.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        bottom_tables_layout.addWidget(self.table_logs, stretch=3)

        # Таблица справа: Процесс обучения
        self.table_process = QTableWidget(0, 4)
        self.table_process.setHorizontalHeaderLabels([
            "Номер эпохи", "Потери", "Точность", "Время шага"
        ])
        self.table_process.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        bottom_tables_layout.addWidget(self.table_process, stretch=2)

        main_layout.addLayout(bottom_tables_layout, stretch=2)

    def populate_objects_library(self):
        """Только ваши 19 картинок, без лишнего газона"""
        catalog = [
            {"id": "road_vertical", "name": "Дорога верт. (Rvertical)", "layer": 0},
            {"id": "road_crossroads", "name": "Перекрёсток (Rcrossroads)", "layer": 0},
            {"id": "zebra_vertical", "name": "Зебра верт. (Zvertical)", "layer": 1},
            {"id": "zebra_horizontal", "name": "Зебра гориз. (Zhorizontal)", "layer": 1},
            {"id": "tl_green", "name": "Светофор зеленый (TLgreen)", "layer": 2},
            {"id": "tl_yellow", "name": "Светофор желтый (TLyellow)", "layer": 2},
            {"id": "tl_red", "name": "Светофор красный (TLred)", "layer": 2},
            {"id": "sign_start", "name": "Точка А / Старт (Start)", "layer": 2},
            {"id": "sign_stop", "name": "Точка Б / Стоп (Stop)", "layer": 2},
            {"id": "sign_block", "name": "Знак 'Движение запрещено' (Block)", "layer": 2},
            {"id": "car_blue", "name": "Синяя машина (BCvertical)", "layer": 3, "speed": 45},
            {"id": "car_red", "name": "Красная машина (Cvertical)", "layer": 3, "speed": 60},
            {"id": "pedestrian", "name": "Пешеход (Pedestrain)", "layer": 3, "speed": 5},
        ]
        for obj in catalog:
            item = QListWidgetItem(f"[{obj['layer']} слой] {obj['name']}")
            item.setData(Qt.UserRole, obj)
            self.list_objects.addItem(item)

    def start_sim(self): self.map_editor.start_car_simulation()
    def stop_sim(self): self.map_editor.stop_car_simulation()
    def reset_sim(self): self.map_editor.reset_car_to_start()
    def delete_element(self): self.map_editor.delete_selected_cell()

    def on_object_selected_from_library(self, item):
        obj_def = item.data(Qt.UserRole)
        self.map_editor.set_active_tool(obj_def)

    def on_map_object_selected(self, obj):
        if obj.get('empty'):
            self.prop_name.setText("Пустая клетка")
            self.prop_x.setValue(obj.get('x', 0))
            self.prop_y.setValue(obj.get('y', 0))
            self.prop_extra.setText("")
            return

        self.prop_name.setText(obj.get('name', ''))
        self.prop_x.setValue(obj.get('x', 0))
        self.prop_y.setValue(obj.get('y', 0))
        dir_text = obj.get('direction', 'Вниз')
        idx = self.prop_direction.findText(dir_text, Qt.MatchStartsWith)
        if idx >= 0: self.prop_direction.setCurrentIndex(idx)
        extra = f"{obj.get('speed', 0)} км/ч" if 'speed' in obj else obj.get('sensor_id', '')
        self.prop_extra.setText(str(extra))

    def on_save_properties_clicked(self):
        x = self.prop_x.value()
        y = self.prop_y.value()
        cell_layers = self.map_editor.grid_data[y][x]
        if cell_layers:
            top_layer = max(cell_layers.keys())
            cell_layers[top_layer]['direction'] = self.prop_direction.currentText().split()[0]
            cell_layers[top_layer]['sensor_id'] = self.prop_extra.text()
            QMessageBox.information(self, "Успех", f"Свойства объекта в ячейке ({x}, {y}) обновлены!")
        else:
            QMessageBox.warning(self, "Предупреждение", f"В ячейке ({x}, {y}) нет объекта!")

    def on_delete_selected_from_props(self):
        x = self.prop_x.value()
        y = self.prop_y.value()
        removed = self.map_editor.delete_object(y, x)
        if removed:
            self.prop_name.setText("Пустая клетка")
            self.prop_extra.setText("")
            QMessageBox.information(self, "Удалено", f"Объект '{removed.get('name')}' удален с карты!")
        else:
            QMessageBox.warning(self, "Внимание", f"В ячейке ({x}, {y}) нет объекта для удаления.")

    def on_train_epoch_click(self):
        res = self.trainer.train_one_epoch()

        # Запись в таблицу 'Процесс обучения' (справа)
        row_proc = self.table_process.rowCount()
        self.table_process.insertRow(row_proc)
        self.table_process.setItem(row_proc, 0, QTableWidgetItem(f"Эпоха {res['epoch']}"))
        self.table_process.setItem(row_proc, 1, QTableWidgetItem(str(res['loss'])))
        self.table_process.setItem(row_proc, 2, QTableWidgetItem(f"{res['accuracy']}%"))
        self.table_process.setItem(row_proc, 3, QTableWidgetItem(res['start_time']))
        self.table_process.scrollToBottom()

        # Запись в таблицу 'Журнал событий' (слева)
        row_log = self.table_logs.rowCount()
        self.table_logs.insertRow(row_log)
        self.table_logs.setItem(row_log, 0, QTableWidgetItem(res['start_time']))
        self.table_logs.setItem(row_log, 1, QTableWidgetItem(f"Эпоха {res['epoch']}"))
        self.table_logs.setItem(row_log, 2, QTableWidgetItem(str(res['loss'])))
        self.table_logs.setItem(row_log, 3, QTableWidgetItem(f"{res['accuracy']}%"))
        self.table_logs.setItem(row_log, 4, QTableWidgetItem(res['saved_model']))
        self.table_logs.setItem(row_log, 5, QTableWidgetItem(res['status']))
        self.table_logs.scrollToBottom()

    def on_focus_process_table(self):
        self.table_process.setFocus()
        if self.table_process.rowCount() > 0:
            self.table_process.selectRow(self.table_process.rowCount() - 1)

    def on_focus_logs_table(self):
        self.table_logs.setFocus()
        if self.table_logs.rowCount() > 0:
            self.table_logs.selectRow(self.table_logs.rowCount() - 1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())