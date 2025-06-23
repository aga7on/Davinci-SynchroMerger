@echo off
echo Активация виртуального окружения и сборка исполняемого файла...
call venv\Scripts\activate.bat
pyinstaller --noconsole --onefile main.py
echo Сборка завершена. Исполняемый файл находится в папке 'dist'.
pause