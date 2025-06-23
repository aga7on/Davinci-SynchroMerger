@echo off
echo Активация виртуального окружения и запуск приложения...
call venv\Scripts\activate.bat
python main.py
echo Приложение завершило работу.
pause