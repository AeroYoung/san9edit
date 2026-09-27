@echo off
chcp 65001 >nul
echo === 清理旧产物 ===
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo === 打包中（约 30 秒） ===
python -m PyInstaller san9edit.spec --noconfirm

echo.
echo === 完成 ===
echo 产物目录：dist\暗耻三国志\
echo 双击运行：dist\暗耻三国志\暗耻三国志.exe
pause