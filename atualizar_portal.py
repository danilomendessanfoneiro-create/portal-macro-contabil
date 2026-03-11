import subprocess

print("Extraindo dados fiscais...")
subprocess.run(["python","Fiscal_imposto.py"])

print("Extraindo dados folha...")
subprocess.run(["python","DPRecibo.py"])

print("Enviando atualização para GitHub...")
subprocess.run(["python","auto_update.py"])

print("Portal atualizado com sucesso!")