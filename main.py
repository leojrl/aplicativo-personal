import os
import sys
import runpy

# Adiciona o diretório base ao sys.path
DIRETORIO_APP = os.path.dirname(os.path.abspath(__file__))
if DIRETORIO_APP not in sys.path:
    sys.path.insert(0, DIRETORIO_APP)

# Executa o aplicativo principal
CAMINHO_PRINCIPAL = os.path.join(DIRETORIO_APP, "aplicativo.py")
runpy.run_path(CAMINHO_PRINCIPAL, run_name="__main__")

