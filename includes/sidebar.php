<?php $currentPage = $currentPage ?? ''; ?>

<nav id="sidebar">
    <div class="brand">
        <div class="brand-inner">
            <img src="<?= BASE_URL ?>/assets/geosis-pro-mark.svg" alt="GEOSIS-PRO" class="brand-logo">
            <div>
                <h4><span class="brand-orange">GEOSIS</span>-PRO</h4>
                <small>Presupuestos, APUs y costos de obra</small>
            </div>
        </div>
    </div>

    <div class="mt-2">
        <div class="nav-section">Principal</div>
        <a href="<?= BASE_URL ?>/index.php"
           class="nav-link <?= $currentPage === 'dashboard' ? 'active' : '' ?>">
            <i class="bi bi-grid-1x2-fill"></i> Dashboard
        </a>

        <div class="nav-section">Gestion Tecnica</div>
        <a href="<?= BASE_URL ?>/modules/rubros/index.php"
           class="nav-link <?= $currentPage === 'rubros' ? 'active' : '' ?>">
            <i class="bi bi-list-columns-reverse"></i> Rubros APU
        </a>
        <a href="<?= BASE_URL ?>/modules/recursos/index.php"
           class="nav-link <?= $currentPage === 'recursos' ? 'active' : '' ?>">
            <i class="bi bi-box-seam-fill"></i> Recursos
        </a>

        <div class="nav-section">Proyectos</div>
        <a href="<?= BASE_URL ?>/modules/proyectos/index.php"
           class="nav-link <?= $currentPage === 'proyectos' ? 'active' : '' ?>">
            <i class="bi bi-building-fill"></i> Proyectos
        </a>
        <a href="<?= BASE_URL ?>/modules/presupuesto/index.php"
           class="nav-link <?= $currentPage === 'presupuesto' ? 'active' : '' ?>">
            <i class="bi bi-calculator-fill"></i> Presupuestos
        </a>
        <a href="<?= BASE_URL ?>/modules/presupuesto/import_excel.php"
           class="nav-link <?= $currentPage === 'presupuesto' ? 'active' : '' ?>">
            <i class="bi bi-file-earmark-excel-fill"></i> Importar Excel
        </a>
    </div>

    <div class="sidebar-footer pb-3 px-3">
        <small class="d-block">
            <i class="bi bi-circle-fill"></i>
            v1.0.0 &mdash; GEOSIS-PRO
        </small>
    </div>
</nav>
