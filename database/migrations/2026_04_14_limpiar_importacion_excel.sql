-- ============================================================
-- LIMPIEZA: Reiniciar la base para volver a importar el Excel
-- Conserva los datos base originales del sistema:
--   - recursos iniciales: IDs 1 al 58
--   - rubros iniciales:   IDs 1 al 37
-- Elimina datos generados por las importaciones de Excel.
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;
START TRANSACTION;

-- 1. Limpiar presupuestos importados y sus detalles
DELETE FROM `presupuesto_lineas`;
DELETE FROM `presupuesto_capitulos`;
DELETE FROM `presupuestos`;
DELETE FROM `presupuesto_items`;

-- 2. Eliminar proyectos creados por la importacion
DELETE FROM `proyectos`
WHERE `descripcion` = 'Importado desde Excel';

-- 3. Eliminar detalle APU de rubros importados
DELETE rr
FROM `rubro_recursos` rr
INNER JOIN `rubros` r ON r.`id` = rr.`rubro_id`
WHERE r.`id` > 37 OR r.`descripcion` = 'Importado desde Excel';

-- 4. Eliminar rubros importados, conservando el catalogo base
DELETE FROM `rubros`
WHERE `id` > 37 OR `descripcion` = 'Importado desde Excel';

-- 5. Eliminar recursos importados, conservando el catalogo base
DELETE FROM `recursos`
WHERE `id` > 58;

-- 6. Reiniciar contadores AUTO_INCREMENT
ALTER TABLE `proyectos` AUTO_INCREMENT = 1;
ALTER TABLE `presupuestos` AUTO_INCREMENT = 1;
ALTER TABLE `presupuesto_capitulos` AUTO_INCREMENT = 1;
ALTER TABLE `presupuesto_lineas` AUTO_INCREMENT = 1;
ALTER TABLE `presupuesto_items` AUTO_INCREMENT = 1;
ALTER TABLE `rubros` AUTO_INCREMENT = 38;
ALTER TABLE `recursos` AUTO_INCREMENT = 59;
ALTER TABLE `rubro_recursos` AUTO_INCREMENT = 1;

COMMIT;
SET FOREIGN_KEY_CHECKS = 1;
