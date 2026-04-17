<?php
require_once __DIR__ . '/../../config/database.php';

$pageTitle   = 'Nuevo Proyecto';
$currentPage = 'proyectos';
$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $nombre     = trim($_POST['nombre'] ?? '');
    $cliente    = trim($_POST['cliente'] ?? '');
    $ubicacion  = trim($_POST['ubicacion'] ?? '');
    $fecha_ini  = $_POST['fecha_inicio'] ?? null;
    $fecha_fin  = $_POST['fecha_fin']    ?? null;
    $descripcion= trim($_POST['descripcion'] ?? '');
    $estado     = $_POST['estado'] ?? 'activo';

    if (!$nombre) {
        $error = 'El nombre del proyecto es obligatorio.';
    } else {
        $db = getDB();
        $db->prepare("INSERT INTO proyectos (nombre,cliente,ubicacion,fecha_inicio,fecha_fin,descripcion,estado)
                      VALUES (?,?,?,?,?,?,?)")
           ->execute([$nombre,$cliente,$ubicacion,$fecha_ini,$fecha_fin,$descripcion,$estado]);
        $newId = $db->lastInsertId();
        header("Location: view.php?id=$newId&new=1");
        exit;
    }
}

include __DIR__ . '/../../includes/header.php';
include __DIR__ . '/../../includes/sidebar.php';
?>

<div id="main">
    <div id="topbar">
        <button class="btn btn-sm btn-light d-md-none" id="menuToggle"><i class="bi bi-list fs-5"></i></button>
        <div>
            <div class="page-title">Nuevo Proyecto</div>
            <nav aria-label="breadcrumb"><ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="index.php">Proyectos</a></li>
                <li class="breadcrumb-item active">Nuevo</li>
            </ol></nav>
        </div>
    </div>

    <div class="p-4">
        <div class="row justify-content-center">
            <div class="col-12 col-md-8">
                <?php if ($error): ?>
                <div class="alert alert-danger"><?= $error ?></div>
                <?php endif; ?>
                <div class="card">
                    <div class="card-header py-3 px-4">
                        <i class="bi bi-building me-2 text-primary"></i>Datos del Proyecto
                    </div>
                    <div class="card-body p-4">
                        <form method="POST">
                            <div class="row g-3">
                                <div class="col-12">
                                    <label class="form-label fw-500">Nombre del Proyecto <span class="text-danger">*</span></label>
                                    <input type="text" name="nombre" class="form-control" required
                                           placeholder="Ej: Construcción Vivienda Unifamiliar Sector Norte">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-500">Cliente / Propietario</label>
                                    <input type="text" name="cliente" class="form-control"
                                           placeholder="Nombre del cliente">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-500">Ubicación / Sector</label>
                                    <input type="text" name="ubicacion" class="form-control"
                                           placeholder="Ciudad, sector...">
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label fw-500">Fecha Inicio</label>
                                    <input type="date" name="fecha_inicio" class="form-control">
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label fw-500">Fecha Fin (estimada)</label>
                                    <input type="date" name="fecha_fin" class="form-control">
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label fw-500">Estado</label>
                                    <select name="estado" class="form-select">
                                        <option value="activo">Activo</option>
                                        <option value="pausado">Pausado</option>
                                        <option value="terminado">Terminado</option>
                                    </select>
                                </div>
                                <div class="col-12">
                                    <label class="form-label fw-500">Descripción / Notas</label>
                                    <textarea name="descripcion" class="form-control" rows="3"
                                              placeholder="Información adicional del proyecto..."></textarea>
                                </div>
                            </div>
                            <div class="alert alert-info mt-3 mb-0 small">
                                <i class="bi bi-info-circle me-1"></i>
                                Después de crear el proyecto podrás agregar los rubros y cantidades del presupuesto.
                            </div>
                            <div class="d-flex gap-2 mt-3">
                                <button type="submit" class="btn btn-primary">
                                    <i class="bi bi-arrow-right me-1"></i> Crear y Agregar Rubros
                                </button>
                                <a href="index.php" class="btn btn-outline-secondary">Cancelar</a>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<?php include __DIR__ . '/../../includes/footer.php'; ?>
