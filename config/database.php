<?php
// ============================================================
// GEOSIS-PRO - Configuracion de base de datos
// ============================================================

define('DB_HOST',     'localhost');
define('DB_NAME',     'corporat_apu_construccion');
define('DB_USER',     'corporat_apu_construccion');
define('DB_PASS',     'LmBl#R79du_p9V@w');
define('DB_CHARSET',  'utf8mb4');

// URL base del sistema (cambiar en producción)
define('BASE_URL', '/GEOSIS-PRO');

function getDB() {
    static $pdo = null;
    if ($pdo === null) {
        try {
            $dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=" . DB_CHARSET;
            $pdo = new PDO($dsn, DB_USER, DB_PASS, [
                PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES   => false,
            ]);
        } catch (PDOException $e) {
            die(json_encode(['error' => 'Error de conexión: ' . $e->getMessage()]));
        }
    }
    return $pdo;
}
