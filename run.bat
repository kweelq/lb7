@echo off
chcp 65001 > nul
echo Запуск приложения PyQt5...

:: Проверка зависимостей
pip install PyQt5 numpy pandas matplotlib --quiet

:: Запуск главного окна
python main.py

pause