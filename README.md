# How to

1. Download espeak installer (espeak-ng.msi) from https://github.com/espeak-ng/espeak-ng/releases and install it
2. Open PowerShell as administrator and enter
```
setx PHONEMIZER_ESPEAK_PATH "C:\Program Files\eSpeak NG\espeak-ng.exe"
setx PHONEMIZER_ESPEAK_LIBRARY "C:\Program Files\eSpeak NG\libespeak-ng.dll"
```
3. Close PowerShell
4. Install Python 3.11 or higher from https://www.python.org/downloads/
5. Open PowerShell and run
```pip install phonemizer```
6. Run ```cd 'C:\Path\To\synthv_translator.py'```
7. Run
```
python .\synthv_translator.py Dies ist ein Text in deutscher Sprache
```
The output should be
```
d iy s  ih s t  ay n  t eh k s t  ih n  d ao oe ch er  sh p r aa kh ax
```
