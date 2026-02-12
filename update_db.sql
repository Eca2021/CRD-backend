-- 1. Modificar tabla detalles_credito
ALTER TABLE detalles_credito ADD COLUMN capital_cuota NUMERIC(15, 2) DEFAULT 0;
ALTER TABLE detalles_credito ADD COLUMN interes_cuota NUMERIC(15, 2) DEFAULT 0;
ALTER TABLE detalles_credito ADD COLUMN cuota_total NUMERIC(15, 2) DEFAULT 0;

-- 2. Crear tabla asientos_contables
CREATE TABLE asientos_contables (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    glosa TEXT,
    id_usuario INTEGER,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
);

-- 3. Crear tabla movimientos_contables
CREATE TABLE movimientos_contables (
    id SERIAL PRIMARY KEY,
    id_asiento INTEGER NOT NULL,
    cuenta_nombre VARCHAR(100) NOT NULL,
    debe NUMERIC(15, 2) DEFAULT 0,
    haber NUMERIC(15, 2) DEFAULT 0,
    FOREIGN KEY (id_asiento) REFERENCES asientos_contables(id) ON DELETE CASCADE
);
