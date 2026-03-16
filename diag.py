import traceback
import sys
import os

sys.path.append(os.getcwd())

with open('diag_final.txt', 'w', encoding='utf-8') as f:
    try:
        f.write("Intentando importar...\n")
        from app.models.catalog import MovimientoAdmin
        f.write("Importación exitosa.\n")
    except Exception:
        f.write("ERROR:\n")
        traceback.print_exc(file=f)
