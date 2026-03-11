import os
import subprocess
from datetime import datetime

pasta_projeto = r"C:\oneflow_bi"

os.chdir(pasta_projeto)

print("Atualizando dados no GitHub...")

# adicionar arquivos
subprocess.run(["git","add","."])

# mensagem com data
msg = f"Atualização automática {datetime.now()}"

# commit
subprocess.run(["git","commit","-m",msg])

# push
subprocess.run(["git","push"])

print("Atualização enviada!")