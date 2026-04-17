<?php
require_once __DIR__ . '/../../config/database.php';
$db = getDB();
$id = intval($_GET['id'] ?? 0);
if ($id) $db->prepare("UPDATE rubros SET activo=0 WHERE id=?")->execute([$id]);
header('Location: index.php?ok=del');
exit;
