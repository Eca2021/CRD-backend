-- Migración para registrar el usuario que ejecuta el pago
ALTER TABLE pagos ADD COLUMN id_usuario INTEGER;
ALTER TABLE pagos ADD CONSTRAINT fk_pagos_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario);
