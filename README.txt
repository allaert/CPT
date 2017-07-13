CPT

Freeze for Windows

from the project root use
pyinstaller --icon=cpt.ico cpt_win32.spec

after building your package dist
you can create an installer by using the installer_win32.iss
for Inno Setup in a the directory under the project root
Make sure that the minimal_adb_fastboot setup exe is in that
directory as well, as it will be packaged in the installer as well




