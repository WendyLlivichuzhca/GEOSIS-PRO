<?php
require_once __DIR__ . '/../../config/database.php';

$db       = getDB();
$rubro_id = intval($_GET['rubro_id'] ?? 0);

$rubro = $db->prepare("SELECT * FROM rubros WHERE id=?");
$rubro->execute([$rubro_id]);
$rubro = $rubro->fetch();
if (!$rubro) { header('Location: index.php'); exit; }

// Guardar nuevo item
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $recurso_id  = intval($_POST['recurso_id']);
    $categoria   = $_POST['categoria'];
    $cantidad    = floatval($_POST['cantidad']);
    $tarifa      = floatval($_POST['tarifa']);
    $rendimiento = floatval($_POST['rendimiento']);
    $costo       = $cantidad * $tarifa * $rendimiento;

    $db->prepare("INSERT INTO rubro_recursos (rubro_id,recurso_id,categoria,cantidad,tarifa,rendimiento,costo)
                  VALUES (?,?,?,?,?,?,?)")
       ->execute([$rubro_id, $recurso_id, $categoria, $cantidad, $tarifa, $rendimiento, $costo]);

    header("Location: add_recurso.php?rubro_id=$rubro_id");
    exit;
}

// Eliminar item
if (isset($_GET['del'])) {
    $db->prepare("DELETE FROM rubro_recursos WHERE id=? AND rubro_id=?")
       ->execute([intval($_GET['del']), $rubro_id]);
    header("Location: add_recurso.php?rubro_id=$rubro_id");
    exit;
}

// Recursos disponibles
$recursos = $db->query("SELECT * FROM recursos WHERE activo=1 ORDER BY categoria, descripcion")->fetchAll();

