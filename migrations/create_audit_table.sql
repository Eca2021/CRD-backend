CREATE TABLE public.historial_pagos_audit (
    id_audit SERIAL PRIMARY KEY,
    id_pago INTEGER, -- Relación con el pago original (sin FK estricta para persistencia si se borra el pago, aunque aquí no se borra)
    id_usuario INTEGER REFERENCES public.usuarios(id_usuario), -- Quién hizo la acción
    accion VARCHAR(20), -- 'CREACION', 'ANULACION', 'MODIFICACION'
    fecha_accion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Datos capturados en el momento (Snapshot)
    monto_registrado NUMERIC(15,2),
    id_detalle_credito INTEGER,
    estado_pago_momento VARCHAR(10),
    
    -- Para auditoría técnica
    direccion_ip VARCHAR(45), -- Opcional, para saber desde dónde pagó
    observacion TEXT -- Ejemplo: "Se anula por error en comprobante"
);
