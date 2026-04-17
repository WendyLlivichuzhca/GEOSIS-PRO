-- ============================================================
-- MIGRACION: Base para presupuesto tipo Excel / InterPro
-- Ejecutar UNA sola vez sobre una base de datos ya existente.
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

ALTER TABLE `recursos`
    ADD KEY `idx_recursos_categoria_activo` (`categoria`, `activo`);

ALTER TABLE `rubros`
    ADD KEY `idx_rubros_activo` (`activo`);

ALTER TABLE `rubro_recursos`
    ADD COLUMN `porcentaje` DECIMAL(7,4) DEFAULT NULL COMMENT 'Participacion porcentual dentro del APU' AFTER `costo`,
    ADD COLUMN `distancia` DECIMAL(10,4) DEFAULT NULL COMMENT 'Usado especialmente en transporte' AFTER `porcentaje`,
    ADD COLUMN `orden` INT(11) DEFAULT 0 AFTER `distancia`,
    ADD COLUMN `observacion` VARCHAR(255) DEFAULT NULL AFTER `orden`,
    ADD KEY `idx_rubro_recursos_rubro_categoria_orden` (`rubro_id`, `categoria`, `orden`);

ALTER TABLE `proyectos`
    ADD COLUMN `codigo` VARCHAR(50) DEFAULT NULL AFTER `id`,
    ADD COLUMN `oferente` VARCHAR(255) DEFAULT NULL AFTER `cliente`,
    ADD COLUMN `fecha_oferta` DATE DEFAULT NULL AFTER `fecha_fin`,
    ADD COLUMN `moneda` VARCHAR(10) NOT NULL DEFAULT 'USD' AFTER `fecha_oferta`,
    ADD COLUMN `iva_pct` DECIMAL(5,2) NOT NULL DEFAULT 0.00 AFTER `moneda`,
    ADD KEY `idx_proyectos_estado` (`estado`);

ALTER TABLE `presupuesto_items`
    ADD COLUMN `item_numero` VARCHAR(30) DEFAULT NULL COMMENT 'Ej. 1.2' AFTER `rubro_id`,
    ADD COLUMN `precio_unitario_cerrado` DECIMAL(14,4) DEFAULT NULL COMMENT 'Valor unitario congelado/importado' AFTER `cantidad`,
    ADD COLUMN `precio_total_cerrado` DECIMAL(14,2) DEFAULT NULL COMMENT 'Subtotal congelado/importado' AFTER `precio_unitario_cerrado`,
    ADD COLUMN `origen_hoja` VARCHAR(100) DEFAULT NULL COMMENT 'Hoja de Excel o fuente de importacion' AFTER `precio_total_cerrado`,
    ADD COLUMN `observaciones` TEXT DEFAULT NULL AFTER `origen_hoja`,
    ADD KEY `idx_presupuesto_items_proyecto_orden` (`proyecto_id`, `orden`);

CREATE TABLE IF NOT EXISTS `presupuestos` (
    `id`                INT(11) NOT NULL AUTO_INCREMENT,
    `proyecto_id`       INT(11) NOT NULL,
    `nombre`            VARCHAR(255) NOT NULL DEFAULT 'Presupuesto base',
    `version`           VARCHAR(50) DEFAULT NULL,
    `estado`            ENUM('borrador','vigente','archivado') NOT NULL DEFAULT 'vigente',
    `origen`            ENUM('manual','excel','interpro','otro') NOT NULL DEFAULT 'manual',
    `fecha_presupuesto` DATE DEFAULT NULL,
    `oferente`          VARCHAR(255) DEFAULT NULL,
    `ubicacion`         VARCHAR(255) DEFAULT NULL,
    `moneda`            VARCHAR(10) NOT NULL DEFAULT 'USD',
    `subtotal_directo`  DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    `indirectos_pct`    DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    `indirectos_valor`  DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    `subtotal_oferta`   DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    `iva_pct`           DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    `iva_valor`         DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    `total_general`     DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    `observaciones`     TEXT DEFAULT NULL,
    `created_at`        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at`        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_presupuestos_proyecto_estado` (`proyecto_id`, `estado`),
    FOREIGN KEY (`proyecto_id`) REFERENCES `proyectos`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `presupuesto_capitulos` (
    `id`             INT(11) NOT NULL AUTO_INCREMENT,
    `presupuesto_id` INT(11) NOT NULL,
    `parent_id`      INT(11) DEFAULT NULL,
    `item_numero`    VARCHAR(30) DEFAULT NULL COMMENT 'Ej. 1 o 1.1',
    `codigo`         VARCHAR(50) DEFAULT NULL,
    `nombre`         VARCHAR(500) NOT NULL,
    `tipo`           ENUM('area','capitulo','subcapitulo') NOT NULL DEFAULT 'capitulo',
    `nivel`          TINYINT(2) NOT NULL DEFAULT 1,
    `orden`          INT(11) DEFAULT 0,
    `total`          DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    PRIMARY KEY (`id`),
    KEY `idx_presupuesto_capitulos_padre` (`presupuesto_id`, `parent_id`, `orden`),
    FOREIGN KEY (`presupuesto_id`) REFERENCES `presupuestos`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`parent_id`)      REFERENCES `presupuesto_capitulos`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `presupuesto_lineas` (
    `id`              INT(11) NOT NULL AUTO_INCREMENT,
    `presupuesto_id`  INT(11) NOT NULL,
    `capitulo_id`     INT(11) DEFAULT NULL,
    `item_numero`     VARCHAR(30) DEFAULT NULL COMMENT 'Ej. 1.2',
    `rubro_id`        INT(11) DEFAULT NULL,
    `rubro_codigo`    VARCHAR(50) DEFAULT NULL,
    `descripcion`     VARCHAR(500) NOT NULL,
    `unidad`          VARCHAR(30) DEFAULT NULL,
    `cantidad`        DECIMAL(14,4) NOT NULL DEFAULT 0.0000,
    `precio_unitario` DECIMAL(14,4) NOT NULL DEFAULT 0.0000,
    `precio_total`    DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    `tipo_linea`      ENUM('titulo','rubro','texto') NOT NULL DEFAULT 'rubro',
    `es_opcional`     TINYINT(1) NOT NULL DEFAULT 0,
    `origen_hoja`     VARCHAR(100) DEFAULT NULL,
    `orden`           INT(11) DEFAULT 0,
    `observaciones`   TEXT DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_presupuesto_lineas_presupuesto` (`presupuesto_id`, `orden`),
    KEY `idx_presupuesto_lineas_capitulo` (`capitulo_id`),
    KEY `idx_presupuesto_lineas_rubro` (`rubro_id`),
    FOREIGN KEY (`presupuesto_id`) REFERENCES `presupuestos`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`capitulo_id`)    REFERENCES `presupuesto_capitulos`(`id`) ON DELETE SET NULL,
    FOREIGN KEY (`rubro_id`)       REFERENCES `rubros`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
