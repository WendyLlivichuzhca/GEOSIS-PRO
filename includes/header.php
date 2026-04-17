<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= $pageTitle ?? 'GEOSIS-PRO' ?> | GEOSIS-PRO</title>
    <link rel="icon" type="image/svg+xml" href="<?= BASE_URL ?>/assets/geosis-pro-mark.svg">

    <!-- Bootstrap 5 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">

    <style>
        :root {
            --sidebar-w: 280px;
            --brand-blue:        #1279bf;
            --brand-blue-dark:   #0c5f97;
            --brand-blue-soft:   #eaf6ff;
            --brand-orange:      #e16f00;
            --brand-orange-dark: #c45f00;
            --brand-orange-soft: #fff1e5;
            --surface:           #ffffff;
            --bg:                #f4f9fd;
            --border:            #d8e5ef;
            --text:              #1b3347;
            --muted:             #677b8f;
            --shadow:            0 18px 45px rgba(18,121,191,.10);
            --primary:           var(--brand-blue);
            --accent:            var(--brand-orange);
            --bs-primary:        var(--brand-blue);
            --bs-primary-rgb:    18, 121, 191;
            --bs-warning:        var(--brand-orange);
            --bs-warning-rgb:    225, 111, 0;
            --bs-link-color:     var(--brand-blue);
            --bs-link-hover-color: var(--brand-orange);
        }

        * { font-family: 'Inter', sans-serif; }

        body {
            background:
                radial-gradient(circle at top left, rgba(225,111,0,.10), transparent 24%),
                radial-gradient(circle at bottom right, rgba(18,121,191,.10), transparent 22%),
                linear-gradient(180deg, #f8fbfe 0%, var(--bg) 100%);
            color: var(--text);
            min-height: 100vh;
        }

        /* ---- SIDEBAR ---- */
        #sidebar {
            position: fixed;
            top: 0;
            left: 0;
            width: var(--sidebar-w);
            height: 100vh;
            background: linear-gradient(180deg, #ffffff 0%, #f5fbff 100%);
            border-right: 1px solid var(--border);
            box-shadow: 0 0 0 1px rgba(18,121,191,.03), 0 24px 48px rgba(12,95,151,.08);
            display: flex;
            flex-direction: column;
            z-index: 1000;
            transition: transform .3s;
            overflow-y: auto;
        }

        #sidebar .brand {
            padding: 1.35rem 1.1rem 1rem;
            border-bottom: 1px solid var(--border);
            background: linear-gradient(135deg, rgba(18,121,191,.10), rgba(225,111,0,.10));
        }

        #sidebar .brand-inner {
            display: flex;
            align-items: center;
            gap: .9rem;
        }

        #sidebar .brand-logo {
            width: 58px;
            height: 58px;
            flex-shrink: 0;
            filter: drop-shadow(0 10px 20px rgba(12,95,151,.15));
        }

        #sidebar .brand h4 {
            color: var(--brand-blue);
            font-weight: 800;
            margin: 0;
            font-size: 1.38rem;
            letter-spacing: -.06em;
        }

        #sidebar .brand .brand-orange { color: var(--brand-orange); }

        #sidebar .brand small {
            color: var(--muted);
            display: block;
            font-size: .74rem;
            margin-top: .16rem;
        }

        #sidebar .nav-section {
            padding: .8rem 1rem .3rem;
            font-size: .68rem;
            font-weight: 700;
            color: #8195a7;
            text-transform: uppercase;
            letter-spacing: 1.4px;
        }

        #sidebar .nav-link {
            color: var(--text);
            border-radius: 14px;
            margin: 3px .65rem;
            padding: .72rem .85rem;
            display: flex;
            align-items: center;
            gap: .7rem;
            font-size: .9rem;
            font-weight: 500;
            transition: all .2s;
        }

        #sidebar .nav-link:hover { background: rgba(18,121,191,.08); }

        #sidebar .nav-link:hover,
        #sidebar .nav-link.active { color: var(--brand-blue-dark); }

        #sidebar .nav-link.active {
            background: linear-gradient(90deg, rgba(18,121,191,.12), rgba(225,111,0,.14));
            box-shadow: inset 3px 0 0 var(--brand-orange);
            font-weight: 700;
        }

        #sidebar .nav-link i {
            font-size: 1.1rem;
            width: 1.2rem;
            text-align: center;
        }

        #sidebar .sidebar-footer {
            border-top: 1px solid var(--border);
            padding-top: .9rem;
            margin-top: auto;
        }

        #sidebar .sidebar-footer small {
            color: var(--muted);
            font-size: .73rem;
        }

        #sidebar .sidebar-footer i {
            color: var(--brand-orange);
            font-size: .5rem;
        }

        /* ---- MAIN ---- */
        #main {
            margin-left: var(--sidebar-w);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* ---- TOPBAR ---- */
        #topbar {
            background: rgba(255,255,255,.92);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border);
            box-shadow: 0 12px 30px rgba(18,121,191,.04);
            padding: .75rem 1.5rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        #topbar .page-title {
            font-weight: 700;
            font-size: 1.1rem;
            color: var(--text);
        }

        #topbar .breadcrumb { margin: 0; font-size: .8rem; }

        /* ---- CARDS ---- */
        .card {
            border: 1px solid rgba(18,121,191,.08);
            border-radius: 18px;
            box-shadow: var(--shadow);
            overflow: hidden;
        }

        .card-header {
            background: linear-gradient(180deg, rgba(18,121,191,.03), rgba(255,255,255,1));
            border-bottom: 1px solid #edf4f9;
            font-weight: 700;
        }

        /* ---- STAT CARDS ---- */
        .stat-card {
            border-radius: 18px;
            padding: 1.4rem;
            background: rgba(255,255,255,.95);
            border: 1px solid rgba(18,121,191,.08);
            box-shadow: var(--shadow);
        }

        .stat-card .icon {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
        }

        .stat-card .value {
            font-size: 1.8rem;
            font-weight: 800;
            color: var(--brand-blue-dark);
        }

        .stat-card .label {
            font-size: .82rem;
            color: var(--muted);
        }

        /* ---- TABLES ---- */
        .table-hover tbody tr:hover { background: #f3f9fe; }

        .badge-categoria {
            font-size: .7rem;
            padding: .3em .6em;
            border-radius: 6px;
            font-weight: 600;
        }

        /* ---- BUTTONS ---- */
        .btn-primary {
            --bs-btn-bg: var(--brand-blue);
            --bs-btn-border-color: var(--brand-blue);
            --bs-btn-hover-bg: var(--brand-blue-dark);
            --bs-btn-hover-border-color: var(--brand-blue-dark);
            --bs-btn-active-bg: var(--brand-blue-dark);
            --bs-btn-active-border-color: var(--brand-blue-dark);
        }

        .btn-outline-primary {
            --bs-btn-color: var(--brand-blue);
            --bs-btn-border-color: rgba(18,121,191,.35);
            --bs-btn-hover-bg: var(--brand-blue);
            --bs-btn-hover-border-color: var(--brand-blue);
            --bs-btn-active-bg: var(--brand-blue-dark);
            --bs-btn-active-border-color: var(--brand-blue-dark);
        }

        .btn-outline-secondary {
            --bs-btn-color: var(--muted);
            --bs-btn-border-color: #c8d7e4;
            --bs-btn-hover-bg: #eef4f8;
            --bs-btn-hover-border-color: #c0d2e1;
            --bs-btn-hover-color: var(--brand-blue-dark);
        }

        .text-primary { color: var(--brand-blue) !important; }
        .text-warning { color: var(--brand-orange) !important; }

        /* ---- MOBILE ---- */
        @media (max-width: 768px) {
            #sidebar { transform: translateX(-100%); }
            #sidebar.open { transform: translateX(0); }
            #main { margin-left: 0; }
        }
    </style>
</head>
<body>
