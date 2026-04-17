<?php
require_once __DIR__ . '/../../config/database.php';

$db    = getDB();
$id    = intval($_GET['id'] ?? 0);
$rubro = $db->prepare("SELECT * FROM rubros WHERE id=?");
$rubro->execute([$id]);
$rubro = $rubro->fetch();
if (!$rubro) { header('Location: index.php'); exit; }

$pageTitle   = 'Editar Rubro';
$currentPage = 'rubros';
$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $codigo     = trim($_POST['codigo'] ?? '');
    $nombre     = trim($_POST['nombre'] ?? '');
    $unidad     = trim($_POST['unidad'] ?? '');
    $indirectos = floatval($_POST['indirectos'] ?? 14.50);
    $descripcion= trim($_POST['descripcion'] ?? '');

    if (!$nombre || !$unidad) {
        $error = 'Nombre y unidad son obligatorios.';
    } else {
        $db->prepare("UPDATE rubros SET codigo=?,nombre=?,unidad=?,indirectos=?,descripcion=? WHERE id=?")
           ->execute([$codigo,$nombre,$unidad,$indirectos,$descripcion,$id]);
        header('Location: index.php?ok=edit');
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
            <div class="page-title">Editar Rubro</div>
            <nav aria-label="breadcrumb"><ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="index.php">Rubros</a></li>
                <li class="breadcrumb-item active">Editar</li>
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
                        <i class="bi bi-pencil-fill me-2 text-primary"></i>Editar Rubro APU
                    </div>
                    <div class="card-body p-4">
                        <form method="POST">
                            <div class="row g-3">
                                <div class="col-md-4">
                                    <label class="form-label fw-500">Código</label>
                                    <input type="text" name="codigo" class="form-control"
                                           value="<?= htmlspecialchars($rubro['codigo'] ?? '') ?>">
                                </div>
                                <div class="col-md-8">
                                    <label class="form-label fw-500">Nombre <span class="text-danger">*</span></label>
                                    <input type="text" name="nombre" class="form-control" required
                                           value="<?= htmlspecialchars($rubro['nombre']) ?>">
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label fw-500">Unidad <span class="text-danger">*</span></label>
                                    <select name="unidad" class="form-select" required>
                                        <?php foreach (['M2','M3','ML','KG','U','GLB','HR'] as $u): ?>
                                        <option value="<?= $u ?>" <?= $rubro['unidad']===$u?'selected':'' ?>><?= $u ?></option>
                                        <?php endforeach; ?>
                                    </select>
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label fw-500">Indirectos (%)</label>
                                    <div class="input-group">
                                        <input type="number" name="indirectos" class="form-control"
                                               step="0.01" min="0" max="100"
                                               value="<?= $rubro['indirectos'] ?>">
                                        <span class="input-group-text">%</span>
                                    </div>
                                </div>
                                <div class="col-12">
                                    <label class="form-label fw-500">Descripción</label>
                                    <textarea name="descripcion" class="form-control" rows="2"><?= htmlspecialchars($rubro['descripcion'] ?? '') ?></textarea>
                                </div>
                            </div>
                            <div class="d-flex gap-2 mt-4">
                                <button type="submit" class="btn btn-primary">
                                    <i class="bi bi-check-lg me-1"></i> Actualizar
                                </button>
                                <a href="add_recurso.php?rubro_id=<?= $id ?>" class="btn btn-outline-primary">
                                    <i class="bi bi-box-seam me-1"></i> Gestionar Recursos
                                </a>
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
