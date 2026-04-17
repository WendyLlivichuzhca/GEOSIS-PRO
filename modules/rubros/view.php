<?php
require_once __DIR__ . '/../../config/database.php';

$db  = getDB();
$id  = intval($_GET['id'] ?? 0);

$rubro = $db->prepare("SELECT * FROM rubros WHERE id=? AND activo=1");
$rubro->execute([$id]);
$rubro = $rubro->fetch();
if (!$rubro) { header('Location: index.php'); exit; }

$detalle = $db->prepare("
    SELECT rr.*, rec.descripcion, rec.unidad AS rec_unidad
    FROM rubro_recursos rr
    JOIN recursos rec ON rec.id = rr.recurso_id
    WHERE rr.rubro_id = ?
    ORDER BY rr.categoria, rec.descripcion
");
$detalle->execute([$id]);
$detalle = $detalle->fetchAll();

// Agrupar por categoría
$grupos = ['M'=>[], 'N'=>[], 'O'=>[], 'P'=>[]];
foreach ($detalle as $d) $grupos[$d['categoria']][] = $d;

$subtotales = [];
foreach ($grupos as $cat => $items) {
    $subtotales[$cat] = array_sum(array_column($items, 'costo'));
}
$total_directo = array_sum($subtotales);
$indirectos    = $total_directo * ($rubro['indirectos'] / 100);
$costo_total   = $total_directo + $indirectos;

$pageTitle   = 'APU: ' . $rubro['nombre'];
$currentPage = 'rubros';

$catInfo = [
    'M' => ['label'=>'EQUIPOS',       'color'=>'primary'],
    'N' => ['label'=>'MANO DE OBRA',  'color'=>'success'],
    'O' => ['label'=>'MATERIALES',    'color'=>'warning'],
    'P' => ['label'=>'TRANSPORTE',    'color'=>'info'],
];

include __DIR__ . '/../../includes/header.php';
include __DIR__ . '/../../includes/sidebar.php';
?>

<div id="main">
    <div id="topbar">
        <button class="btn btn-sm btn-light d-md-none" id="menuToggle"><i class="bi bi-list fs-5"></i></button>
        <div>
            <div class="page-title">Ficha APU</div>
            <nav aria-label="breadcrumb"><ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="<?= BASE_URL ?>/index.php">Inicio</a></li>
                <li class="breadcrumb-item"><a href="index.php">Rubros</a></li>
                <li class="breadcrumb-item active"><?= htmlspecialchars($rubro['codigo'] ?? '') ?></li>
            </ol></nav>
        </div>
        <div class="ms-auto d-flex gap-2">
            <a href="<?= BASE_URL ?>/exports/pdf_rubro.php?id=<?= $id ?>" class="btn btn-sm btn-danger" target="_blank">
                <i class="bi bi-file-earmark-pdf me-1"></i> PDF
            </a>
            <a href="edit.php?id=<?= $id ?>" class="btn btn-sm btn-primary">
                <i class="bi bi-pencil me-1"></i> Editar
            </a>
        </div>
    </div>

    <div class="p-4">
        <!-- HEADER RUBRO -->
        <div class="card mb-4">
            <div class="card-body p-4">
                <div class="row align-items-center">
                    <div class="col">
                        <div class="text-muted small mb-1">RUBRO: <?= htmlspecialchars($rubro['codigo'] ?? '') ?></div>
                        <h4 class="mb-1 fw-700"><?= htmlspecialchars($rubro['nombre']) ?></h4>
                        <div class="text-muted">Unidad: <strong><?= htmlspecialchars($rubro['unidad']) ?></strong>
                            &nbsp;|&nbsp; Indirectos: <strong><?= $rubro['indirectos'] ?>%</strong>
                        </div>
                    </div>
                    <div class="col-auto text-end">
                        <div class="text-muted small">VALOR OFERTADO</div>
                        <div style="font-size:2rem; font-weight:800; color:#1a56db;">
                            $<?= number_format($costo_total, 2) ?>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- DETALLE APU -->
        <?php foreach ($catInfo as $cat => $info): ?>
        <div class="card mb-3">
            <div class="card-header py-2 px-4 d-flex justify-content-between align-items-center">
                <span class="fw-600 text-<?= $info['color'] ?>">
                    <?= $cat ?> — <?= $info['label'] ?>
                </span>
                <span class="fw-700">$<?= number_format($subtotales[$cat] ?? 0, 2) ?></span>
            </div>
            <div class="card-body p-0">
                <table class="table table-sm align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th class="px-4">Descripción</th>
                            <th class="text-center">Cantidad</th>
                            <th class="text-center">Tarifa</th>
                            <th class="text-center">Rendimiento</th>
                            <th class="text-end px-4">Costo</th>
                        </tr>
                    </thead>
                    <tbody>
                    <?php if (empty($grupos[$cat])): ?>
                        <tr><td colspan="5" class="text-muted text-center py-2 small">Sin items</td></tr>
                    <?php else: foreach ($grupos[$cat] as $item): ?>
                        <tr>
                            <td class="px-4"><?= htmlspecialchars($item['descripcion']) ?></td>
                            <td class="text-center"><?= number_format($item['cantidad'],2) ?></td>
                            <td class="text-center"><?= number_format($item['tarifa'],2) ?></td>
                            <td class="text-center"><?= number_format($item['rendimiento'],2) ?></td>
                            <td class="text-end px-4 fw-600">$<?= number_format($item['costo'],2) ?></td>
                        </tr>
                    <?php endforeach; endif; ?>
                    </tbody>
                </table>
            </div>
        </div>
        <?php endforeach; ?>

        <!-- RESUMEN COSTOS -->
        <div class="card">
            <div class="card-body p-4">
                <div class="row justify-content-end">
                    <div class="col-12 col-md-4">
                        <table class="table table-sm mb-0">
                            <tr>
                                <td>Total Costo Directo (M+N+O+P)</td>
                                <td class="text-end fw-600">$<?= number_format($total_directo,2) ?></td>
                            </tr>
                            <tr>
                                <td>Indirectos y Utilidades (<?= $rubro['indirectos'] ?>%)</td>
                                <td class="text-end fw-600">$<?= number_format($indirectos,2) ?></td>
                            </tr>
                            <tr class="table-primary">
                                <td class="fw-700">COSTO TOTAL DEL RUBRO</td>
                                <td class="text-end fw-800 fs-5 text-primary">$<?= number_format($costo_total,2) ?></td>
                            </tr>
                            <tr class="table-success">
                                <td class="fw-700">VALOR OFERTADO</td>
                                <td class="text-end fw-800 fs-5 text-success">$<?= number_format($costo_total,2) ?></td>
                            </tr>
                        </table>
                        <p class="text-muted small mt-2">* ESTOS PRECIOS NO INCLUYEN IVA</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Botón agregar recurso -->
        <div class="mt-3">
            <a href="add_recurso.php?rubro_id=<?= $id ?>" class="btn btn-outline-primary">
                <i class="bi bi-plus-circle me-1"></i> Agregar Recurso a este Rubro
            </a>
            <a href="index.php" class="btn btn-outline-secondary ms-2">
                <i class="bi bi-arrow-left me-1"></i> Volver
            </a>
        </div>
    </div>
</div>

<?php include __DIR__ . '/../../includes/footer.php'; ?>
