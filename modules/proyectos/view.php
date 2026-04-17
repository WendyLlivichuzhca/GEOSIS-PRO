<?php
require_once __DIR__ . '/../../config/database.php';

$db  = getDB();
$id  = intval($_GET['id'] ?? 0);

$proyecto = $db->prepare("SELECT * FROM proyectos WHERE id=?");
$proyecto->execute([$id]);
$proyecto = $proyecto->fetch();
if (!$proyecto) { header('Location: index.php'); exit; }

// Agregar rubro al presupuesto
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['rubro_id'])) {
    $rubro_id = intval($_POST['rubro_id']);
    $cantidad = floatval($_POST['cantidad'] ?? 1);
    // Verificar si ya existe
    $exists = $db->prepare("SELECT id FROM presupuesto_items WHERE proyecto_id=? AND rubro_id=?");
    $exists->execute([$id, $rubro_id]);
    if ($exists->fetch()) {
        $db->prepare("UPDATE presupuesto_items SET cantidad=cantidad+? WHERE proyecto_id=? AND rubro_id=?")
           ->execute([$cantidad, $id, $rubro_id]);
    } else {
        $db->prepare("INSERT INTO presupuesto_items (proyecto_id,rubro_id,cantidad) VALUES (?,?,?)")
           ->execute([$id, $rubro_id, $cantidad]);
    }
    header("Location: view.php?id=$id");
    exit;
}

// Eliminar item
if (isset($_GET['del_item'])) {
    $db->prepare("DELETE FROM presupuesto_items WHERE id=? AND proyecto_id=?")
       ->execute([intval($_GET['del_item']), $id]);
    header("Location: view.php?id=$id");
    exit;
}

// Actualizar cantidad
if (isset($_GET['upd_item']) && isset($_GET['qty'])) {
    $db->prepare("UPDATE presupuesto_items SET cantidad=? WHERE id=? AND proyecto_id=?")
       ->execute([floatval($_GET['qty']), intval($_GET['upd_item']), $id]);
    header("Location: view.php?id=$id");
    exit;
}

