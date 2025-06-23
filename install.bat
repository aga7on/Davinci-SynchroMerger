@echo off
echo Создание виртуального окружения...
python -m venv venv
echo Активация виртуального окружения и установка PyInstaller...
call venv\Scripts\activate.bat
pip install pyinstaller
echo Установка завершена.
pause