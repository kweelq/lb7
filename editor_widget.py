"""
editor_widget.py
Многослойный интерактивный редактор дорожной карты 11х11.
Слои:
  0: Дорожное полотно (Rvertical, Rcrossroads)
  1: Разметка (Zvertical, Zhorizontal)
  2: Знаки и светофоры (Start - Точка А, Stop - Точка Б, Block, TLgreen/yellow/red)
  3: Транспорт и пешеходы (BCvertical, Cvertical, Pedestrain)
"""

from PyQt5.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, pyqtSignal, QTimer


class RoadMapEditor(QTableWidget):
    object_selected = pyqtSignal(dict)

    def __init__(self, rows=11, cols=11, parent=None):
        super().__init__(rows, cols, parent)
        self.rows = rows
        self.cols = cols
        
        # Данные слоев: grid_data[row][col] = {layer_id: object_dict}
        self.grid_data = [[{} for _ in range(cols)] for _ in range(rows)]
        self.current_selected_tool = None
        
        self.init_ui()
        self.init_default_crossroads()
        self.init_simulation()

    def init_ui(self):
        self.setRowCount(self.rows)
        self.setColumnCount(self.cols)
        self.horizontalHeader().setDefaultSectionSize(48)
        self.verticalHeader().setDefaultSectionSize(48)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.setShowGrid(True)
        self.cellClicked.connect(self.on_cell_clicked)

    def init_default_crossroads(self):
        """Начальная разметка 11х11 (Точка А вверху row=0, Точка Б внизу row=10)"""
        mid_r = self.rows // 2  # 5
        mid_c = self.cols // 2  # 5
        
        # Дорога горизонт
        for c in range(self.cols):
            self.place_object(mid_r, c, {
                'id': 'road_crossroads' if c == mid_c else 'road_horizontal',
                'name': 'Перекрёсток' if c == mid_c else 'Дорога гориз.',
                'layer': 0,
            })
            
        # Дорога вертик
        for r in range(self.rows):
            if r != mid_r:
                self.place_object(r, mid_c, {
                    'id': 'road_vertical',
                    'name': 'Дорога верт.',
                    'layer': 0,
                })

        # Зебры
        self.place_object(mid_r, mid_c - 1, {'id': 'zebra_vertical', 'name': 'Зебра', 'layer': 1})
        self.place_object(mid_r, mid_c + 1, {'id': 'zebra_vertical', 'name': 'Зебра', 'layer': 1})
        self.place_object(mid_r - 1, mid_c, {'id': 'zebra_horizontal', 'name': 'Зебра', 'layer': 1})
        self.place_object(mid_r + 1, mid_c, {'id': 'zebra_horizontal', 'name': 'Зебра', 'layer': 1})

        # Светофоры
        self.place_object(mid_r - 1, mid_c - 1, {'id': 'tl_green', 'name': 'Светофор (Зел)', 'layer': 2, 'state': 'green'})
        self.place_object(mid_r + 1, mid_c + 1, {'id': 'tl_red', 'name': 'Светофор (Красн)', 'layer': 2, 'state': 'red'})

        # Точка А (Старт) и Точка Б (Стоп)
        self.place_object(0, mid_c, {'id': 'sign_start', 'name': 'Точка А (Старт)', 'layer': 2})
        self.place_object(10, mid_c, {'id': 'sign_stop', 'name': 'Точка Б (Стоп)', 'layer': 2})

        # Машина готова на старте в точке А
        self.place_object(0, mid_c, {'id': 'car_blue', 'name': 'Синяя машина', 'layer': 3, 'speed': 50, 'direction': 'Вниз'})

    def set_active_tool(self, tool_def):
        self.current_selected_tool = tool_def

    def place_object(self, row, col, obj_def):
        layer = obj_def.get('layer', 0)
        cell_layers = self.grid_data[row][col]

        if layer == 3 and (0 not in cell_layers or 'road' not in cell_layers[0].get('id', '')):
            QMessageBox.warning(self, "Правило", "Машину можно ставить только на дорогу!")
            return False

        if layer == 1 and 0 not in cell_layers:
            QMessageBox.warning(self, "Правило", "Разметку нужно ставить на дорогу!")
            return False

        cell_layers[layer] = {
            **obj_def,
            'x': col,
            'y': row,
            'direction': obj_def.get('direction', 'Вниз'),
            'speed': obj_def.get('speed', 50 if layer == 3 else 0),
            'sensor_id': obj_def.get('sensor_id', f'S_{row}_{col}')
        }
        self.refresh_cell_view(row, col)
        return True

    def refresh_cell_view(self, row, col):
        cell_layers = self.grid_data[row][col]
        item = self.item(row, col)
        if not item:
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row, col, item)

        if not cell_layers:
            item.setText(f"{col},{row}")
            item.setBackground(QColor("#f8fafc"))
            item.setForeground(QColor("#94a3b8"))
            return

        top_layer_id = max(cell_layers.keys())
        top_obj = cell_layers[top_layer_id]

        short_names = {
            'road_vertical': '║ Дор.В',
            'road_horizontal': '═ Дор.Г',
            'road_crossroads': '╬ Перекр.',
            'zebra_vertical': '≡ Зебра',
            'zebra_horizontal': 'Ш Зебра',
            'tl_green': '🟢 Св-фор',
            'tl_red': '🔴 Св-фор',
            'tl_yellow': '🟡 Св-фор',
            'car_blue': '🚙 Машина',
            'car_red': '🚗 Машина',
            'pedestrian': '🚶 Пешеход',
            'sign_start': '🏁 Точка А',
            'sign_stop': '🛑 Точка Б',
            'sign_block': '⛔ Блок',
        }
        name = short_names.get(top_obj.get('id'), top_obj.get('name', 'Объект'))
        item.setText(f"{name}\n[L{top_layer_id}]")
        item.setForeground(QColor("#0f172a"))

        layer_colors = {
            0: QColor("#cbd5e1"),
            1: QColor("#94a3b8"),
            2: QColor("#fef08a"),
            3: QColor("#bfdbfe")
        }
        item.setBackground(layer_colors.get(top_layer_id, QColor("#ffffff")))

    def on_cell_clicked(self, row, col):
        if self.current_selected_tool:
            placed = self.place_object(row, col, self.current_selected_tool)
            if placed:
                top_obj = self.grid_data[row][col][max(self.grid_data[row][col].keys())]
                self.object_selected.emit(top_obj)
        else:
            cell_layers = self.grid_data[row][col]
            if cell_layers:
                top_obj = cell_layers[max(cell_layers.keys())]
                self.object_selected.emit(top_obj)
            else:
                self.object_selected.emit({'empty': True, 'x': col, 'y': row})

    def delete_selected_cell(self):
        """Удаление элемента с выбранной ячейки таблицы"""
        row = self.currentRow()
        col = self.currentColumn()
        if row < 0 or col < 0:
            QMessageBox.information(self, "Удаление", "Сначала выделите ячейку на таблице карты!")
            return None
        cell_layers = self.grid_data[row][col]
        if not cell_layers:
            QMessageBox.information(self, "Удаление", f"Ячейка ({col}, {row}) уже пуста.")
            return None
        top_layer = max(cell_layers.keys())
        removed = cell_layers.pop(top_layer)
        self.refresh_cell_view(row, col)
        self.object_selected.emit({'empty': True, 'x': col, 'y': row})
        return removed

    def delete_object(self, row, col):
        if 0 <= row < self.rows and 0 <= col < self.cols:
            cell_layers = self.grid_data[row][col]
            if cell_layers:
                top_layer = max(cell_layers.keys())
                removed = cell_layers.pop(top_layer)
                self.refresh_cell_view(row, col)
                self.object_selected.emit({'empty': True, 'x': col, 'y': row})
                return removed
        return None

    # ========================================================
    # СИМУЛЯЦИЯ: Машина едет от Точки А (row=0) в Точку Б (row=10)
    # ========================================================
    def init_simulation(self):
        self.sim_timer = QTimer(self)
        self.sim_timer.setInterval(500)
        self.sim_timer.timeout.connect(self._simulation_step)
        self.sim_car_pos = [0, 5]
        self.sim_target_row = 10

    def start_car_simulation(self):
        self.place_object(0, 5, {'id': 'sign_start', 'name': 'Точка А (Старт)', 'layer': 2})
        self.place_object(10, 5, {'id': 'sign_stop', 'name': 'Точка Б (Стоп)', 'layer': 2})

        r, c = self.sim_car_pos
        self.place_object(r, c, {'id': 'car_blue', 'name': 'Синяя машина', 'layer': 3, 'direction': 'Вниз'})
        self.sim_timer.start()

    def stop_car_simulation(self):
        if self.sim_timer.isActive():
            self.sim_timer.stop()

    def reset_car_to_start(self):
        self.stop_car_simulation()
        r, c = self.sim_car_pos
        if 3 in self.grid_data[r][c]:
            del self.grid_data[r][c][3]
            self.refresh_cell_view(r, c)
            
        self.sim_car_pos = [0, 5]
        self.place_object(0, 5, {'id': 'car_blue', 'name': 'Синяя машина', 'layer': 3, 'direction': 'Вниз'})

    def _simulation_step(self):
        curr_r, c = self.sim_car_pos
        if 3 in self.grid_data[curr_r][c]:
            del self.grid_data[curr_r][c][3]
            self.refresh_cell_view(curr_r, c)

        next_r = curr_r + 1
        if next_r > self.sim_target_row:
            self.sim_timer.stop()
            self.place_object(self.sim_target_row, c, {'id': 'car_blue', 'name': 'Синяя машина (Финиш)', 'layer': 3, 'direction': 'Вниз'})
            QMessageBox.information(self, "Финиш", "🎉 Машина успешно доехала из точки А в точку Б!")
            return

        self.sim_car_pos = [next_r, c]
        self.place_object(next_r, c, {'id': 'car_blue', 'name': 'Синяя машина', 'layer': 3, 'direction': 'Вниз'})