import subprocess
import time
import sys

exe_path = r"C:\Users\ADN\Videos\Nouveau dossier (4)\dist\SolidariteEtoile.exe"

print(f"Lancement de {exe_path}...")
print("=" * 60)

try:
    process = subprocess.Popen(
        [exe_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    # Attendre 5 secondes
    time.sleep(5)

    # Vérifier si le processus est toujours en cours
    if process.poll() is None:
        print("Processus toujours en cours d'exécution après 5 secondes")
        process.terminate()
        process.wait(timeout=2)
    else:
        stdout, stderr = process.communicate()
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        print("Code de retour:", process.returncode)

except Exception as e:
    print(f"Erreur: {e}")
    import traceback
    traceback.print_exc()
