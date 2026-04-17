<?php
require_once __DIR__ . '/../../config/database.php';

$pageTitle   = 'Proyectos';
$currentPage = 'proyectos';
$db = getDB();

$proyectos = $db->query("
    SELECT p.*,
           COUNT(pi.id)        AS num_rubros,
           COALESCE(SUM(
               (SELECT (SUM(rr.costo)*(1+r.indirectos/100)) FROM rubro_recursos rr
                JOIN rubros r ON r.id=rr.rubro_id WHERE r.id=pi.rubro_id)
               * pi.cantidad
           ),0) AS total_presupuesto
    FROM proyectos p
    LEFT JOIN presupuesto_items pi ON pi.proyecto_id = p.id
    GROUP BY p.id
    ORDER BY p.created_at DESC
")->fetchAll();

include __DIR__ . '/../../includes/header.php';
include __DIR__ . '/../../includes/sidebar.php';
?>

<div id="main">
    <div id="topbar">
        <button class="btn btn-sm btn-light d-md-none" id="menuToggle"><i class="bi bi-list fs-5"></i></button>
        <div>
            <div class="page-title">Proyectos</div>
            <nav aria-label="breadcrumb"><ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="<?= BASE_URL ?>/index.php">Inicio</a></li>
                <li class="breadcrumb-item active">Proyectos</li>
            </ol></nav>
        </div>
    </div>

    <div class="p-4">
        <?php if (isset($_GET['ok'])): ?>
        <div class="alert alert-success alert-dismissible fade show">
            <i class="bi bi-check-circle me-2"></i>Operación realizada correctamente.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        <?php endif; ?>

        <div class="d-flex justify-content-between align-items-center mb-3">
            <h5 class="mb-0 fw-700"><i class="bi bi-building-fill me-2 text-primary"></i>Mis Proyectos</h5>
            <a href="create.php" class="btn btn-primary">
                <i class="bi bi-plus-lg me-1"></i> Nuevo Proyecto
            </a>
        </div>

        <?php if (empty($proyectos)): ?>
        <div class="card text-center py-5">
            <div class="card-body">
                <i class="bi bi-building display-4 text-muted"></i>
                <h5 class="mt-3 text-muted">Sin proyectos aún</h5>
                <a href="create.php" class="btn btn-primary mt-2">Crear primer proyecto</a>
            </div>
        </div>
        <?php else: ?>
        <div class="row g-3">
            <?php foreach ($proyectos as $p):
                $badges = ['activo'=>'success','pausado'=>'warning','terminado'=>'secondary'];
                $bc = $badges[$p['estado']] ?? 'secondary';
            ?>
            <div class="col-12 col-md-6 col-xl-4">
                <div class="card h-100">
                    <div class="card-body p-4">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <span class="badge bg-<?= $bc ?> bg-opacity-15 text-<?= $bc ?>">
                                <?= ucfirst($p['estado']) ?>
                            </span>
                            <div class="dropdown">
                                <button class="btn btn-sm btn-light" data-bs-toggle="dropdown">
                                    <i class="bi bi-three-dots-vertical"></i>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end">
                                    <li><a class="dropdown-item" href="view.php?id=<?= $p['id'] ?>">
                                        <i class="bi bi-eye me-2"></i>Ver Presupuesto</a></li>
                                    <li><a class="dropdown-item" href="edit.php?id=<?= $p['id'] ?>">
                                        <i class="bi bi-pencil me-2"></i>Editar</a></li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li><a class="dropdown-item text-danger"
                                           href="delete.php?id=<?= $p['id'] ?>"
                                           onclick="return confirm('¿Eliminar este proyecto?')">
                                        <i class="bi bi-trash me-2"></i>Eliminar</a></li>
                                </ul>
                            </div>
                        </div>
                        <h6 class="fw-700 mb-1"><?= htmlspecialchars($p['nombre']) ?></h6>
                        <div class="text-muted small mb-3"><?= htmlspecialchars($p['cliente'] ?? 'Sin cliente') ?></div>
                        <div class="d-flex justify-content-between align-items-end">
                            <div>
                                <div class="small text-muted">Rubros</div>
                                <div class="fw-600"><?= $p['num_rubros'] ?></div>
                            </div>
                            <div class="text-end">
                                <div class="small text-muted">Total Presupuesto</div>
                                <div class="fw-800 text-primary fs-5">$<?= number_format($p['total_presupuesto'],2) ?></div>
                            </div>
                        </div>
                    </div>
                    <div class="card-footer py-2 px-4 d-flex gap-2">
                        <a href="view.php?id=<?= $p['id'] ?>" class="btn btn-sm btn-primary flex-grow-1">
                            <i class="bi bi-calculator me-1"></i> Presupuesto
                        </a>
                        <a href="<?= BASE_URL ?>/exports/pdf_presupuesto.php?id=<?= $p['id'] ?>"
                           class="btn btn-sm btn-outline-danger" target="_blank">
                            <i class="bi bi-file-pdf"></i>
                        </a>
                    </div>
                </div>
            </div>
            <?php endforeach; ?>
        </div>
        <?php endif; ?>
    </div>
</div>

<?php include __DIR__ . '/../../includes/footer.php'; ?>
