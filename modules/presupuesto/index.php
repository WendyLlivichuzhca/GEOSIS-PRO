<?php
require_once __DIR__ . '/../../config/database.php';

$pageTitle   = 'Presupuestos';
$currentPage = 'presupuesto';
$db = getDB();

// Todos los proyectos con totales calculados
$proyectos = $db->query("
    SELECT p.*,
           COUNT(pi.id) AS num_rubros
    FROM proyectos p
    LEFT JOIN presupuesto_items pi ON pi.proyecto_id = p.id
    GROUP BY p.id
    ORDER BY p.created_at DESC
")->fetchAll();

// Calcular total real por proyecto (costo_directo × indirectos × cantidad)
foreach ($proyectos as &$p) {
    $stmt = $db->prepare("
        SELECT COALESCE(SUM(
            (
                COALESCE(
                    pi.precio_unitario_cerrado,
                    COALESCE((SELECT SUM(rr.costo) FROM rubro_recursos rr WHERE rr.rubro_id=r.id),0)
                    * (1 + r.indirectos/100)
                )
            ) * pi.cantidad
        ),0) AS total
        FROM presupuesto_items pi
        JOIN rubros r ON r.id = pi.rubro_id
        WHERE pi.proyecto_id = ?
    ");
    $stmt->execute([$p['id']]);
    $p['total_presupuesto'] = $stmt->fetchColumn();
}
unset($p);

// Estadísticas generales
$total_proyectos  = count($proyectos);
$total_global     = array_sum(array_column($proyectos, 'total_presupuesto'));
$activos          = count(array_filter($proyectos, function ($p) { return $p['estado'] === 'activo'; }));
$terminados       = count(array_filter($proyectos, function ($p) { return $p['estado'] === 'terminado'; }));

include __DIR__ . '/../../includes/header.php';
include __DIR__ . '/../../includes/sidebar.php';
?>

<div id="main">
    <div id="topbar">
        <button class="btn btn-sm btn-light d-md-none" id="menuToggle"><i class="bi bi-list fs-5"></i></button>
        <div>
            <div class="page-title">Presupuestos</div>
            <nav aria-label="breadcrumb"><ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="<?= BASE_URL ?>/index.php">Inicio</a></li>
                <li class="breadcrumb-item active">Presupuestos</li>
            </ol></nav>
        </div>
        <div class="ms-auto d-flex gap-2">
            <a href="<?= BASE_URL ?>/modules/presupuesto/import_excel.php" class="btn btn-sm btn-success">
                <i class="bi bi-file-earmark-excel me-1"></i> Importar Excel
            </a>
            <a href="<?= BASE_URL ?>/modules/proyectos/create.php" class="btn btn-sm btn-primary">
                <i class="bi bi-plus-lg me-1"></i> Nuevo Proyecto
            </a>
        </div>
    </div>

    <div class="p-4">

        <!-- STAT CARDS -->
        <div class="row g-3 mb-4">
            <div class="col-6 col-md-3">
                <div class="card stat-card">
                    <div class="stat-icon" style="background:rgba(26,86,219,.12);">
                        <i class="bi bi-calculator-fill text-primary"></i>
                    </div>
                    <div class="stat-value"><?= $total_proyectos ?></div>
                    <div class="stat-label">Total Proyectos</div>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="card stat-card">
                    <div class="stat-icon" style="background:rgba(22,163,74,.12);">
                        <i class="bi bi-play-circle-fill text-success"></i>
                    </div>
                    <div class="stat-value"><?= $activos ?></div>
                    <div class="stat-label">En Ejecución</div>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="card stat-card">
                    <div class="stat-icon" style="background:rgba(107,114,128,.12);">
                        <i class="bi bi-check-circle-fill text-secondary"></i>
                    </div>
                    <div class="stat-value"><?= $terminados ?></div>
                    <div class="stat-label">Terminados</div>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="card stat-card">
                    <div class="stat-icon" style="background:rgba(26,86,219,.12);">
                        <i class="bi bi-currency-dollar text-primary"></i>
                    </div>
                    <div class="stat-value" style="font-size:1.2rem;">$<?= number_format($total_global, 0) ?></div>
                    <div class="stat-label">Valor Total Acumulado</div>
                </div>
            </div>
        </div>

        <!-- TABLA DE PRESUPUESTOS -->
        <div class="card">
            <div class="card-header py-3 px-4 d-flex justify-content-between align-items-center">
                <span><i class="bi bi-table me-2 text-primary"></i>Resumen de Presupuestos</span>
                <span class="badge bg-primary"><?= $total_proyectos ?> proyectos</span>
            </div>
            <div class="card-body p-0">
                <?php if (empty($proyectos)): ?>
                <div class="text-center py-5 text-muted">
                    <i class="bi bi-calculator display-4"></i>
                    <p class="mt-3">No hay proyectos registrados.</p>
                    <a href="<?= BASE_URL ?>/modules/proyectos/create.php" class="btn btn-primary">
                        Crear primer proyecto
                    </a>
                </div>
                <?php else: ?>
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th class="px-4">Proyecto</th>
                                <th>Cliente</th>
                                <th class="text-center">Estado</th>
                                <th class="text-center">Rubros</th>
                                <th class="text-end">Total Presupuesto</th>
                                <th class="text-center" style="width:130px;">Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                        <?php
                        $badges = ['activo'=>'success','pausado'=>'warning','terminado'=>'secondary'];
                        foreach ($proyectos as $p):
                            $bc = $badges[$p['estado']] ?? 'secondary';
                        ?>
                            <tr>
                                <td class="px-4">
                                    <div class="fw-600"><?= htmlspecialchars($p['nombre']) ?></div>
                                    <?php if ($p['ubicacion']): ?>
                                    <div class="text-muted small"><?= htmlspecialchars($p['ubicacion']) ?></div>
                                    <?php endif; ?>
                                </td>
                                <td class="text-muted small"><?= htmlspecialchars($p['cliente'] ?? '—') ?></td>
                                <td class="text-center">
                                    <span class="badge bg-<?= $bc ?> bg-opacity-15 text-<?= $bc ?>">
                                        <?= ucfirst($p['estado']) ?>
                                    </span>
                                </td>
                                <td class="text-center">
                                    <span class="badge bg-primary bg-opacity-10 text-primary"><?= $p['num_rubros'] ?></span>
                                </td>
                                <td class="text-end fw-700 text-primary fs-6">
                                    $<?= number_format($p['total_presupuesto'], 2) ?>
                                </td>
                                <td class="text-center">
                                    <div class="d-flex gap-1 justify-content-center">
                                        <a href="<?= BASE_URL ?>/modules/proyectos/view.php?id=<?= $p['id'] ?>"
                                           class="btn btn-sm btn-primary" title="Ver presupuesto">
                                            <i class="bi bi-calculator"></i>
                                        </a>
                                        <a href="<?= BASE_URL ?>/exports/pdf_presupuesto.php?id=<?= $p['id'] ?>"
                                           class="btn btn-sm btn-outline-danger" target="_blank" title="Exportar PDF">
                                            <i class="bi bi-file-pdf"></i>
                                        </a>
                                    </div>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                        </tbody>
                        <tfoot class="table-light">
                            <tr>
                                <td colspan="4" class="px-4 fw-700">TOTAL ACUMULADO</td>
                                <td class="text-end fw-800 text-primary fs-5">$<?= number_format($total_global, 2) ?></td>
                                <td></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
                <?php endif; ?>
            </div>
        </div>

        <!-- GRÁFICO DE BARRAS SIMPLE (sin librería) -->
        <?php if (!empty($proyectos) && $total_global > 0): ?>
        <div class="card mt-4">
            <div class="card-header py-3 px-4">
                <i class="bi bi-bar-chart-fill me-2 text-primary"></i>Participación por Proyecto
            </div>
            <div class="card-body p-4">
                <?php foreach ($proyectos as $p):
                    if ($p['total_presupuesto'] <= 0) continue;
                    $pct = ($p['total_presupuesto'] / $total_global) * 100;
                    $badges2 = ['activo'=>'#1a56db','pausado'=>'#d97706','terminado'=>'#6b7280'];
                    $color = $badges2[$p['estado']] ?? '#1a56db';
                ?>
                <div class="mb-3">
                    <div class="d-flex justify-content-between small mb-1">
                        <span class="fw-500"><?= htmlspecialchars($p['nombre']) ?></span>
                        <span class="text-muted"><?= number_format($pct, 1) ?>% — $<?= number_format($p['total_presupuesto'], 2) ?></span>
                    </div>
                    <div style="background:#f0f4ff;border-radius:4px;height:12px;overflow:hidden;">
                        <div style="width:<?= number_format($pct, 2) ?>%;background:<?= $color ?>;height:100%;border-radius:4px;transition:width .3s;"></div>
                    </div>
                </div>
                <?php endforeach; ?>
            </div>
        </div>
        <?php endif; ?>

    </div>
</div>

<?php include __DIR__ . '/../../includes/footer.php'; ?>
