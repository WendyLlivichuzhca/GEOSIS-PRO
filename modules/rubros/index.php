<?php
require_once __DIR__ . '/../../config/database.php';

$pageTitle   = 'Rubros APU';
$currentPage = 'rubros';
$db = getDB();

$search = $_GET['search'] ?? '';
$params = ['%' . $search . '%'];
$rubros = $db->prepare("
    SELECT r.*,
           COUNT(rr.id) AS num_recursos,
           COALESCE(SUM(rr.costo), 0) AS costo_directo
    FROM rubros r
    LEFT JOIN rubro_recursos rr ON rr.rubro_id = r.id
    WHERE r.activo = 1 AND r.nombre LIKE ?
    GROUP BY r.id
    ORDER BY r.codigo
");
$rubros->execute($params);
$rubros = $rubros->fetchAll();

include __DIR__ . '/../../includes/header.php';
include __DIR__ . '/../../includes/sidebar.php';
?>

<div id="main">
    <div id="topbar">
        <button class="btn btn-sm btn-light d-md-none" id="menuToggle"><i class="bi bi-list fs-5"></i></button>
        <div>
            <div class="page-title">Rubros APU</div>
            <nav aria-label="breadcrumb"><ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="<?= BASE_URL ?>/index.php">Inicio</a></li>
                <li class="breadcrumb-item active">Rubros APU</li>
            </ol></nav>
        </div>
    </div>

    <div class="p-4">
        <?php if (isset($_GET['ok'])): ?>
        <div class="alert alert-success alert-dismissible fade show">
            <i class="bi bi-check-circle me-2"></i> Operación realizada con éxito.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        <?php endif; ?>

        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center py-3 px-4 flex-wrap gap-2">
                <span><i class="bi bi-list-columns-reverse me-2 text-primary"></i>Catálogo de Rubros APU</span>
                <a href="create.php" class="btn btn-primary btn-sm">
                    <i class="bi bi-plus-lg me-1"></i> Nuevo Rubro
                </a>
            </div>

            <div class="card-body border-bottom pb-3">
                <form method="GET" class="row g-2">
                    <div class="col-12 col-md-6">
                        <input type="text" name="search" class="form-control form-control-sm"
                               placeholder="Buscar rubro..." value="<?= htmlspecialchars($search) ?>">
                    </div>
                    <div class="col-auto">
                        <button type="submit" class="btn btn-sm btn-outline-primary">
                            <i class="bi bi-search"></i> Buscar
                        </button>
                    </div>
                    <div class="col-auto">
                        <a href="?" class="btn btn-sm btn-outline-secondary">
                            <i class="bi bi-x-lg"></i> Limpiar
                        </a>
                    </div>
                </form>
            </div>

            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th class="px-4" style="width:90px">Código</th>
                                <th>Nombre del Rubro</th>
                                <th>Unidad</th>
                                <th class="text-end">Costo Directo</th>
                                <th class="text-end">Indirectos</th>
                                <th class="text-end">Costo Total</th>
                                <th class="text-center" style="width:120px">Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                        <?php if (empty($rubros)): ?>
                            <tr><td colspan="7" class="text-center text-muted py-5">
                                No hay rubros. <a href="create.php">Crear el primero</a>
                            </td></tr>
                        <?php else: foreach ($rubros as $r):
                            $indirectos  = $r['costo_directo'] * ($r['indirectos'] / 100);
                            $costo_total = $r['costo_directo'] + $indirectos;
                        ?>
                            <tr>
                                <td class="px-4 text-muted small"><?= htmlspecialchars($r['codigo'] ?? '-') ?></td>
                                <td class="fw-500"><?= htmlspecialchars($r['nombre']) ?></td>
                                <td><span class="badge bg-secondary bg-opacity-10 text-secondary"><?= htmlspecialchars($r['unidad']) ?></span></td>
                                <td class="text-end">$<?= number_format($r['costo_directo'], 2) ?></td>
                                <td class="text-end text-muted small"><?= $r['indirectos'] ?>%</td>
                                <td class="text-end fw-700 text-primary">$<?= number_format($costo_total, 2) ?></td>
                                <td class="text-center">
                                    <a href="view.php?id=<?= $r['id'] ?>" class="btn btn-sm btn-light" title="Ver APU">
                                        <i class="bi bi-eye text-info"></i>
                                    </a>
                                    <a href="edit.php?id=<?= $r['id'] ?>" class="btn btn-sm btn-light" title="Editar">
                                        <i class="bi bi-pencil-fill text-primary"></i>
                                    </a>
                                    <a href="delete.php?id=<?= $r['id'] ?>" class="btn btn-sm btn-light" title="Eliminar"
                                       onclick="return confirm('¿Eliminar este rubro?')">
                                        <i class="bi bi-trash-fill text-danger"></i>
                                    </a>
                                </td>
                            </tr>
                        <?php endforeach; endif; ?>
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="card-footer text-muted small px-4">
                <?= count($rubros) ?> rubros encontrados
            </div>
        </div>
    </div>
</div>

<?php include __DIR__ . '/../../includes/footer.php'; ?>
