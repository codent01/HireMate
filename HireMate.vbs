Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "F:\Claude CODE\nextraise-local"
WshShell.Run """F:\Claude CODE\nextraise-local\venv\Scripts\pythonw.exe"" ""F:\Claude CODE\nextraise-local\launcher.py""", 0, False
