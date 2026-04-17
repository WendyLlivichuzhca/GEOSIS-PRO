<?php
require_once __DIR__ . '/../config/database.php';

$db = getDB();
$id = intval($_GET['id'] ?? 0);

$rubro = $db->prepare("SELECT * FROM rubros WHERE id=? AND activo=1");
$rubro->execute([$id]);
$rubro = $rubro->fetch();
if (!$rubro) {
    die('Rubro no encontrado');
}

$detalle = $db->prepare("
    SELECT rr.*, rec.descripcion, rec.unidad AS rec_unidad
    FROM rubro_recursos rr
    JOIN recursos rec ON rec.id = rr.recurso_id
    WHERE rr.rubro_id = ?
    ORDER BY rr.categoria, rec.descripcion
");
$detalle->execute([$id]);
$detalle = $detalle->fetchAll();

$grupos = ['M' => [], 'N' => [], 'O' => [], 'P' => []];
foreach ($detalle as $d) {
    $grupos[$d['categoria']][] = $d;
}

$subtotales = [];
foreach ($grupos as $cat => $items) {
    $subtotales[$cat] = array_sum(array_column($items, 'costo'));
}
$total_directo = array_sum($subtotales);
$indirectos = $total_directo * ($rubro['indirectos'] / 100);
$costo_total = $total_directo + $indirectos;

$catInfo = [
    'M' => 'EQUIPOS',
    'N' => 'MANO DE OBRA',
    'O' => 'MATERIALES',
    'P' => 'TRANSPORTE',
];

$fecha = date('d/m/Y');
?>
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>GEOSIS-PRO - APU - <?= htmlspecialchars($rubro['nombre']) ?></title>
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; font-family: Arial, sans-serif; font-size: 11px; }
    body { padding: 20px; color: #222; }
    .header { display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; margin-bottom: 12px; border-bottom: 3px solid #1279bf; padding-bottom: 10px; }
    .brand-block { display: flex; align-items: flex-start; gap: 12px; }
    .brand-logo { width: 54px; height: 54px; }
    .header h1 { font-size: 20px; color: #1279bf; font-weight: 800; }
    .header h1 .brand-orange { color: #e16f00; }
    .header .sub { color: #666; font-size: 9px; }
    .ficha { background: #f0f4ff; border: 1px solid #c7d7f9; border-radius: 6px; padding: 10px 14px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }
    .ficha .left .code { font-size: 9px; color: #666; text-transform: uppercase; }
    .ficha .left .nombre { font-size: 14px; font-weight: 800; color: #1279bf; }
    .ficha .left .meta { font-size: 9px; color: #555; margin-top: 3px; }
    .ficha .right { text-align: right; }
    .ficha .right .label { font-size: 9px; color: #666; text-transform: uppercase; }
    .ficha .right .valor { font-size: 22px; font-weight: 800; color: #1279bf; }
    .sec-header { display: flex; justify-content: space-between; align-items: center; color: #fff; padding: 5px 10px; margin-bottom: 0; font-weight: 700; font-size: 10px; }
    .sec-header.eq { background: #1279bf; }
    .sec-header.mo { background: #0c5f97; }
    .sec-header.mat { background: #e16f00; }
    .sec-header.tra { background: #4b91c6; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
    table thead th { background: #e8edf5; color: #333; padding: 5px 8px; text-align: left; font-size: 9px; border: 1px solid #ccd5e0; }
    table thead th:nth-child(2),
    table thead th:nth-child(3),
    table thead th:nth-child(4),
    table thead th:nth-child(5) { text-align: center; }
    table thead th:last-child { text-align: right; }
    table tbody td { padding: 5px 8px; border: 1px solid #dde3ec; vertical-align: middle; }
    table tbody td:nth-child(2),
    table tbody td:nth-child(3),
    table tbody td:nth-child(4) { text-align: center; }
    table tbody td:last-child { text-align: right; font-weight: 600; }
    table tbody tr:nth-child(even) { background: #f8f9fa; }
    .empty-row td { color: #999; text-align: center; font-style: italic; }
    .resumen { margin-top: 4px; border-top: 2px solid #1279bf; }
    .resumen table { margin-bottom: 0; }
    .resumen table td { padding: 5px 8px; border: 1px solid #dde3ec; }
    .resumen table td:last-child { text-align: right; font-weight: 700; }
    .row-total { background: #dbeafe !important; }
    .row-ofertado { background: #fff1e5 !important; }
    .row-total td, .row-ofertado td { font-weight: 800 !important; font-size: 12px; }
    .nota { margin-top: 12px; font-size: 9px; color: #777; border-top: 1px solid #dde3ec; padding-top: 8px; }
    @media print { body { padding: 8px; } .no-print { display: none; } }
</style>
</head>
<body>

<div class="no-print" style="margin-bottom: 15px;">
    <button onclick="window.print()" style="background: #1279bf; color: #fff; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 12px;">
        Imprimir / Guardar PDF
    </button>
    <button onclick="window.close()" style="background: #6c757d; color: #fff; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 12px; margin-left: 8px;">
        Cerrar
    </button>
</div>

<div class="header">
    <div class="brand-block">
        <img src="<?= BASE_URL ?>/assets/geosis-pro-mark.svg" alt="GEOSIS-PRO" class="brand-logo">
        <div>
            <h1><span class="brand-orange">GEOSIS</span>-PRO</h1>
            <div class="sub">Presupuestos, APUs y costos de obra</div>
            <div class="sub">Fecha: <?= $fecha ?></div>
        </div>
    </div>
    <div style="text-align: right;">
        <div style="font-size: 13px; font-weight: 700; color: #333;">ANALISIS DE PRECIO UNITARIO</div>
        <div class="sub">ESTOS PRECIOS NO INCLUYEN IVA</div>
    </div>
</div>

<div class="ficha">
    <div class="left">
        <div class="code">Codigo: <?= htmlspecialchars($rubro['codigo'] ?? '-') ?></div>
        <div class="nombre"><?= htmlspecialchars($rubro['nombre']) ?></div>
        <div class="meta">
            Unidad: <strong><?= htmlspecialchars($rubro['unidad']) ?></strong>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            Indirectos y utilidades: <strong><?= number_format($rubro['indirectos'], 2) ?>%</strong>
        </div>
    </div>
    <div class="right">
        <div class="label">Valor ofertado</div>
        <div class="valor">$<?= number_format($costo_total, 2) ?></div>
    </div>
</div>

<?php foreach ($catInfo as $cat => $label):
    $clsMap = ['M' => 'eq', 'N' => 'mo', 'O' => 'mat', 'P' => 'tra'];
    $cls = $clsMap[$cat];
?>
<div class="sec-header <?= $cls ?>">
    <span><?= $cat ?> - <?= $label ?></span>
    <span>$<?= number_format($subtotales[$cat] ?? 0, 2) ?></span>
</div>
<table>
    <thead>
        <tr>
            <th style="width: 40%">Descripcion</th>
            <th style="width: 10%">Unidad</th>
            <th style="width: 12%">Cantidad</th>
            <th style="width: 12%">Tarifa</th>
            <th style="width: 12%">Rendimiento</th>
            <th style="width: 14%">Costo</th>
        </tr>
    </thead>
    <tbody>
    <?php if (empty($grupos[$cat])): ?>
        <tr class="empty-row"><td colspan="6">Sin items en esta categoria</td></tr>
    <?php else: foreach ($grupos[$cat] as $item): ?>
        <tr>
            <td><?= htmlspecialchars($item['descripcion']) ?></td>
            <td style="text-align: center;"><?= htmlspecialchars($item['rec_unidad'] ?? '') ?></td>
            <td><?= number_format($item['cantidad'], 4) ?></td>
            <td><?= number_format($item['tarifa'], 4) ?></td>
            <td><?= number_format($item['rendimiento'], 4) ?></td>
            <td>$<?= number_format($item['costo'], 4) ?></td>
        </tr>
    <?php endforeach; endif; ?>
    </tbody>
</table>
<?php endforeach; ?>

<div class="resumen">
    <table>
        <tbody>
            <tr>
                <td style="width: 60%">A - SUBTOTAL EQUIPOS (M)</td>
                <td>$<?= number_format($subtotales['M'] ?? 0, 2) ?></td>
            </tr>
            <tr>
                <td>B - SUBTOTAL MANO DE OBRA (N)</td>
                <td>$<?= number_format($subtotales['N'] ?? 0, 2) ?></td>
            </tr>
            <tr>
                <td>C - SUBTOTAL MATERIALES (O)</td>
                <td>$<?= number_format($subtotales['O'] ?? 0, 2) ?></td>
            </tr>
            <tr>
                <td>D - SUBTOTAL TRANSPORTE (P)</td>
                <td>$<?= number_format($subtotales['P'] ?? 0, 2) ?></td>
            </tr>
            <tr>
                <td>TOTAL COSTO DIRECTO (A+B+C+D)</td>
                <td>$<?= number_format($total_directo, 2) ?></td>
            </tr>
            <tr>
                <td>INDIRECTOS Y UTILIDADES (<?= number_format($rubro['indirectos'], 2) ?>%)</td>
                <td>$<?= number_format($indirectos, 2) ?></td>
            </tr>
            <tr class="row-total">
                <td>COSTO TOTAL DEL RUBRO</td>
                <td>$<?= number_format($costo_total, 2) ?></td>
            </tr>
            <tr class="row-ofertado">
                <td>VALOR OFERTADO</td>
                <td>$<?= number_format($costo_total, 2) ?></td>
            </tr>
        </tbody>
    </table>
</div>

<div class="nota">
    * ESTOS PRECIOS NO INCLUYEN IVA &nbsp;&mdash;&nbsp; Generado con GEOSIS-PRO el <?= $fecha ?>
</div>

</body>
</html>
