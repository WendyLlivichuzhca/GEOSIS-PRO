-- ============================================================
-- MIGRACION: Ampliar longitud de campos codigo para importacion
-- Ejecutar una sola vez si aparece "Data too long for column codigo"
-- ============================================================

ALTER TABLE `recursos`
    MODIFY COLUMN `codigo` VARCHAR(100) DEFAULT NULL;

ALTER TABLE `rubros`
    MODIFY COLUMN `codigo` VARCHAR(100) DEFAULT NULL;

ALTER TABLE `proyectos`
    MODIFY COLUMN `codigo` VARCHAR(100) DEFAULT NULL;

ALTER TABLE `presupuesto_capitulos`
    MODIFY COLUMN `codigo` VARCHAR(100) DEFAULT NULL;

ALTER TABLE `presupuesto_lineas`
    MODIFY COLUMN `rubro_codigo` VARCHAR(100) DEFAULT NULL;
