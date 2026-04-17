<?php
require_once __DIR__ . '/../../config/database.php';

function importedItemOrder(string $itemNumero, int $fallback): int
{
    $itemNumero = trim($itemNumero);
    if ($itemNumero === '') {
        return $fallback;
    }

    $numeric = str_replace('.', '', $itemNumero);
    return ctype_digit($numeric) ? (int) $numeric : $fallback;
}

function importedChapterTotal(int $chapterId, array $childrenByParent, array $directTotals, array &$memo): float
{
    if (isset($memo[$chapterId])) {
        return $memo[$chapterId];
    }

    $total = isset($directTotals[$chapterId]) ? (float) $directTotals[$chapterId] : 0.0;

    if (!empty($childrenByParent[$chapterId])) {
        foreach ($childrenByParent[$chapterId] as $childId) {
            $total += importedChapterTotal($childId, $childrenByParent, $directTotals, $memo);
        }
    }

    $memo[$chapterId] = $total;
    return $total;
}

function recalculateImportedBudget(PDO $db, array $presupuesto): void
{
    $presupuestoId = (int) $presupuesto['id'];
    $projectId = (int) $presupuesto['proyecto_id'];

    $chapterRows = $db->prepare("
        SELECT id, parent_id
        FROM presupuesto_capitulos
        WHERE presupuesto_id = ?
    ");
    $chapterRows->execute([$presupuestoId]);
    $chapters = $chapterRows->fetchAll();

    $directTotalsStmt = $db->prepare("
        SELECT capitulo_id, COALESCE(SUM(precio_total), 0) AS total
        FROM presupuesto_lineas
        WHERE presupuesto_id = ? AND tipo_linea = 'rubro' AND capitulo_id IS NOT NULL
        GROUP BY capitulo_id
    ");
    $directTotalsStmt->execute([$presupuestoId]);
    $directTotals = [];
    foreach ($directTotalsStmt->fetchAll() as $row) {
        $directTotals[(int) $row['capitulo_id']] = (float) $row['total'];
    }

    $childrenByParent = [];
    foreach ($chapters as $chapter) {
        $parentId = $chapter['parent_id'] !== null ? (int) $chapter['parent_id'] : 0;
        if (!isset($childrenByParent[$parentId])) {
            $childrenByParent[$parentId] = [];
        }
        $childrenByParent[$parentId][] = (int) $chapter['id'];
    }

    $memo = [];
    $updateChapter = $db->prepare("UPDATE presupuesto_capitulos SET total = ? WHERE id = ?");
    $updateTitle = $db->prepare("
        UPDATE presupuesto_lineas
        SET precio_total = ?
        WHERE presupuesto_id = ? AND tipo_linea = 'titulo' AND capitulo_id = ?
    ");

    foreach ($chapters as $chapter) {
        $chapterId = (int) $chapter['id'];
        $total = importedChapterTotal($chapterId, $childrenByParent, $directTotals, $memo);
        $updateChapter->execute([$total, $chapterId]);
        $updateTitle->execute([$total, $presupuestoId, $chapterId]);
    }

    $totalStmt = $db->prepare("
        SELECT COALESCE(SUM(precio_total), 0)
        FROM presupuesto_lineas
        WHERE presupuesto_id = ? AND tipo_linea = 'rubro'
    ");
    $totalStmt->execute([$presupuestoId]);
    $budgetTotal = (float) $totalStmt->fetchColumn();

    $updateBudget = $db->prepare("
        UPDATE presupuestos
        SET subtotal_directo = ?, subtotal_oferta = ?, total_general = ?
        WHERE id = ?
    ");
    $updateBudget->execute([$budgetTotal, $budgetTotal, $budgetTotal, $presupuestoId]);

    $itemRows = $db->prepare("
        SELECT orden, item_numero, cantidad, precio_unitario, precio_total, rubro_id
        FROM presupuesto_lineas
        WHERE presupuesto_id = ? AND tipo_linea = 'rubro' AND rubro_id IS NOT NULL
    ");
    $itemRows->execute([$presupuestoId]);
    $items = $itemRows->fetchAll();

    $updateItem = $db->prepare("
        UPDATE presupuesto_items
        SET item_numero = ?, cantidad = ?, precio_unitario_cerrado = ?, precio_total_cerrado = ?
        WHERE proyecto_id = ? AND orden = ? AND rubro_id = ?
    ");

    foreach ($items as $item) {
        $updateItem->execute([
            $item['item_numero'] ?: null,
            $item['cantidad'],
            $item['precio_unitario'],
            $item['precio_total'],
            $projectId,
            $item['orden'],
            $item['rubro_id'],
        ]);
    }
}

$db = getDB();
$id = intval($_GET['id'] ?? 0);
$editingId = intval($_GET['edit'] ?? 0);
$error = null;

$stmt = $db->prepare("
    SELECT pr.*, p.id AS proyecto_id, p.nombre AS proyecto_nombre
    FROM presupuestos pr
    JOIN proyectos p ON p.id = pr.proyecto_id
    WHERE pr.id = ?
");
$stmt->execute([$id]);
$presupuesto = $stmt->fetch();

if (!$presupuesto) {
    header('Location: index.php');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    try {
        if ($action === 'save_line') {
            $lineId = intval($_POST['line_id'] ?? 0);

            $lineStmt = $db->prepare("
                SELECT pl.*, pr.proyecto_id
                FROM presupuesto_lineas pl
                JOIN presupuestos pr ON pr.id = pl.presupuesto_id
                WHERE pl.id = ? AND pl.presupuesto_id = ?
                LIMIT 1
            ");
            $lineStmt->execute([$lineId, $id]);
            $line = $lineStmt->fetch();

            if (!$line) {
                throw new RuntimeException('No se encontro la linea a editar.');
            }

            $itemNumero = trim($_POST['item_numero'] ?? '');
            $descripcion = trim($_POST['descripcion'] ?? '');
            $unidad = trim($_POST['unidad'] ?? '');
            $order = importedItemOrder($itemNumero, (int) $line['orden']);

            $db->beginTransaction();

            if ($line['tipo_linea'] === 'titulo') {
                $updateTitle = $db->prepare("
                    UPDATE presupuesto_lineas
                    SET item_numero = ?, descripcion = ?, unidad = ?, orden = ?
                    WHERE id = ?
                ");
                $updateTitle->execute([
                    $itemNumero !== '' ? $itemNumero : null,
                    $descripcion !== '' ? $descripcion : $line['descripcion'],
                    $unidad !== '' ? $unidad : null,
                    $order,
                    $lineId,
                ]);

                if (!empty($line['capitulo_id'])) {
                    $updateChapter = $db->prepare("
                        UPDATE presupuesto_capitulos
                        SET item_numero = ?, nombre = ?, orden = ?
                        WHERE id = ?
                    ");
                    $updateChapter->execute([
                        $itemNumero !== '' ? $itemNumero : null,
                        $descripcion !== '' ? $descripcion : $line['descripcion'],
                        $order,
                        $line['capitulo_id'],
                    ]);
                }
            } else {
                $rubroCodigo = trim($_POST['rubro_codigo'] ?? '');
                $cantidad = max(0, (float) ($_POST['cantidad'] ?? 0));
                $precioUnitario = max(0, (float) ($_POST['precio_unitario'] ?? 0));
                $precioTotal = round($cantidad * $precioUnitario, 2);

                $updateLine = $db->prepare("
                    UPDATE presupuesto_lineas
                    SET item_numero = ?, rubro_codigo = ?, descripcion = ?, unidad = ?,
                        cantidad = ?, precio_unitario = ?, precio_total = ?, orden = ?
                    WHERE id = ?
                ");
                $updateLine->execute([
                    $itemNumero !== '' ? $itemNumero : null,
                    $rubroCodigo !== '' ? $rubroCodigo : null,
                    $descripcion !== '' ? $descripcion : $line['descripcion'],
                    $unidad !== '' ? $unidad : null,
                    $cantidad,
                    $precioUnitario,
                    $precioTotal,
                    $order,
                    $lineId,
                ]);

                if (!empty($line['rubro_id'])) {
                    $updateItem = $db->prepare("
                        UPDATE presupuesto_items
                        SET item_numero = ?, cantidad = ?, precio_unitario_cerrado = ?, precio_total_cerrado = ?, orden = ?
                        WHERE proyecto_id = ? AND orden = ? AND rubro_id = ?
                    ");
                    $updateItem->execute([
                        $itemNumero !== '' ? $itemNumero : null,
                        $cantidad,
                        $precioUnitario,
                        $precioTotal,
                        $order,
                        $presupuesto['proyecto_id'],
                        $line['orden'],
                        $line['rubro_id'],
                    ]);
                }
            }

            recalculateImportedBudget($db, $presupuesto);
            $db->commit();

            header('Location: view_importado.php?id=' . $id . '&updated=1');
            exit;
        }

        if ($action === 'recalculate') {
            $db->beginTransaction();
            recalculateImportedBudget($db, $presupuesto);
            $db->commit();

            header('Location: view_importado.php?id=' . $id . '&recalculated=1');
            exit;
        }
    } catch (Throwable $e) {
        if ($db->inTransaction()) {
            $db->rollBack();
        }
        $error = $e->getMessage();
    }
}

$stmt->execute([$id]);
$presupuesto = $stmt->fetch();

$linesStmt = $db->prepare("
    SELECT *
    FROM presupuesto_lineas
    WHERE presupuesto_id = ?
    ORDER BY orden, id
");
$linesStmt->execute([$id]);
$lineas = $linesStmt->fetchAll();

$pageTitle = 'Presupuesto Importado';
$currentPage = 'presupuesto';

include __DIR__ . '/../../includes/header.php';
include __DIR__ . '/../../includes/sidebar.php';
?>

<div id="main">
    <div id="topbar">
        <button class="btn btn-sm btn-light d-md-none" id="menuToggle"><i class="bi bi-list fs-5"></i></button>
        <div>
            <div class="page-title"><?= htmlspecialchars($presupuesto['proyecto_nombre']) ?></div>
            <nav aria-label="breadcrumb"><ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="<?= BASE_URL ?>/index.php">Inicio</a></li>
                <li class="breadcrumb-item"><a href="<?= BASE_URL ?>/modules/presupuesto/index.php">Presupuestos</a></li>
                <li class="breadcrumb-item active">Importado</li>
            </ol></nav>
        </div>
        <div class="ms-auto d-flex gap-2">
            <form method="POST" class="m-0">
                <input type="hidden" name="action" value="recalculate">
                <button type="submit" class="btn btn-sm btn-outline-secondary">
                    <i class="bi bi-arrow-repeat me-1"></i> Recalcular
                </button>
            </form>
            <a href="<?= BASE_URL ?>/modules/proyectos/view.php?id=<?= $presupuesto['proyecto_id'] ?>" class="btn btn-sm btn-outline-primary">
                <i class="bi bi-building me-1"></i> Ver proyecto
            </a>
            <a href="<?= BASE_URL ?>/modules/presupuesto/import_excel.php" class="btn btn-sm btn-success">
                <i class="bi bi-upload me-1"></i> Nueva importacion
            </a>
        </div>
    </div>

    <div class="p-4">
        <?php if ($error): ?>
        <div class="alert alert-danger alert-dismissible fade show">
            <i class="bi bi-exclamation-triangle me-2"></i><?= htmlspecialchars($error) ?>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        <?php endif; ?>

        <?php if (isset($_GET['imported'])): ?>
        <div class="alert alert-success alert-dismissible fade show">
            <i class="bi bi-check-circle me-2"></i>
            Importacion completada. Lineas: <strong><?= intval($_GET['lineas'] ?? 0) ?></strong>,
            rubros procesados: <strong><?= intval($_GET['rubros'] ?? 0) ?></strong>.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        <?php endif; ?>

        <?php if (isset($_GET['updated'])): ?>
        <div class="alert alert-primary alert-dismissible fade show">
            <i class="bi bi-save me-2"></i>La linea se actualizo y el presupuesto fue recalculado.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        <?php endif; ?>

        <?php if (isset($_GET['recalculated'])): ?>
        <div class="alert alert-info alert-dismissible fade show">
            <i class="bi bi-arrow-repeat me-2"></i>Totales recalculados correctamente.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        <?php endif; ?>

        <div class="card mb-4">
            <div class="card-body p-4">
                <div class="row g-3">
                    <div class="col-12 col-lg-8">
                        <div class="text-muted small mb-1">PRESUPUESTO</div>
                        <h4 class="mb-1 fw-700"><?= htmlspecialchars($presupuesto['proyecto_nombre']) ?></h4>
                        <div class="text-muted small">
                            <?= htmlspecialchars($presupuesto['oferente'] ?? '-') ?>
                            <?= !empty($presupuesto['ubicacion']) ? ' | ' . htmlspecialchars($presupuesto['ubicacion']) : '' ?>
                            <?= !empty($presupuesto['fecha_presupuesto']) ? ' | ' . htmlspecialchars($presupuesto['fecha_presupuesto']) : '' ?>
                        </div>
                    </div>
                    <div class="col-12 col-lg-4 text-lg-end">
                        <div class="text-muted small">TOTAL IMPORTADO</div>
                        <div class="fw-800 text-primary" style="font-size:2rem;">
                            $<?= number_format((float) $presupuesto['total_general'], 2) ?>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header py-3 px-4 d-flex justify-content-between align-items-center">
                <span><i class="bi bi-table me-2 text-primary"></i>Detalle del presupuesto</span>
                <span class="badge bg-primary"><?= count($lineas) ?> lineas</span>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th class="px-4" style="width:90px;">Item</th>
                                <th style="width:120px;">Codigo</th>
                                <th>Descripcion</th>
                                <th class="text-center" style="width:90px;">Unidad</th>
                                <th class="text-end" style="width:120px;">Cantidad</th>
                                <th class="text-end" style="width:130px;">P.Unit.</th>
                                <th class="text-end" style="width:130px;">P.Total</th>
                                <th class="text-center px-4" style="width:120px;">Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                        <?php foreach ($lineas as $linea): ?>
                            <?php $isEditing = $editingId === (int) $linea['id']; ?>
                            <?php if ($isEditing): ?>
                            <tr class="<?= $linea['tipo_linea'] === 'titulo' ? 'table-warning' : 'table-light' ?>">
                                <form method="POST">
                                    <input type="hidden" name="action" value="save_line">
                                    <input type="hidden" name="line_id" value="<?= (int) $linea['id'] ?>">
                                    <td class="px-4">
                                        <input type="text" name="item_numero" class="form-control form-control-sm"
                                               value="<?= htmlspecialchars($linea['item_numero'] ?? '') ?>">
                                    </td>
                                    <td>
                                        <?php if ($linea['tipo_linea'] === 'titulo'): ?>
                                            <span class="text-muted small">Capitulo</span>
                                        <?php else: ?>
                                            <input type="text" name="rubro_codigo" class="form-control form-control-sm"
                                                   value="<?= htmlspecialchars($linea['rubro_codigo'] ?? '') ?>">
                                        <?php endif; ?>
                                    </td>
                                    <td>
                                        <input type="text" name="descripcion" class="form-control form-control-sm"
                                               value="<?= htmlspecialchars($linea['descripcion']) ?>" required>
                                    </td>
                                    <td>
                                        <input type="text" name="unidad" class="form-control form-control-sm text-center"
                                               value="<?= htmlspecialchars($linea['unidad'] ?? '') ?>">
                                    </td>
                                    <td>
                                        <?php if ($linea['tipo_linea'] === 'titulo'): ?>
                                            <div class="text-end small text-muted pt-1">Auto</div>
                                        <?php else: ?>
                                            <input type="number" name="cantidad" class="form-control form-control-sm text-end"
                                                   value="<?= htmlspecialchars($linea['cantidad']) ?>" step="0.0001" min="0">
                                        <?php endif; ?>
                                    </td>
                                    <td>
                                        <?php if ($linea['tipo_linea'] === 'titulo'): ?>
                                            <div class="text-end small text-muted pt-1">Auto</div>
                                        <?php else: ?>
                                            <input type="number" name="precio_unitario" class="form-control form-control-sm text-end"
                                                   value="<?= htmlspecialchars($linea['precio_unitario']) ?>" step="0.0001" min="0">
                                        <?php endif; ?>
                                    </td>
                                    <td class="text-end fw-700 text-primary">
                                        <?= $linea['tipo_linea'] === 'titulo' ? '$' . number_format((float) $linea['precio_total'], 2) : 'Se recalcula' ?>
                                    </td>
                                    <td class="text-center px-4">
                                        <div class="d-flex gap-1 justify-content-center">
                                            <button type="submit" class="btn btn-sm btn-primary" title="Guardar">
                                                <i class="bi bi-save"></i>
                                            </button>
                                            <a href="<?= BASE_URL ?>/modules/presupuesto/view_importado.php?id=<?= $id ?>" class="btn btn-sm btn-light" title="Cancelar">
                                                <i class="bi bi-x-lg"></i>
                                            </a>
                                        </div>
                                    </td>
                                </form>
                            </tr>
                            <?php elseif ($linea['tipo_linea'] === 'titulo'): ?>
                            <tr class="table-secondary">
                                <td class="px-4 fw-700"><?= htmlspecialchars($linea['item_numero'] ?? '') ?></td>
                                <td></td>
                                <td class="fw-700"><?= htmlspecialchars($linea['descripcion']) ?></td>
                                <td class="text-center"><?= htmlspecialchars($linea['unidad'] ?? '') ?></td>
                                <td class="text-end"><?= $linea['cantidad'] > 0 ? number_format((float) $linea['cantidad'], 2) : '' ?></td>
                                <td class="text-end"><?= $linea['precio_unitario'] > 0 ? number_format((float) $linea['precio_unitario'], 2) : '' ?></td>
                                <td class="text-end fw-700 text-primary">$<?= number_format((float) $linea['precio_total'], 2) ?></td>
                                <td class="text-center px-4">
                                    <a href="<?= BASE_URL ?>/modules/presupuesto/view_importado.php?id=<?= $id ?>&edit=<?= (int) $linea['id'] ?>" class="btn btn-sm btn-light" title="Editar capitulo">
                                        <i class="bi bi-pencil text-primary"></i>
                                    </a>
                                </td>
                            </tr>
                            <?php else: ?>
                            <tr>
                                <td class="px-4 small"><?= htmlspecialchars($linea['item_numero'] ?? '') ?></td>
                                <td class="small text-muted"><?= htmlspecialchars($linea['rubro_codigo'] ?? '') ?></td>
                                <td><?= htmlspecialchars($linea['descripcion']) ?></td>
                                <td class="text-center">
                                    <span class="badge bg-secondary bg-opacity-10 text-secondary"><?= htmlspecialchars($linea['unidad'] ?? '') ?></span>
                                </td>
                                <td class="text-end"><?= number_format((float) $linea['cantidad'], 2) ?></td>
                                <td class="text-end">$<?= number_format((float) $linea['precio_unitario'], 2) ?></td>
                                <td class="text-end fw-600 text-primary">$<?= number_format((float) $linea['precio_total'], 2) ?></td>
                                <td class="text-center px-4">
                                    <a href="<?= BASE_URL ?>/modules/presupuesto/view_importado.php?id=<?= $id ?>&edit=<?= (int) $linea['id'] ?>" class="btn btn-sm btn-light" title="Editar linea">
                                        <i class="bi bi-pencil text-primary"></i>
                                    </a>
                                </td>
                            </tr>
                            <?php endif; ?>
                        <?php endforeach; ?>
                        </tbody>
                        <tfoot class="table-primary">
                            <tr>
                                <td colspan="6" class="px-4 fw-700">TOTAL GENERAL</td>
                                <td class="text-end fw-800 fs-5 text-primary">$<?= number_format((float) $presupuesto['total_general'], 2) ?></td>
                                <td></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>

<?php include __DIR__ . '/../../includes/footer.php'; ?>
