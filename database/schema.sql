-- ============================================================
-- GEOSIS-PRO - Sistema de analisis de precios unitarios
-- Base de datos: corporat_apu_construccion
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";

-- ------------------------------------------------------------
-- Tabla: recursos (materiales, mano de obra, equipos, transporte)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `recursos` (
    `id`          INT(11) NOT NULL AUTO_INCREMENT,
    `codigo`      VARCHAR(100) DEFAULT NULL,
    `descripcion` VARCHAR(500) NOT NULL,
    `unidad`      VARCHAR(30) NOT NULL,
    `precio`      DECIMAL(10,4) NOT NULL DEFAULT 0.0000,
    `categoria`   ENUM('M','N','O','P') NOT NULL COMMENT 'M=Equipos, N=Mano de Obra, O=Materiales, P=Transporte',
    `activo`      TINYINT(1) DEFAULT 1,
    `created_at`  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_recursos_categoria_activo` (`categoria`, `activo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Tabla: rubros (APUs)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `rubros` (
    `id`           INT(11) NOT NULL AUTO_INCREMENT,
    `codigo`       VARCHAR(100) DEFAULT NULL,
    `nombre`       VARCHAR(500) NOT NULL,
    `unidad`       VARCHAR(30) NOT NULL,
    `descripcion`  TEXT DEFAULT NULL,
    `indirectos`   DECIMAL(5,2) NOT NULL DEFAULT 14.50,
    `activo`       TINYINT(1) DEFAULT 1,
    `created_at`   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at`   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_rubros_activo` (`activo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Tabla: rubro_recursos (detalle APU - recursos por rubro)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `rubro_recursos` (
    `id`           INT(11) NOT NULL AUTO_INCREMENT,
    `rubro_id`     INT(11) NOT NULL,
    `recurso_id`   INT(11) NOT NULL,
    `categoria`    ENUM('M','N','O','P') NOT NULL,
    `cantidad`     DECIMAL(10,4) DEFAULT 0.0000,
    `tarifa`       DECIMAL(10,4) DEFAULT 0.0000,
    `rendimiento`  DECIMAL(10,4) DEFAULT 0.0000,
    `costo`        DECIMAL(10,4) DEFAULT 0.0000,
    `porcentaje`   DECIMAL(7,4) DEFAULT NULL COMMENT 'Participacion porcentual dentro del APU',
    `distancia`    DECIMAL(10,4) DEFAULT NULL COMMENT 'Usado especialmente en transporte',
    `orden`        INT(11) DEFAULT 0,
    `observacion`  VARCHAR(255) DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_rubro_recursos_rubro_categoria_orden` (`rubro_id`, `categoria`, `orden`),
    FOREIGN KEY (`rubro_id`)   REFERENCES `rubros`(`id`)   ON DELETE CASCADE,
    FOREIGN KEY (`recurso_id`) REFERENCES `recursos`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Tabla: proyectos
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `proyectos` (
    `id`           INT(11) NOT NULL AUTO_INCREMENT,
    `codigo`       VARCHAR(100) DEFAULT NULL,
    `nombre`       VARCHAR(500) NOT NULL,
    `cliente`      VARCHAR(255) DEFAULT NULL,
    `oferente`     VARCHAR(255) DEFAULT NULL,
    `ubicacion`    VARCHAR(255) DEFAULT NULL,
    `fecha_inicio` DATE DEFAULT NULL,
    `fecha_fin`    DATE DEFAULT NULL,
    `fecha_oferta` DATE DEFAULT NULL,
    `moneda`       VARCHAR(10) NOT NULL DEFAULT 'USD',
    `iva_pct`      DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    `descripcion`  TEXT DEFAULT NULL,
    `estado`       ENUM('activo','pausado','terminado') DEFAULT 'activo',
    `created_at`   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_proyectos_estado` (`estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Tabla: presupuesto_items (modo simplificado actual)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `presupuesto_items` (
    `id`           INT(11) NOT NULL AUTO_INCREMENT,
    `proyecto_id`  INT(11) NOT NULL,
    `rubro_id`     INT(11) NOT NULL,
    `item_numero`  VARCHAR(30) DEFAULT NULL COMMENT 'Ej. 1.2',
    `cantidad`     DECIMAL(10,4) NOT NULL DEFAULT 1.0000,
    `precio_unitario_cerrado` DECIMAL(14,4) DEFAULT NULL COMMENT 'Valor unitario congelado/importado',
    `precio_total_cerrado`    DECIMAL(14,2) DEFAULT NULL COMMENT 'Subtotal congelado/importado',
    `origen_hoja`  VARCHAR(100) DEFAULT NULL COMMENT 'Hoja de Excel o fuente de importacion',
    `observaciones` TEXT DEFAULT NULL,
    `orden`        INT(11) DEFAULT 0,
    PRIMARY KEY (`id`),
    KEY `idx_presupuesto_items_proyecto_orden` (`proyecto_id`, `orden`),
    FOREIGN KEY (`proyecto_id`) REFERENCES `proyectos`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`rubro_id`)    REFERENCES `rubros`(`id`)    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Tabla: presupuestos (cabecera avanzada por proyecto/version)
-- Permite manejar varias versiones del presupuesto de un mismo
-- proyecto, como en exportaciones tipo InterPro o Excel.
-- ------------------------------------------------------------
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

-- ------------------------------------------------------------
-- Tabla: presupuesto_capitulos
-- Estructura jerarquica para areas, capitulos y subcapitulos.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `presupuesto_capitulos` (
    `id`             INT(11) NOT NULL AUTO_INCREMENT,
    `presupuesto_id` INT(11) NOT NULL,
    `parent_id`      INT(11) DEFAULT NULL,
    `item_numero`    VARCHAR(30) DEFAULT NULL COMMENT 'Ej. 1 o 1.1',
    `codigo`         VARCHAR(100) DEFAULT NULL,
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

-- ------------------------------------------------------------
-- Tabla: presupuesto_lineas
-- Registra las lineas detalladas del presupuesto importado o
-- elaborado manualmente, incluyendo precios congelados.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `presupuesto_lineas` (
    `id`              INT(11) NOT NULL AUTO_INCREMENT,
    `presupuesto_id`  INT(11) NOT NULL,
    `capitulo_id`     INT(11) DEFAULT NULL,
    `item_numero`     VARCHAR(30) DEFAULT NULL COMMENT 'Ej. 1.2',
    `rubro_id`        INT(11) DEFAULT NULL,
    `rubro_codigo`    VARCHAR(100) DEFAULT NULL,
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

-- ============================================================
-- DATOS INICIALES - Recursos base del PDF
-- ============================================================

INSERT INTO `recursos` (`codigo`, `descripcion`, `unidad`, `precio`, `categoria`) VALUES
-- MANO DE OBRA (N)
('MO-001', 'MAESTRO MAYOR (E.O.C1)',           'HR', 3.38, 'N'),
('MO-002', 'PEON (E.O.E2)',                    'HR', 3.01, 'N'),
('MO-003', 'ALBAÑIL (E.O.D2)',                 'HR', 3.05, 'N'),
('MO-004', 'FIERRERO (E.O.D2)',                'HR', 3.05, 'N'),
('MO-005', 'OPERADOR DE EQUIPO LIVIANO',       'HR', 3.05, 'N'),
('MO-006', 'CARPINTERO (E.O.D2)',              'HR', 3.05, 'N'),
('MO-007', 'PLOMERO (E.O.D2)',                 'HR', 3.05, 'N'),
('MO-008', 'ELECTRICISTA (E.O.D2)',            'HR', 3.05, 'N'),
('MO-009', 'PINTOR (E.O.D2)',                  'HR', 3.05, 'N'),
('MO-010', 'INST. REVESTIMIENTO EN GEN.',      'HR', 3.05, 'N'),
-- EQUIPOS (M)
('EQ-001', 'HERRAMIENTAS MENORES 5% MO',       'GLB', 0.00, 'M'),
('EQ-002', 'CONCRETERA',                        'HR', 3.70, 'M'),
('EQ-003', 'VIBRADOR',                          'HR', 2.50, 'M'),
('EQ-004', 'COMPACTADOR',                       'HR', 3.00, 'M'),
('EQ-005', 'CORTADORA DE HIERRO',               'HR', 1.00, 'M'),
('EQ-006', 'CIZALLA',                           'HR', 0.50, 'M'),
('EQ-007', 'SOLDADORA',                         'HR', 1.50, 'M'),
('EQ-008', 'CONO DE ABRAMS',                    'HR', 0.18, 'M'),
('EQ-009', 'CILINDRO DE ENSAYO',                'HR', 0.30, 'M'),
-- MATERIALES (O)
('MA-001', 'CEMENTO',                          'SACO', 6.83, 'O'),
('MA-002', 'ARENA',                            'M3',   4.00, 'O'),
('MA-003', 'RIPIO',                            'M3',  11.00, 'O'),
('MA-004', 'AGUA',                             'M3',   1.00, 'O'),
('MA-005', 'LASTRE',                           'M3',   1.50, 'O'),
('MA-006', 'PIEDRA BOLA',                      'M3',  10.00, 'O'),
('MA-007', 'HIERRO ESTRUCTURAL',               'KG',   1.14, 'O'),
('MA-008', 'ALAMBRE NEGRO #18',                'KG',   1.70, 'O'),
('MA-009', 'TABLA DE ENCOFRADO 20CMX2.40M',   'U',    3.50, 'O'),
('MA-010', 'CUARTONES DE 5V',                  'U',    2.20, 'O'),
('MA-011', 'CLAVOS DE 2½"',                   'KG',   1.30, 'O'),
('MA-012', 'PIOLA',                            'ROLLO',1.70, 'O'),
('MA-013', 'LADRILLO TIPO MALETA 6X15X26',    'U',    0.14, 'O'),
('MA-014', 'LADRILLO BURRITO',                 'U',    0.13, 'O'),
('MA-015', 'DIESEL',                           'GALON',1.10, 'O'),
('MA-016', 'CEMENTO PORTLAND',                 'SACO', 6.83, 'O'),
('MA-017', 'PORCELANA',                        'KG',   1.75, 'O'),
('MA-018', 'CERAMICA 30X30',                   'M2',   8.50, 'O'),
('MA-019', 'PINTURA',                          'GAL',  8.50, 'O'),
('MA-020', 'EMPASTE',                          'KG',   1.50, 'O'),
('MA-021', 'LIJA',                             'PLIEGO',1.00,'O'),
('MA-022', 'RESINA',                           'GALON',5.50, 'O'),
('MA-023', 'CUBIERTA GALVALUME E=0.25MM',      'M2',   7.30, 'O'),
('MA-024', 'CORREA METALICA 60X30X10X1.5MM',  'U',    9.50, 'O'),
('MA-025', 'SOLDADURA E6011',                  'KG',   2.52, 'O'),
('MA-026', 'PINTURA ANTICORROSIVA',            'GALON',13.50,'O'),
('MA-027', 'TUBERIA PVC 110MM',                'M',    3.25, 'O'),
('MA-028', 'CODO PVC 110MM',                   'U',    1.95, 'O'),
('MA-029', 'YEE 110 A 50MM',                   'U',    2.12, 'O'),
('MA-030', 'TUBO PVC 50MM',                    'U',    3.48, 'O'),
('MA-031', 'TUBERIA PVC ROSCABLE 1/2"',        'U',    7.50, 'O'),
('MA-032', 'CABLE AWG #12',                    'ML',   0.55, 'O'),
('MA-033', 'CABLE AWG #10',                    'ML',   0.95, 'O'),
('MA-034', 'INODORO TANQUE BAJO',              'U',   50.00, 'O'),
('MA-035', 'LAVAMANOS BLANCO',                 'U',   13.00, 'O'),
-- TRANSPORTE (P)
('TR-001', 'TRANSPORTE ARENA',                 'M3',   4.50, 'P'),
('TR-002', 'TRANSPORTE RIPIO',                 'M3',   4.50, 'P'),
('TR-003', 'TRANSPORTE LASTRE',                'M3',   4.50, 'P'),
('TR-004', 'TRANSPORTE PIEDRA BOLA',           'M3',   4.50, 'P');

-- ============================================================
-- RUBROS DEL PDF (37 rubros)
-- ============================================================
INSERT INTO `rubros` (`codigo`, `nombre`, `unidad`, `indirectos`) VALUES
('R-001',  'REPLANTEO Y TRAZADO',                                          'M2',  14.50),
('R-002',  'EXCAVACIÓN DE CIMIENTOS',                                      'M3',  14.50),
('R-003',  'RELLENO COMPACTADO - LASTRE',                                  'M3',  14.50),
('R-004',  'RELLENO COMPACTADO CON PIEDRA BOLA',                           'M3',  14.50),
('R-005',  'ACERO DE REFUERZO Fy=4200KG/CM2',                             'KG',  14.50),
('R-006',  'HORMIGÓN SIMPLE 180KG/CM2 PARA REPLANTILLO',                   'M3',  14.50),
('R-007',  'MURO DE HORMIGÓN CICLÓPEO F\'C 180 KG/CM2',                    'M3',  14.50),
('R-008',  'HORMIGÓN SIMPLE 210KG/CM2 PLINTO',                             'M3',  14.50),
('R-009',  'HORMIGÓN SIMPLE 210KG/CM2 COLUMNAS',                           'M3',  14.50),
('R-010',  'HORMIGÓN SIMPLE 210KG/CM2 RIOSTRAS',                           'M3',  14.50),
('R-011',  'HORMIGÓN SIMPLE 210KG/CM2 PARA VIGA',                          'M3',  14.50),
('R-012',  'HORMIGÓN SIMPLE 210KG/CM2 PARA PILARETES',                     'M3',  14.50),
('R-013',  'HORMIGÓN SIMPLE 210KG/CM2 PARA DINTELES',                      'M3',  14.50),
('R-014',  'PAREDES DE LADRILLO MALETA - MAMPOSTERIA',                     'M2',  14.50),
('R-015',  'MESÓN DE COCINA INCLUYE PATAS LOSA Y ENLUCIDO',               'ML',  14.50),
('R-016',  'ENLUCIDO INTERIOR-EXTERIOR Y FILOS - DOSIFICACION 1:3',       'M2',  14.50),
('R-017',  'CUBIERTA DE GALVALUME E=25MM CON CORREAS METALICAS',          'M2',  14.50),
('R-018',  'CONTRAPISO HORMIGON SIMPLE 180 KG/CM2 e=7CM',                 'M2',  14.50),
('R-019',  'VENTANA PVC O ALUMINIO CON VIDRIO E=4MM Y MALLA ANTIMOSQUITO','M2',  14.50),
('R-020',  'PUERTA TAMBOR LAUREL 0.70x2.00 BAÑO CON CHAPA',              'U',   14.50),
('R-021',  'PUERTA TAMBOR LAUREL 0.80x2.00 DORMITORIO PRINCIPAL',        'U',   14.50),
('R-022',  'PUERTA TAMBOR LAUREL 0.90x2.00 ENTRADA PRINCIPAL',           'U',   14.50),
('R-023',  'PUERTA METALICA 0.80x2.00 POSTERIOR CON CERRADURA',          'U',   14.50),
('R-024',  'PUNTO DE AGUA SERVIDA 110MM',                                  'U',   14.50),
('R-025',  'PUNTO DE AGUA SERVIDA 50MM',                                   'U',   14.50),
('R-026',  'CAJA DE REGISTRO 40X40 CON TAPA SIN MARCO METALICO',         'U',   14.50),
('R-027',  'PUNTO DE AGUA POTABLE INCLUYE LLAVE DE CONTROL',              'U',   14.50),
('R-028',  'INODORO TANQUE BAJO',                                          'U',   14.50),
('R-029',  'LAVAMANOS COMERCIAL BLANCO',                                   'U',   14.50),
('R-030',  'DUCHA SENCILLA INCLUYE LLAVE CAMPANOLA Y REJILLA',            'U',   14.50),
('R-031',  'LAVAPLATOS 1 POZO CON ESCURRIDERA',                           'U',   14.50),
('R-032',  'PUNTOS DE LUZ',                                                'U',   14.50),
('R-033',  'PUNTO DE TOMACORRIENTE 110V',                                  'U',   14.50),
('R-034',  'PUNTO DE TOMACORRIENTE 220V',                                  'U',   14.50),
('R-035',  'CAJA DE BREAKER 6P CON CONEXIÓN A TIERRA',                   'U',   14.50),
('R-036',  'PINTURA EXTERIOR FACHADA INCLUYE EMPASTE',                    'M2',  14.50),
('R-037',  'CERAMICA 30X30 EN BAÑO Y DUCHA',                              'M2',  14.50);
