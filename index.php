<?php
require_once __DIR__ . '/config/database.php';

$pageTitle   = 'Dashboard';
$currentPage = 'dashboard';

$db = getDB();

$totalRubros    = $db->query("SELECT COUNT(*) FROM rubros   WHERE activo=1")->fetchColumn();
$totalRecursos  = $db->query("SELECT COUNT(*) FROM recursos WHERE activo=1")->fetchColumn();
$totalProyectos = $db->query("SELECT COUNT(*) FROM proyectos")->fetchColumn();
$totalActivos   = $db->query("SELECT COUNT(*) FROM proyectos WHERE estado='activo'")->fetchColumn();

// Últimos proyectos
$proyectos = $db->query("
    SELECT p.*, COUNT(pi.id) AS num_rubros
    FROM proyectos p
    LEFT JOIN presupuesto_items pi ON pi.proyecto_id = p.id
    GROUP BY p.id
    ORDER BY p.created_at DESC
    LIMIT 5
")->fetchAll();

// Recursos por categoría
$categorias = $db->query("
    SELECT categoria,
           COUNT(*) AS total,
           AVG(precio) AS precio_avg
    FROM recursos WHERE activo=1
    GROUP BY categoria
")->fetchAll();

include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>

<div id="main">
    <!-- TOPBAR -->
    <div id="topbar">
        <button class="btn btn-sm btn-light d-md-none" id="menuToggle">
            <i class="bi bi-list fs-5"></i>
        </button>
        <div>
            <div class="page-title">Dashboard</div>
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item active">Inicio</li>
                </ol>
            </nav>
        </div>
    </div>

    <!-- CONTENT -->
    <div class="p-4">

        <!-- STAT CARDS -->
        <div class="row g-3 mb-4">
            <div class="col-6 col-md-3">
                <div class="stat-card">
                    <div class="d-flex align-items-center gap-3">
                        <div class="icon bg-primary bg-opacity-10 text-primary">
                            <i class="bi bi-list-columns-reverse"></i>
                        </div>
                        <div>
                            <div class="value"><?= number_format($totalRubros) ?></div>
                            <div class="label">Rubros APU</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="stat-card">
                    <div class="d-flex align-items-center gap-3">
                        <div class="icon bg-success bg-opacity-10 text-success">
                            <i class="bi bi-box-seam-fill"></i>
                        </div>
                        <div>
                            <div class="value"><?= number_format($totalRecursos) ?></div>
                            <div class="label">Recursos</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="stat-card">
                    <div class="d-flex align-items-center gap-3">
                        <div class="icon bg-warning bg-opacity-10 text-warning">
                            <i class="bi bi-building-fill"></i>
                        </div>
                        <div>
                            <div class="value"><?= number_format($totalProyectos) ?></div>
                            <div class="label">Proyectos</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="stat-card">
                    <div class="d-flex align-items-center gap-3">
                        <div class="icon bg-info bg-opacity-10 text-info">
                            <i class="bi bi-activity"></i>
                        </div>
                        <div>
                            <div class="value"><?= number_format($totalActivos) ?></div>
                            <div class="label">En ejecución</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-3">
            <!-- Últimos Proyectos -->
            <div class="col-12 col-lg-7">
                <div class="card h-100">
                    <div class="card-header d-flex justify-content-between align-items-center py-3 px-4">
                        <span><i class="bi bi-building-fill me-2 text-primary"></i>Últimos Proyectos</span>
                        <a href="<?= BASE_URL ?>/modules/proyectos/create.php" class="btn btn-sm btn-primary">
                            <i class="bi bi-plus-lg"></i> Nuevo
                        </a>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-hover align-middle mb-0">
                                <thead class="table-light">
                                    <tr>
                                        <th class="px-4">Proyecto</th>
                                        <th>Cliente</th>
                                        <th>Rubros</th>
                                        <th>Estado</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                <?php if (empty($proyectos)): ?>
                                    <tr><td colspan="5" class="text-center text-muted py-4">
                                        Sin proyectos aún.
                                        <a href="<?= BASE_URL ?>/modules/proyectos/create.php">Crear uno</a>
                                    </td></tr>
                                <?php else: foreach ($proyectos as $p): ?>
                                    <tr>
                                        <td class="px-4 fw-500"><?= htmlspecialchars($p['nombre']) ?></td>
                                        <td class="text-muted small"><?= htmlspecialchars($p['cliente'] ?? '-') ?></td>
                                        <td><span class="badge bg-primary bg-opacity-10 text-primary"><?= $p['num_rubros'] ?></span></td>
                                        <td>
                                            <?php
                                            $badges = ['activo'=>'success','pausado'=>'warning','terminado'=>'secondary'];
                                            $b = $badges[$p['estado']] ?? 'secondary';
                                            ?>
                                            <span class="badge bg-<?= $b ?> bg-opacity-15 text-<?= $b ?>">
                                                <?= ucfirst($p['estado']) ?>
                                            </span>
                                        </td>
                                        <td>
                                            <a href="<?= BASE_URL ?>/modules/proyectos/view.php?id=<?= $p['id'] ?>"
                                               class="btn btn-sm btn-light">
                                                <i class="bi bi-eye"></i>
                                            </a>
                                        </td>
                                    </tr>
                                <?php endforeach; endif; ?>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Recursos por categoría -->
            <div class="col-12 col-lg-5">
                <div class="card h-100">
                    <div class="card-header py-3 px-4">
                        <i class="bi bi-box-seam-fill me-2 text-success"></i>Recursos por Categoría
                    </div>
                    <div class="card-body">
                        <?php
                        $catInfo = [
                            'M' => ['label'=>'Equipos',       'color'=>'primary', 'icon'=>'gear-fill'],
                            'N' => ['label'=>'Mano de Obra',  'color'=>'success', 'icon'=>'person-fill'],
                            'O' => ['label'=>'Materiales',    'color'=>'warning', 'icon'=>'box-seam'],
                            'P' => ['label'=>'Transporte',    'color'=>'info',    'icon'=>'truck'],
                        ];
                        foreach ($categorias as $cat):
                            $info = $catInfo[$cat['categoria']] ?? ['label'=>$cat['categoria'],'color'=>'secondary','icon'=>'circle'];
                        ?>
                        <div class="d-flex align-items-center gap-3 mb-3 p-3 rounded-3 bg-light">
                            <div class="icon bg-<?= $info['color'] ?> bg-opacity-10 text-<?= $info['color'] ?>"
                                 style="width:42px;height:42px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;">
                                <i class="bi bi-<?= $info['icon'] ?>"></i>
                            </div>
                            <div class="flex-grow-1">
                                <div class="fw-600 small"><?= $info['label'] ?></div>
                                <div class="text-muted" style="font-size:.75rem;"><?= $cat['total'] ?> recursos</div>
                            </div>
                            <div class="text-end">
                                <div class="fw-600 small">$<?= number_format($cat['precio_avg'], 2) ?></div>
                                <div class="text-muted" style="font-size:.72rem;">precio prom.</div>
                            </div>
                        </div>
                        <?php endforeach; ?>

                        <div class="mt-3">
                            <a href="<?= BASE_URL ?>/modules/recursos/create.php"
                               class="btn btn-outline-success btn-sm w-100">
                                <i class="bi bi-plus-lg me-1"></i> Agregar Recurso
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- ACCESOS RÁPIDOS -->
        <div class="row g-3 mt-1">
            <div class="col-12">
                <div class="card">
                    <div class="card-header py-3 px-4">
                        <i class="bi bi-lightning-fill me-2 text-warning"></i>Accesos Rápidos
                    </div>
                    <div class="card-body d-flex flex-wrap gap-2">
                        <a href="<?= BASE_URL ?>/modules/rubros/create.php" class="btn btn-primary">
                            <i class="bi bi-plus-circle me-1"></i> Nuevo Rubro APU
                        </a>
                        <a href="<?= BASE_URL ?>/modules/proyectos/create.php" class="btn btn-success">
                            <i class="bi bi-building me-1"></i> Nuevo Proyecto
                        </a>
                        <a href="<?= BASE_URL ?>/modules/rubros/index.php" class="btn btn-outline-primary">
                            <i class="bi bi-list-columns-reverse me-1"></i> Ver Rubros
                        </a>
                        <a href="<?= BASE_URL ?>/modules/presupuesto/index.php" class="btn btn-outline-secondary">
                            <i class="bi bi-calculator me-1"></i> Presupuestos
                        </a>
                    </div>
                </div>
            </div>
        </div>

    </div><!-- /.p-4 -->
</div><!-- /#main -->

<?php include __DIR__ . '/includes/footer.php'; ?>
