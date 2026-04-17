-- ============================================================
-- RESET DE DATOS
-- Vacía la base para volver a importar desde cero.
-- No elimina tablas, solo borra registros y reinicia IDs.
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

DELETE FROM `presupuesto_lineas`;
DELETE FROM `presupuesto_capitulos`;
DELETE FROM `presupuestos`;
DELETE FROM `presupuesto_items`;
DELETE FROM `rubro_recursos`;
DELETE FROM `rubros`;
DELETE FROM `recursos`;
DELETE FROM `proyectos`;

ALTER TABLE `presupuesto_lineas` AUTO_INCREMENT = 1;
ALTER TABLE `presupuesto_capitulos` AUTO_INCREMENT = 1;
ALTER TABLE `presupuestos` AUTO_INCREMENT = 1;
ALTER TABLE `presupuesto_items` AUTO_INCREMENT = 1;
ALTER TABLE `rubro_recursos` AUTO_INCREMENT = 1;
ALTER TABLE `rubros` AUTO_INCREMENT = 1;
ALTER TABLE `recursos` AUTO_INCREMENT = 1;
ALTER TABLE `proyectos` AUTO_INCREMENT = 1;

SET FOREIGN_KEY_CHECKS = 1;