// Items actuales
$items = $db->prepare("
    SELECT rr.*, rec.descripcion, rec.unidad AS rec_unidad
    FROM rubro_recursos rr
    JOIN recursos rec ON rec.id = rr.recurso_id
    WHERE rr.rubro_id = ?
    ORDER BY rr.categoria, rec.descripcion
");
$items->execute([$rubro_id]);
$items = $items->fetchAll();

$grupos = ['M'=>[], 'N'=>[], 'O'=>[], 'P'=>[]];
foreach ($items as $i) $grupos[$i['categoria']][] = $i;
$subtotales = [];
foreach ($grupos as $cat => $its) $subtotales[$cat] = array_sum(array_column($its, 'costo'));
$total = array_sum($subtotales);
$indir = $total * ($rubro['indirectos'] / 100);

$pageTitle   = 'Recursos del Rubro';
$currentPage = 'rubros';
$catInfo = ['M'=>'Equipos','N'=>'Mano de Obra','O'=>'Materiales','P'=>'Transporte'];

include __DIR__ . '/../../includes/header.php';
include __DIR__ . '/../../includes/sidebar.php';
?>

<div id="main">
    <div id="topbar">
        <button class="btn btn-sm btn-light d-md-none" id="menuToggle"><i class="bi bi-list fs-5"></i></button>
        <div>
            <div class="page-title">Recursos del Rubro</div>
            <nav aria-label="breadcrumb"><ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="index.php">Rubros</a></li>
                <li class="breadcrumb-item active"><?= htmlspecialchars($rubro['nombre']) ?></li>
            </ol></nav>
        </div>
        <div class="ms-auto">
            <a href="view.php?id=<?= $rubro_id ?>" class="btn btn-sm btn-success">
                <i class="bi bi-eye me-1"></i> Ver Ficha APU
            </a>
        </div>
    </div>

    <div class="p-4">
        <div class="row g-3">
            <!-- FORMULARIO -->
            <div class="col-12 col-lg-4">
                <div class="card sticky-top" style="top:80px">
                    <div class="card-header py-3 px-4">
                        <i class="bi bi-plus-circle me-2 text-primary"></i>Agregar Recurso
                    </div>
                    <div class="card-body p-4">
                        <form method="POST">
                            <div class="mb-3">
                                <label class="form-label fw-500">Categoría</label>
                                <select name="categoria" class="form-select" id="selCat" onchange="filtrarRecursos()">
                                    <option value="M">M - Equipos</option>
                                    <option value="N">N - Mano de Obra</option>
                                    <option value="O">O - Materiales</option>
                                    <option value="P">P - Transporte</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-500">Recurso</label>
                                <select name="recurso_id" class="form-select" id="selRecurso" onchange="autoTarifa()">
                                    <?php foreach ($recursos as $rec): ?>
                                    <option value="<?= $rec['id'] ?>"
                                            data-cat="<?= $rec['categoria'] ?>"
                                            data-precio="<?= $rec['precio'] ?>">
                                        <?= htmlspecialchars($rec['descripcion']) ?>
                                    </option>
                                    <?php endforeach; ?>
                                </select>
                            </div>
                            <div class="row g-2">
                                <div class="col-4">
                                    <label class="form-label fw-500 small">Cantidad</label>
                                    <input type="number" name="cantidad" class="form-control form-control-sm"
                                           step="0.0001" min="0" value="1" id="inpCantidad" onchange="calcCosto()">
                                </div>
                                <div class="col-4">
                                    <label class="form-label fw-500 small">Tarifa</label>
                                    <input type="number" name="tarifa" class="form-control form-control-sm"
                                           step="0.0001" min="0" id="inpTarifa" onchange="calcCosto()">
                                </div>
                                <div class="col-4">
                                    <label class="form-label fw-500 small">Rendimiento</label>
                                    <input type="number" name="rendimiento" class="form-control form-control-sm"
                                           step="0.0001" min="0" value="1" id="inpRendimiento" onchange="calcCosto()">
                                </div>
                            </div>
                            <div class="mt-2 p-2 bg-light rounded small">
                                Costo estimado: <strong id="lblCosto">$0.00</strong>
                            </div>
                            <button type="submit" class="btn btn-primary w-100 mt-3">
                                <i class="bi bi-plus-lg me-1"></i> Agregar
                            </button>
                        </form>
                    </div>
                </div>
            </div>

            <!-- TABLA DE ITEMS -->
            <div class="col-12 col-lg-8">
                <?php foreach ($catInfo as $cat => $catLabel): ?>
                <div class="card mb-3">
                    <div class="card-header d-flex justify-content-between py-2 px-4">
                        <strong><?= $cat ?> — <?= $catLabel ?></strong>
                        <span class="fw-700">$<?= number_format($subtotales[$cat] ?? 0, 2) ?></span>
                    </div>
                    <div class="card-body p-0">
                        <table class="table table-sm align-middle mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th class="px-3">Descripción</th>
                                    <th class="text-center">Cant.</th>
                                    <th class="text-center">Tarifa</th>
                                    <th class="text-center">Rend.</th>
                                    <th class="text-end">Costo</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody>
                            <?php if (empty($grupos[$cat])): ?>
                                <tr><td colspan="6" class="text-muted text-center py-2 small">Sin items</td></tr>
                            <?php else: foreach ($grupos[$cat] as $it): ?>
                                <tr>
                                    <td class="px-3 small"><?= htmlspecialchars($it['descripcion']) ?></td>
                                    <td class="text-center small"><?= number_format($it['cantidad'],4) ?></td>
                                    <td class="text-center small"><?= number_format($it['tarifa'],4) ?></td>
                                    <td class="text-center small"><?= number_format($it['rendimiento'],4) ?></td>
                                    <td class="text-end small fw-600">$<?= number_format($it['costo'],2) ?></td>
                                    <td>
                                        <a href="?rubro_id=<?= $rubro_id ?>&del=<?= $it['id'] ?>"
                                           onclick="return confirm('¿Eliminar?')"
                                           class="btn btn-sm btn-light"><i class="bi bi-trash text-danger"></i></a>
                                    </td>
                                </tr>
                            <?php endforeach; endif; ?>
                            </tbody>
                        </table>
                    </div>
                </div>
                <?php endforeach; ?>

                <!-- RESUMEN -->
                <div class="card">
                    <div class="card-body">
                        <table class="table table-sm mb-0">
                            <tr><td>Total Costo Directo</td><td class="text-end fw-700">$<?= number_format($total,2) ?></td></tr>
                            <tr><td>Indirectos (<?= $rubro['indirectos'] ?>%)</td><td class="text-end">$<?= number_format($indir,2) ?></td></tr>
                            <tr class="table-primary">
                                <td class="fw-700">VALOR OFERTADO</td>
                                <td class="text-end fw-800 text-primary fs-5">$<?= number_format($total+$indir,2) ?></td>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
const recursos = <?= json_encode(array_column($recursos, null, 'id')) ?>;

function filtrarRecursos() {
    const cat = document.getElementById('selCat').value;
    const sel = document.getElementById('selRecurso');
    [...sel.options].forEach(o => {
        o.style.display = (o.dataset.cat === cat || !o.value) ? '' : 'none';
    });
    sel.value = [...sel.options].find(o => o.dataset.cat === cat)?.value || '';
    autoTarifa();
}

function autoTarifa() {
    const id = document.getElementById('selRecurso').value;
    if (id && recursos[id]) {
        document.getElementById('inpTarifa').value = recursos[id].precio;
    }
    calcCosto();
}

function calcCosto() {
    const c = parseFloat(document.getElementById('inpCantidad').value)||0;
    const t = parseFloat(document.getElementById('inpTarifa').value)||0;
    const r = parseFloat(document.getElementById('inpRendimiento').value)||0;
    document.getElementById('lblCosto').textContent = '$' + (c*t*r).toFixed(2);
}

filtrarRecursos();
</script>

<?php include __DIR__ . '/../../includes/footer.php'; ?>
