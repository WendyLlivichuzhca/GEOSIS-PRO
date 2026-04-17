<?php
require_once __DIR__ . '/../../config/database.php';

$pageTitle   = 'Recursos';
$currentPage = 'recursos';

$db = getDB();

// Filtros
$cat    = $_GET['cat']    ?? '';
$search = $_GET['search'] ?? '';

$where  = ['r.activo = 1'];
$params = [];
if ($cat)    { $where[] = 'r.categoria = ?'; $params[] = $cat; }
if ($search) { $where[] = 'r.descripcion LIKE ?'; $params[] = "%$search%"; }

$sql = "SELECT * FROM recursos r WHERE " . implode(' AND ', $where) . " ORDER BY r.categoria, r.descripcion";
$stmt = $db->prepare($sql);
$stmt->execute($params);
$recursos = $stmt->fetchAll();

$catInfo = [
    'M' => ['label'=>'Equipos',      'color'=>'primary'],
    'N' => ['label'=>'Mano de Obra', 'color'=>'success'],
    'O' => ['label'=>'Materiales',   'color'=>'warning'],
    'P' => ['label'=>'Transporte',   'color'=>'info'],
];

include __DIR__ . '/../../includes/header.php';
include __DIR__ . '/../../includes/sidebar.php';
?>

<div id="main">
    <div id="topbar">
        <button class="btn btn-sm btn-light d-md-none" id="menuToggle"><i class="bi bi-list fs-5"></i></button>
        <div>
            <div class="page-title">Recursos</div>
            <nav aria-label="breadcrumb"><ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="<?= BASE_URL ?>/index.php">Inicio</a></li>
                <li class="breadcrumb-item active">Recursos</li>
            </ol></nav>
        </div>
    </div>

    <div class="p-4">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center py-3 px-4 flex-wrap gap-2">
                <span><i class="bi bi-box-seam-fill me-2 text-success"></i>Catálogo de Recursos</span>
                <a href="<?= BASE_URL ?>/modules/recursos/create.php" class="btn btn-primary btn-sm">
                    <i class="bi bi-plus-lg me-1"></i> Nuevo Recurso
                </a>
            </div>

            <!-- Filtros -->
            <div class="card-body border-bottom pb-3">
                <form method="GET" class="row g-2">
                    <div class="col-12 col-md-5">
                        <input type="text" name="search" class="form-control form-control-sm"
                               placeholder="Buscar recurso..." value="<?= htmlspecialchars($search) ?>">
                    </div>
                    <div class="col-6 col-md-3">
                        <select name="cat" class="form-select form-select-sm">
                            <option value="">Todas las categorías</option>
                            <?php foreach ($catInfo as $k => $v): ?>
                            <option value="<?= $k ?>" <?= $cat === $k ? 'selected' : '' ?>>
                                <?= $v['label'] ?>
                            </option>
                            <?php endforeach; ?>
                        </select>
                    </div>
                    <div class="col-6 col-md-2">
                        <button type="submit" class="btn btn-sm btn-outline-primary w-100">
                            <i class="bi bi-search"></i> Filtrar
                        </button>
                    </div>
                    <div class="col-6 col-md-2">
                        <a href="?" class="btn btn-sm btn-outline-secondary w-100">
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
                                <th class="px-4" style="width:80px">Código</th>
                                <th>Descripción</th>
                                <th>Categoría</th>
                                <th>Unidad</th>
                                <th class="text-end">Precio</th>
                                <th class="text-center" style="width:110px">Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                        <?php if (empty($recursos)): ?>
                            <tr><td colspan="6" class="text-center text-muted py-5">
                                No se encontraron recursos.
                            </td></tr>
                        <?php else: foreach ($recursos as $r):
                            $ci = $catInfo[$r['categoria']] ?? ['label'=>$r['categoria'],'color'=>'secondary'];
                        ?>
                            <tr>
                                <td class="px-4 text-muted small"><?= htmlspecialchars($r['codigo'] ?? '-') ?></td>
                                <td class="fw-500"><?= htmlspecialchars($r['descripcion']) ?></td>
                                <td>
                                    <span class="badge bg-<?= $ci['color'] ?> bg-opacity-15 text-<?= $ci['color'] ?> badge-categoria">
                                        <?= $ci['label'] ?>
                                    </span>
                                </td>
                                <td><?= htmlspecialchars($r['unidad']) ?></td>
                                <td class="text-end fw-600">$<?= number_format($r['precio'], 4) ?></td>
                                <td class="text-center">
                                    <a href="edit.php?id=<?= $r['id'] ?>" class="btn btn-sm btn-light" title="Editar">
                                        <i class="bi bi-pencil-fill text-primary"></i>
                                    </a>
                                    <a href="delete.php?id=<?= $r['id'] ?>"
                                       class="btn btn-sm btn-light" title="Eliminar"
                                       onclick="return confirm('¿Eliminar este recurso?')">
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
                <?= count($recursos) ?> recursos encontrados
            </div>
        </div>
    </div>
</div>

<?php include __DIR__ . '/../../includes/footer.php'; ?>
