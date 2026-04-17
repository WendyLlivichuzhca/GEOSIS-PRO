<?php
require_once __DIR__ . '/../../config/database.php';

$db  = getDB();
$id  = intval($_GET['id'] ?? 0);
$p   = $db->prepare("SELECT * FROM proyectos WHERE id=?");
$p->execute([$id]); $p = $p->fetch();
if (!$p) { header('Location: index.php'); exit; }

$pageTitle   = 'Editar Proyecto';
$currentPage = 'proyectos';
$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $nombre    = trim($_POST['nombre'] ?? '');
    $cliente   = trim($_POST['cliente'] ?? '');
    $ubicacion = trim($_POST['ubicacion'] ?? '');
    $fecha_ini = $_POST['fecha_inicio'] ?? null;
    $fecha_fin = $_POST['fecha_fin']    ?? null;
    $desc      = trim($_POST['descripcion'] ?? '');
    $estado    = $_POST['estado'] ?? 'activo';

    if (!$nombre) { $error = 'El nombre es obligatorio.'; }
    else {
        $db->prepare("UPDATE proyectos SET nombre=?,cliente=?,ubicacion=?,fecha_inicio=?,fecha_fin=?,descripcion=?,estado=? WHERE id=?")
           ->execute([$nombre,$cliente,$ubicacion,$fecha_ini,$fecha_fin,$desc,$estado,$id]);
        header('Location: index.php?ok=edit'); exit;
    }
}

include __DIR__ . '/../../includes/header.php';
include __DIR__ . '/../../includes/sidebar.php';
?>
<div id="main">
    <div id="topbar">
        <button class="btn btn-sm btn-light d-md-none" id="menuToggle"><i class="bi bi-list fs-5"></i></button>
        <div><div class="page-title">Editar Proyecto</div></div>
    </div>
    <div class="p-4">
        <div class="row justify-content-center"><div class="col-12 col-md-8">
            <?php if ($error): ?><div class="alert alert-danger"><?= $error ?></div><?php endif; ?>
            <div class="card">
                <div class="card-header py-3 px-4"><i class="bi bi-pencil me-2 text-primary"></i>Editar Proyecto</div>
                <div class="card-body p-4">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-12">
                                <label class="form-label fw-500">Nombre <span class="text-danger">*</span></label>
                                <input type="text" name="nombre" class="form-control" required value="<?= htmlspecialchars($p['nombre']) ?>">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-500">Cliente</label>
                                <input type="text" name="cliente" class="form-control" value="<?= htmlspecialchars($p['cliente'] ?? '') ?>">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-500">Ubicación</label>
                                <input type="text" name="ubicacion" class="form-control" value="<?= htmlspecialchars($p['ubicacion'] ?? '') ?>">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label fw-500">Fecha Inicio</label>
                                <input type="date" name="fecha_inicio" class="form-control" value="<?= $p['fecha_inicio'] ?>">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label fw-500">Fecha Fin</label>
                                <input type="date" name="fecha_fin" class="form-control" value="<?= $p['fecha_fin'] ?>">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label fw-500">Estado</label>
                                <select name="estado" class="form-select">
                                    <option value="activo"    <?= $p['estado']==='activo'   ?'selected':'' ?>>Activo</option>
                                    <option value="pausado"   <?= $p['estado']==='pausado'  ?'selected':'' ?>>Pausado</option>
                                    <option value="terminado" <?= $p['estado']==='terminado'?'selected':'' ?>>Terminado</option>
                                </select>
                            </div>
                            <div class="col-12">
                                <label class="form-label fw-500">Descripción</label>
                                <textarea name="descripcion" class="form-control" rows="3"><?= htmlspecialchars($p['descripcion'] ?? '') ?></textarea>
                            </div>
                        </div>
                        <div class="d-flex gap-2 mt-4">
                            <button type="submit" class="btn btn-primary"><i class="bi bi-check-lg me-1"></i>Actualizar</button>
                            <a href="index.php" class="btn btn-outline-secondary">Cancelar</a>
                        </div>
                    </form>
                </div>
            </div>
        </div></div>
    </div>
</div>
<?php include __DIR__ . '/../../includes/footer.php'; ?>