// Items del presupuesto
$items = $db->prepare("
    SELECT pi.*,
           r.nombre AS rubro_nombre,
           r.codigo AS rubro_codigo,
           r.unidad,
           r.indirectos,
           COALESCE((SELECT SUM(rr.costo) FROM rubro_recursos rr WHERE rr.rubro_id=r.id),0) AS costo_directo
    FROM presupuesto_items pi
    JOIN rubros r ON r.id = pi.rubro_id
    WHERE pi.proyecto_id = ?
    ORDER BY pi.orden, pi.id
");
$items->execute([$id]);
$items = $items->fetchAll();

// Rubros disponibles para agregar
$rubros = $db->query("SELECT id, codigo, nombre, unidad FROM rubros WHERE activo=1 ORDER BY codigo")->fetchAll();

// Calcular totales
$gran_total = 0;
foreach ($items as &$it) {
    $it['costo_total_unit'] = $it['precio_unitario_cerrado'] !== null
        ? (float) $it['precio_unitario_cerrado']
        : $it['costo_directo'] * (1 + $it['indirectos']/100);
    $it['subtotal']         = $it['costo_total_unit'] * $it['cantidad'];
    $gran_total += $it['subtotal'];
}
unset($it);

$pageTitle   = 'Presupuesto: ' . $proyecto['nombre'];
$currentPage = 'proyectos';

include __DIR__ . '/../../includes/header.php';
include __DIR__ . '/../../includes/sidebar.php';
?>

<div id="main">
    <div id="topbar">
        <button class="btn btn-sm btn-light d-md-none" id="menuToggle"><i class="bi bi-list fs-5"></i></button>
        <div>
            <div class="page-title"><?= htmlspecialchars($proyecto['nombre']) ?></div>
            <nav aria-label="breadcrumb"><ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="index.php">Proyectos</a></li>
                <li class="breadcrumb-item active">Presupuesto</li>
            </ol></nav>
        </div>
        <div class="ms-auto d-flex gap-2">
            <a href="<?= BASE_URL ?>/exports/pdf_presupuesto.php?id=<?= $id ?>"
               class="btn btn-sm btn-danger" target="_blank">
                <i class="bi bi-file-earmark-pdf me-1"></i> PDF
            </a>
            <a href="edit.php?id=<?= $id ?>" class="btn btn-sm btn-outline-primary">
                <i class="bi bi-pencil me-1"></i> Editar
            </a>
        </div>
    </div>

    <div class="p-4">
        <?php if (isset($_GET['new'])): ?>
        <div class="alert alert-success alert-dismissible fade show">
            <i class="bi bi-check-circle me-2"></i>Proyecto creado. ¡Ahora agrega los rubros del presupuesto!
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        <?php endif; ?>

        <!-- INFO PROYECTO -->
        <div class="card mb-4">
            <div class="card-body p-4">
                <div class="row">
                    <div class="col-md-8">
                        <h5 class="fw-700 mb-1"><?= htmlspecialchars($proyecto['nombre']) ?></h5>
                        <div class="text-muted small">
                            <?= htmlspecialchars($proyecto['cliente'] ?? '') ?>
                            <?= $proyecto['ubicacion'] ? ' &mdash; ' . htmlspecialchars($proyecto['ubicacion']) : '' ?>
                        </div>
                    </div>
                    <div class="col-md-4 text-end">
                        <div class="text-muted small">TOTAL PRESUPUESTO</div>
                        <div class="fw-800 text-primary" style="font-size:2rem;">
                            $<?= number_format($gran_total, 2) ?>
                        </div>
                        <div class="text-muted small">* No incluye IVA</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-3">
            <!-- AGREGAR RUBRO -->
            <div class="col-12 col-lg-4">
                <div class="card sticky-top" style="top:80px">
                    <div class="card-header py-3 px-4">
                        <i class="bi bi-plus-circle me-2 text-primary"></i>Agregar Rubro
                    </div>
                    <div class="card-body p-4">
                        <form method="POST">
                            <div class="mb-3">
                                <label class="form-label fw-500">Rubro APU</label>
                                <select name="rubro_id" class="form-select" id="selRubro">
                                    <?php foreach ($rubros as $r): ?>
                                    <option value="<?= $r['id'] ?>"><?= htmlspecialchars($r['codigo'].' - '.$r['nombre']) ?></option>
                                    <?php endforeach; ?>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-500">Cantidad</label>
                                <input type="number" name="cantidad" class="form-control"
                                       step="0.01" min="0.01" value="1">
                            </div>
                            <button type="submit" class="btn btn-primary w-100">
                                <i class="bi bi-plus-lg me-1"></i> Agregar al Presupuesto
                            </button>
                        </form>
                    </div>
                </div>
            </div>

            <!-- TABLA PRESUPUESTO -->
            <div class="col-12 col-lg-8">
                <div class="card">
                    <div class="card-header py-3 px-4 d-flex justify-content-between">
                        <span><i class="bi bi-calculator me-2 text-primary"></i>Ítems del Presupuesto</span>
                        <span class="badge bg-primary"><?= count($items) ?> rubros</span>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-hover align-middle mb-0">
                                <thead class="table-light">
                                    <tr>
                                        <th class="px-4">Rubro</th>
                                        <th class="text-center">Unidad</th>
                                        <th class="text-center">Cantidad</th>
                                        <th class="text-end">P. Unit.</th>
                                        <th class="text-end">Subtotal</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                <?php if (empty($items)): ?>
                                    <tr><td colspan="6" class="text-center text-muted py-5">
                                        Sin rubros. Agrega el primero desde el panel izquierdo.
                                    </td></tr>
                                <?php else: foreach ($items as $it): ?>
                                    <tr>
                                        <td class="px-4">
                                            <div class="fw-500 small"><?= htmlspecialchars($it['rubro_nombre']) ?></div>
                                            <div class="text-muted" style="font-size:.72rem;">
                                                <?= htmlspecialchars(trim(($it['item_numero'] ? $it['item_numero'] . ' | ' : '') . ($it['rubro_codigo'] ?? ''))) ?>
                                            </div>
                                        </td>
                                        <td class="text-center">
                                            <span class="badge bg-secondary bg-opacity-10 text-secondary"><?= $it['unidad'] ?></span>
                                        </td>
                                        <td class="text-center">
                                            <input type="number" class="form-control form-control-sm text-center"
                                                   style="width:80px;margin:auto"
                                                   value="<?= $it['cantidad'] ?>"
                                                   min="0.01" step="0.01"
                                                   onchange="actualizarCantidad(<?= $it['id'] ?>, this.value)">
                                        </td>
                                        <td class="text-end small">$<?= number_format($it['costo_total_unit'],2) ?></td>
                                        <td class="text-end fw-700 text-primary">$<?= number_format($it['subtotal'],2) ?></td>
                                        <td>
                                            <a href="?id=<?= $id ?>&del_item=<?= $it['id'] ?>"
                                               onclick="return confirm('¿Quitar este rubro?')"
                                               class="btn btn-sm btn-light">
                                                <i class="bi bi-trash text-danger"></i>
                                            </a>
                                        </td>
                                    </tr>
                                <?php endforeach; endif; ?>
                                </tbody>
                                <?php if (!empty($items)): ?>
                                <tfoot class="table-primary">
                                    <tr>
                                        <td colspan="4" class="px-4 fw-700">TOTAL PRESUPUESTO</td>
                                        <td class="text-end fw-800 fs-5 text-primary">$<?= number_format($gran_total,2) ?></td>
                                        <td></td>
                                    </tr>
                                </tfoot>
                                <?php endif; ?>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
function actualizarCantidad(itemId, qty) {
    window.location.href = `?id=<?= $id ?>&upd_item=${itemId}&qty=${qty}`;
}
</script>

<?php include __DIR__ . '/../../includes/footer.php'; ?>
