<?php
require_once __DIR__ . '/../config/database.php';

$db = getDB();
$id = intval($_GET['id'] ?? 0);

$proyecto = $db->prepare("SELECT * FROM proyectos WHERE id=?");
$proyecto->execute([$id]);
$proyecto = $proyecto->fetch();
if (!$proyecto) {
    die('Proyecto no encontrado');
}

$items = $db->prepare("
    SELECT pi.*,
           r.nombre AS rubro_nombre,
           r.codigo AS rubro_codigo,
           r.unidad,
           r.indirectos,
           COALESCE((SELECT SUM(rr.costo) FROM rubro_recursos rr WHERE rr.rubro_id = r.id), 0) AS costo_directo
    FROM presupuesto_items pi
    JOIN rubros r ON r.id = pi.rubro_id
    WHERE pi.proyecto_id = ?
    ORDER BY pi.orden, pi.id
");
$items->execute([$id]);
$items = $items->fetchAll();

$gran_total = 0;
foreach ($items as &$it) {
    $it['precio_unit'] = $it['costo_directo'] * (1 + $it['indirectos'] / 100);
    $it['subtotal'] = $it['precio_unit'] * $it['cantidad'];
    $gran_total += $it['subtotal'];
}
unset($it);

$fecha = date('d/m/Y');
?>
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>GEOSIS-PRO - Presupuesto - <?= htmlspecialchars($proyecto['nombre']) ?></title>
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; font-family: Arial, sans-serif; font-size: 11px; }
    body { padding: 20px; color: #222; }
    .header { display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; margin-bottom: 20px; border-bottom: 3px solid #1279bf; padding-bottom: 15px; }
    .brand-block { display: flex; align-items: flex-start; gap: 12px; }
    .brand-logo { width: 56px; height: 56px; }
    .header h1 { font-size: 22px; color: #1279bf; font-weight: 800; }
    .header h1 .brand-orange { color: #e16f00; }
    .header .sub { color: #666; font-size: 10px; }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; background: #f8f9fa; padding: 12px; border-radius: 6px; margin-bottom: 18px; }
    .info-grid div { display: flex; flex-direction: column; }
    .info-grid span { font-size: 9px; color: #666; text-transform: uppercase; }
    .info-grid strong { font-size: 11px; color: #222; }
    table { width: 100%; border-collapse: collapse; }
    thead th { background: #1279bf; color: #fff; padding: 7px 10px; text-align: left; font-size: 10px; }
    thead th:last-child,
    thead th:nth-child(3),
    thead th:nth-child(4),
    thead th:nth-child(5) { text-align: right; }
    tbody tr:nth-child(even) { background: #f8f9fa; }
    tbody td { padding: 6px 10px; border-bottom: 1px solid #e9ecef; vertical-align: middle; }
    tbody td:nth-child(3),
    tbody td:nth-child(4),
    tbody td:nth-child(5) { text-align: right; }
    tfoot td { padding: 8px 10px; font-weight: bold; background: #1279bf; color: #fff; }
    tfoot td:last-child { text-align: right; font-size: 13px; }
    .nota { margin-top: 15px; font-size: 9px; color: #666; }
    @media print { body { padding: 10px; } .no-print { display: none; } }
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
        <div style="font-size: 14px; font-weight: 700; color: #333;">PRESUPUESTO DE OBRA</div>
        <div class="sub">ESTOS PRECIOS NO INCLUYEN IVA</div>
    </div>
</div>

<div class="info-grid">
    <div>
        <span>Proyecto</span>
        <strong><?= htmlspecialchars($proyecto['nombre']) ?></strong>
    </div>
    <div>
        <span>Cliente</span>
        <strong><?= htmlspecialchars($proyecto['cliente'] ?? '-') ?></strong>
    </div>
    <div>
        <span>Ubicacion</span>
        <strong><?= htmlspecialchars($proyecto['ubicacion'] ?? '-') ?></strong>
    </div>
    <div>
        <span>Estado</span>
        <strong><?= ucfirst($proyecto['estado']) ?></strong>
    </div>
</div>

<table>
    <thead>
        <tr>
            <th style="width: 60px">Codigo</th>
            <th>Descripcion del Rubro</th>
            <th style="width: 60px">Unidad</th>
            <th style="width: 70px">Cantidad</th>
            <th style="width: 90px">P. Unitario</th>
            <th style="width: 100px">Subtotal</th>
        </tr>
    </thead>
    <tbody>
    <?php if (empty($items)): ?>
        <tr><td colspan="6" style="text-align: center; padding: 20px; color: #999;">Sin rubros en el presupuesto</td></tr>
    <?php else: foreach ($items as $i => $it): ?>
        <tr>
            <td style="color: #666;"><?= htmlspecialchars($it['rubro_codigo'] ?? ($i + 1)) ?></td>
            <td><strong><?= htmlspecialchars($it['rubro_nombre']) ?></strong></td>
            <td style="text-align: center;"><?= htmlspecialchars($it['unidad']) ?></td>
            <td style="text-align: right;"><?= number_format($it['cantidad'], 2) ?></td>
            <td style="text-align: right;">$<?= number_format($it['precio_unit'], 2) ?></td>
            <td style="text-align: right; font-weight: 700;">$<?= number_format($it['subtotal'], 2) ?></td>
        </tr>
    <?php endforeach; endif; ?>
    </tbody>
    <tfoot>
        <tr>
            <td colspan="5">TOTAL PRESUPUESTO</td>
            <td>$<?= number_format($gran_total, 2) ?></td>
        </tr>
    </tfoot>
</table>

<div class="nota">
    * ESTOS PRECIOS NO INCLUYEN IVA &nbsp;&mdash;&nbsp; Generado con GEOSIS-PRO el <?= $fecha ?>
</div>

</body>
</html>
