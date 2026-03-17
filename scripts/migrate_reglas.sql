-- Paso 1: Agregar columna porcentaje
ALTER TABLE reglas_credito ADD COLUMN IF NOT EXISTS porcentaje numeric;

-- Paso 2: Usar los datos de tasas_interes para rellenar porcentaje y actualizar/crear las reglas base
-- Insertar/actualizar la regla semanal (asumiendo que id_tasa=1 es 7%)
INSERT INTO reglas_credito (codigo, nombre, id_tasa, dias_intervalo, activo, porcentaje)
SELECT 'SEM', 'Semanal', id_tasa, 7, true, porcentaje
FROM tasas_interes WHERE id_tasa = 1
ON CONFLICT (codigo) DO UPDATE 
SET porcentaje = EXCLUDED.porcentaje, id_tasa = EXCLUDED.id_tasa;

-- Insertar/actualizar la regla quincenal (id_tasa=2 es 15%)
INSERT INTO reglas_credito (codigo, nombre, id_tasa, dias_intervalo, activo, porcentaje)
SELECT 'QUIN', 'Quincenal', id_tasa, 15, true, porcentaje
FROM tasas_interes WHERE id_tasa = 2
ON CONFLICT (codigo) DO UPDATE 
SET porcentaje = EXCLUDED.porcentaje, id_tasa = EXCLUDED.id_tasa;

-- Insertar/actualizar la regla mensual (id_tasa=3 es 30%)
INSERT INTO reglas_credito (codigo, nombre, id_tasa, dias_intervalo, activo, porcentaje)
SELECT 'MENS', 'Mensual', id_tasa, 30, true, porcentaje
FROM tasas_interes WHERE id_tasa = 3
ON CONFLICT (codigo) DO UPDATE 
SET porcentaje = EXCLUDED.porcentaje, id_tasa = EXCLUDED.id_tasa;

-- Paso 3: Asignar id_regla a los creditos existentes basados en su id_tasa
UPDATE creditos c
SET id_regla = r.id_regla
FROM reglas_credito r
WHERE c.id_tasa = r.id_tasa AND c.id_regla IS NULL;

-- Asegurarse de que no queden creditos con id_regla nulo (forzar a 1 por si acaso hay inconsistencias, aunque preferible no, revisar manual si falla)
-- UPDATE creditos SET id_regla = 1 WHERE id_regla IS NULL;

-- Paso 4: Hacer que id_regla en creditos sea NOT NULL
ALTER TABLE creditos ALTER COLUMN id_regla SET NOT NULL;

-- Paso 5: Eliminar id_tasa de creditos
ALTER TABLE creditos DROP CONSTRAINT IF EXISTS creditos_id_tasa_fkey;
ALTER TABLE creditos DROP COLUMN IF EXISTS id_tasa;

-- Paso 6: Eliminar id_tasa de reglas_credito
ALTER TABLE reglas_credito DROP CONSTRAINT IF EXISTS reglas_credito_id_tasa_fkey;
ALTER TABLE reglas_credito DROP COLUMN IF EXISTS id_tasa;
ALTER TABLE reglas_credito ALTER COLUMN porcentaje SET NOT NULL;
