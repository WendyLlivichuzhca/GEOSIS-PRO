<?php
require_once __DIR__ . '/../../config/database.php';
require_once __DIR__ . '/../../includes/XlsxBudgetImporter.php';

$pageTitle = 'Importar Excel';
$currentPage = 'presupuesto';

$error = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!isset($_FILES['archivo_excel']) || $_FILES['archivo_excel']['error'] !== UPLOAD_ERR_OK) {
        $error = 'Selecciona un archivo XLSX valido para continuar.';
    } else {
        $file = $_FILES['archivo_excel'];
        $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));

        if ($ext !== 'xlsx') {
            $error = 'Solo se permiten archivos con extension .xlsx';
        } else {
            try {
                $importer = new XlsxBudgetImporter();
                $result = $importer->import($file['tmp_name'], getDB());

                $query = http_build_query([
                    'id' => $result['presupuesto_id'],
                    'imported' => 1,
                    'lineas' => $result['line_count'],
                    'rubros' => $result['rubro_count'],
                ]);

                header('Location: view_importado.php?' . $query);
                exit;
            } catch (Throwable $e) {
                $error = $e->getMessage();
            }
        }
    }
}

include __DIR__ . '/../../includes/header.php';
include __DIR__ . '/../../includes/sidebar.php';
?>

<div id="main">
    <div id="topbar">
        <button class="btn btn-sm btn-light d-md-none" id="menuToggle"><i class="bi bi-list fs-5"></i></button>
        <div>
            <div class="page-title">Importar Presupuesto Excel</div>
            <nav aria-label="breadcrumb"><ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="<?= BASE_URL ?>/index.php">Inicio</a></li>
                <li class="breadcrumb-item"><a href="<?= BASE_URL ?>/modules/presupuesto/index.php">Presupuestos</a></li>
                <li class="breadcrumb-item active">Importar Excel</li>
            </ol></nav>
        </div>
    </div>

    <div class="p-4">
        <?php if ($error): ?>
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i><?= htmlspecialchars($error) ?>
        </div>
        <?php endif; ?>

        <div class="row g-3">
            <div class="col-12 col-lg-7">
                <div class="card">
                    <div class="card-header py-3 px-4">
                        <i class="bi bi-file-earmark-excel me-2 text-success"></i>Subir archivo
                    </div>
                    <div class="card-body p-4">
                        <form method="POST" enctype="multipart/form-data">
                            <div class="mb-3">
                                <label class="form-label fw-500">Archivo Excel (.xlsx)</label>
                                <input type="file" name="archivo_excel" class="form-control" accept=".xlsx" required>
                            </div>

                            <button type="submit" class="btn btn-success">
                                <i class="bi bi-upload me-1"></i> Importar presupuesto
                            </button>
                            <a href="<?= BASE_URL ?>/modules/presupuesto/index.php" class="btn btn-outline-secondary ms-2">
                                Cancelar
                            </a>
                        </form>
                    </div>
                </div>
            </div>

            <div class="col-12 col-lg-5">
                <div class="card">
                    <div class="card-header py-3 px-4">
                        <i class="bi bi-info-circle me-2 text-primary"></i>Que importa esta pantalla
                    </div>
                    <div class="card-body p-4">
                        <div class="small text-muted mb-3">
                            Esta primera version esta pensada para archivos estilo InterPro con:
                        </div>
                        <ul class="small mb-0">
                            <li>Hoja principal llamada <strong>Presupuesto</strong></li>
                            <li>Columnas de item, codigo, descripcion, unidad, cantidad, precio unitario y total</li>
                            <li>Hojas APU por codigo para crear rubros, recursos y detalle</li>
                        </ul>

                        <hr>

                        <div class="small text-muted mb-2">Resultado de la importacion:</div>
                        <ul class="small mb-0">
                            <li>Crea un proyecto nuevo</li>
                            <li>Crea un presupuesto importado</li>
                            <li>Guarda capitulos y lineas detalladas</li>
                            <li>Genera rubros y recursos cuando encuentra las hojas APU</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<?php include __DIR__ . '/../../includes/footer.php'; ?>
