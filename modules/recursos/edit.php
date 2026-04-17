<?php
require_once __DIR__ . '/../../config/database.php';

$pageTitle   = 'Editar Recurso';
$currentPage = 'recursos';
$db = getDB();

$id = intval($_GET['id'] ?? 0);
$recurso = $db->prepare("SELECT * FROM recursos WHERE id=?");
$recurso->execute([$id]);
$recurso = $recurso->fetch();
if (!$recurso) { header('Location: index.php'); exit; }

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $codigo      = trim($_POST['codigo'] ?? '');
    $descripcion = trim($_POST['descripcion'] ?? '');
    $unidad      = trim($_POST['unidad'] ?? '');
    $precio      = floatval($_POST['precio'] ?? 0);
    $categoria   = $_POST['categoria'] ?? '';

    if (!$descripcion || !$unidad || !$categoria) {
        $error = 'Completa todos los campos obligatorios.';
    } else {
        $stmt = $db->prepare("UPDATE recursos SET codigo=?,descripcion=?,unidad=?,precio=?,categoria=? WHERE id=?");
        $stmt->execute([$codigo, $descripcion, $unidad, $precio, $categoria, $id]);
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
            <div class="page-title">Editar Recurso</div>
            <nav aria-label="breadcrumb"><ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="<?= BASE_URL ?>/index.php">Inicio</a></li>
                <li class="breadcrumb-item"><a href="index.php">Recursos</a></li>
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
                        <i class="bi bi-pencil-fill me-2 text-primary"></i>Editar Recurso #<?= $id ?>
                    </div>
                    <div class="card-body p-4">
                        <form method="POST">
                            <div class="row g-3">
                                <div class="col-md-4">
                                    <label class="form-label fw-500">Código</label>
                                    <input type="text" name="codigo" class="form-control"
                                           value="<?= htmlspecialchars($recurso['codigo'] ?? '') ?>">
                                </div>
                                <div class="col-md-8">
                                    <label class="form-label fw-500">Descripción <span class="text-danger">*</span></label>
                                    <input type="text" name="descripcion" class="form-control" required
                                           value="<?= htmlspecialchars($recurso['descripcion']) ?>">
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label fw-500">Categoría <span class="text-danger">*</span></label>
                                    <select name="categoria" class="form-select" required>
                                        <option value="M" <?= $recurso['categoria']==='M'?'selected':'' ?>>M - Equipos</option>
                                        <option value="N" <?= $recurso['categoria']==='N'?'selected':'' ?>>N - Mano de Obra</option>
                                        <option value="O" <?= $recurso['categoria']==='O'?'selected':'' ?>>O - Materiales</option>
                                        <option value="P" <?= $recurso['categoria']==='P'?'selected':'' ?>>P - Transporte</option>
                                    </select>
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label fw-500">Unidad <span class="text-danger">*</span></label>
                                    <input type="text" name="unidad" class="form-control" required
                                           value="<?= htmlspecialchars($recurso['unidad']) ?>">
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label fw-500">Precio Unit.</label>
                                    <div class="input-group">
                                        <span class="input-group-text">$</span>
                                        <input type="number" name="precio" class="form-control" step="0.0001" min="0"
                                               value="<?= $recurso['precio'] ?>">
                                    </div>
                                </div>
                            </div>
                            <div class="d-flex gap-2 mt-4">
                                <button type="submit" class="btn btn-primary">
                                    <i class="bi bi-check-lg me-1"></i> Actualizar
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
