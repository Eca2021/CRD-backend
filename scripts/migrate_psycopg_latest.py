import psycopg

conn = psycopg.connect('postgresql://postgres:POS_2025@127.0.0.1:5432/Creditos?connect_timeout=5&sslmode=disable')
with conn.cursor() as cur:
    print('1. Agregando porcentaje a reglas_credito')
    cur.execute('ALTER TABLE reglas_credito ADD COLUMN IF NOT EXISTS porcentaje numeric;')
    
    print('2. Migrando tasas a reglas')
    cur.execute('SELECT id_tasa, porcentaje FROM tasas_interes;')
    tasas = cur.fetchall()
    
    for id_tasa, pct in tasas:
        if id_tasa == 1: cod, nom, dias = 'SEM', 'Semanal', 7
        elif id_tasa == 2: cod, nom, dias = 'QUIN', 'Quincenal', 15
        elif id_tasa == 3: cod, nom, dias = 'MENS', 'Mensual', 30
        else: continue
        
        cur.execute(f"""
            INSERT INTO reglas_credito (codigo, nombre, id_tasa, dias_intervalo, activo, porcentaje)
            VALUES ('{cod}', '{nom}', {id_tasa}, {dias}, true, {pct})
            ON CONFLICT (codigo) DO UPDATE SET porcentaje = EXCLUDED.porcentaje, id_tasa = EXCLUDED.id_tasa;
        """)

    print('3. Asignando id_regla a creditos')
    cur.execute('''
        UPDATE creditos c 
        SET id_regla = r.id_regla 
        FROM reglas_credito r 
        WHERE c.id_tasa = r.id_tasa AND c.id_regla IS NULL;
    ''')
    
    print('Limpiando ids huerfanos si los hay para creditos')
    cur.execute('''
        UPDATE creditos SET id_regla = (SELECT MIN(id_regla) FROM reglas_credito) WHERE id_regla IS NULL;
    ''')
    
    print('Limpiando regla sin porcentaje')
    cur.execute('''
        UPDATE reglas_credito SET porcentaje = 0 WHERE porcentaje IS NULL;
    ''')
    
    print('4. Forzando id_regla NOT NULL')
    cur.execute('ALTER TABLE creditos ALTER COLUMN id_regla SET NOT NULL;')
    
    print('5. Borrando id_tasa de creditos')
    cur.execute('ALTER TABLE creditos DROP CONSTRAINT IF EXISTS creditos_id_tasa_fkey;')
    cur.execute('ALTER TABLE creditos DROP COLUMN IF EXISTS id_tasa;')
    
    print('6. Borrando id_tasa de reglas_credito')
    cur.execute('ALTER TABLE reglas_credito DROP CONSTRAINT IF EXISTS reglas_credito_id_tasa_fkey;')
    cur.execute('ALTER TABLE reglas_credito DROP COLUMN IF EXISTS id_tasa;')
    cur.execute('ALTER TABLE reglas_credito ALTER COLUMN porcentaje SET NOT NULL;')
    
    conn.commit()
    print('Migracion Finalizada Correctamente')
conn.close()
