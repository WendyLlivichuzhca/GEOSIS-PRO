<?php
require_once __DIR__ . '/../../config/database.php';

$pageTitle   = 'Nuevo Rubro APU';
$currentPage = 'rubros';
$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $db          = getDB();
    $codigo      = trim($_POST['codigo'] ?? '');
    $nombre      = trim($_POST['nombre'] ?? '');
    $unidad      = trim($_POST['unidad'] ?? '');
    $indirectos  = floatval($_POST['indirectos'] ?? 14.50);
    $descripcion = trim($_POST['descripcion'] ?? '');

    if (!$nombre || !$unidad) {
        $error = 'El nombre y la unidad son obligatorios.';
    } else {
        $stmt = $db->prepare("INSERT INTO rubros (codigo,nombre,unidad,indirectos,descripcion) VALUES (?,?,?,?,?)");
        $stmt->execute([$codigo, $nombre, $unidad, $indirectos, $descripcion]);
        $newId = $db->lastInsertId();
        header("Location: add_recurso.php?rubro_id=$newId&new=1");
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
            <div class="page-title">Nuevo Rubro APU</div>
            <nav aria-label="breadcrumb"><ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="<?= BASE_URL ?>/index.php">Inicio</a></li>
                <li class="breadcrumb-item"><a href="index.php">Rubros</a></li>
                <li class="breadcrumb-item active">Nuevo</li>
            </ol></nav>
        </div>
    </div>

    <div class="p-4">
        <div class="row justify-content-center">
            <div class="col-12 col-md-7">
                <?php if ($error): ?>
                <div class="alert alert-danger"><?= $error ?></div>
                <?php endif; ?>
                <div class="card">
                    <div class="card-header py-3 px-4">
                        <i class="bi bi-plus-circle me-2 text-primary"></i>Datos del Rubro APU
                    </div>
                    <div class="card-body p-4">
                        <form method="POST">
                            <div class="row g-3">
                                <div class="col-md-4">
                                    <label class="form-label fw-500">Código</label>
                                    <input type="text" name="codigo" class="form-control" placeholder="R-038">
                                </div>
                                <div class="col-md-8">
                                    <label class="form-label fw-500">Nombre del Rubro <span class="text-danger">*</span></label>
                                    <input type="text" name="nombre" class="form-control" required
                                           placeholder="Ej: HORMIGÓN SIMPLE 210 KG/CM2">
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label fw-500">Unidad <span class="text-danger">*</span></label>
                                    <select name="unidad" class="form-select" required>
                                        <option value="">Seleccionar...</option>
                                        <option value="M2">M2</option>
                                        <option value="M3">M3</option>
                                        <option value="ML">ML</option>
                                        <option value="KG">KG</option>
                                        <option value="U">U</option>
                                        <option value="GLB">GLB</option>
                                    </select>
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label fw-500">Indirectos y Utilidades (%)</label>
                                    <div class="input-group">
                                        <input type="number" name="indirectos" class="form-control"
                                               step="0.01" min="0" max="100" value="14.50">
                                        <span class="input-group-text">%</span>
                                    </div>
                                </div>
                                <div class="col-12">
                                    <label class="form-label fw-500">Detalle / Descripción</label>
                                    <textarea name="descripcion" class="form-control" rows="2"
                                              placeholder="Descripción adicional del rubro..."></textarea>
                                </div>
                            </div>
                            <div class="alert alert-info mt-3 mb-0 small">
                                <i class="bi bi-info-circle me-1"></i>
                                Después de guardar podrás agregar los recursos (equipos, mano de obra, materiales y transporte).
                            </div>
                            <div class="d-flex gap-2 mt-3">
                                <button type="submit" class="btn btn-primary">
                                    <i class="bi bi-arrow-right me-1"></i> Guardar y Agregar Recursos
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
