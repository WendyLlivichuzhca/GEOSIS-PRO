<?php

class XlsxBudgetImporter
{
    private $zip;
    private $sharedStrings = [];
    private $sheetPaths = [];
    private $rubroCache = [];
    private $resourceCache = [];
    private $columnLengths = [];

    public function import(string $filePath, PDO $db): array
    {
        if (!class_exists('ZipArchive')) {
            throw new RuntimeException('La extension ZipArchive no esta disponible en PHP.');
        }

        ini_set('memory_limit', '512M');
        set_time_limit(300);

        $this->openWorkbook($filePath);

        try {
            $budget = $this->parseBudgetSheet();

            $db->beginTransaction();

            $projectId = $this->createProject($db, $budget['meta']);
            $presupuestoId = $this->createPresupuesto($db, $projectId, $budget['meta']);

            $currentChapterId = null;
            $chapterStack = [];
            $order = 1;
            $importedRubros = 0;

            foreach ($budget['rows'] as $row) {
                $currentOrder = $order++;

                if ($row['type'] === 'titulo') {
                    $currentChapterId = $this->insertChapter($db, $presupuestoId, $row, $chapterStack);
                    $this->insertBudgetLine($db, $presupuestoId, $currentChapterId, $row, $currentOrder);
                    continue;
                }

                $rubroId = $this->importBudgetRubro($db, $row);
                if ($rubroId !== null) {
                    $importedRubros++;
                }

                $this->insertBudgetLine($db, $presupuestoId, $currentChapterId, $row, $currentOrder, $rubroId);
                $this->insertLegacyBudgetItem($db, $projectId, $rubroId, $row, $currentOrder);
            }

            $this->updatePresupuestoTotals($db, $presupuestoId);

            $db->commit();

            return [
                'project_id' => $projectId,
                'presupuesto_id' => $presupuestoId,
                'line_count' => count($budget['rows']),
                'rubro_count' => $importedRubros,
                'project_name' => $budget['meta']['nombre'],
            ];
        } catch (Throwable $e) {
            if ($db->inTransaction()) {
                $db->rollBack();
            }

            throw $e;
        } finally {
            $this->closeWorkbook();
        }
    }

    private function openWorkbook(string $filePath): void
    {
        $this->zip = new ZipArchive();
        if ($this->zip->open($filePath) !== true) {
            throw new RuntimeException('No se pudo abrir el archivo XLSX.');
        }

        $this->sharedStrings = $this->loadSharedStrings();
        $this->sheetPaths = $this->loadSheetPaths();
    }

    private function closeWorkbook(): void
    {
        if (isset($this->zip)) {
            $this->zip->close();
        }
    }

    private function loadSharedStrings(): array
    {
        $xmlString = $this->readZipEntry('xl/sharedStrings.xml');
        if ($xmlString === null) {
            return [];
        }

        $xml = simplexml_load_string($xmlString);
        if ($xml === false) {
            return [];
        }

        $strings = [];
        foreach ($xml->si as $item) {
            $parts = [];
            if (isset($item->t)) {
                $parts[] = (string) $item->t;
            }

            if (isset($item->r)) {
                foreach ($item->r as $run) {
                    $parts[] = (string) $run->t;
                }
            }

            $strings[] = trim(implode('', $parts));
        }

        return $strings;
    }

    private function loadSheetPaths(): array
    {
        $workbookXml = $this->readZipEntry('xl/workbook.xml');
        $relsXml = $this->readZipEntry('xl/_rels/workbook.xml.rels');

        if ($workbookXml === null || $relsXml === null) {
            throw new RuntimeException('El archivo XLSX no tiene la estructura esperada.');
        }

        $workbook = simplexml_load_string($workbookXml);
        $rels = simplexml_load_string($relsXml);

        if ($workbook === false || $rels === false) {
            throw new RuntimeException('No se pudo leer la estructura interna del XLSX.');
        }

        $workbookNs = $workbook->getNamespaces(true);
        $workbook->registerXPathNamespace('x', $workbookNs[''] ?? 'http://schemas.openxmlformats.org/spreadsheetml/2006/main');
        $workbook->registerXPathNamespace('r', $workbookNs['r'] ?? 'http://schemas.openxmlformats.org/officeDocument/2006/relationships');

        $relationships = [];
        foreach ($rels->Relationship as $rel) {
            $relationships[(string) $rel['Id']] = (string) $rel['Target'];
        }

        $paths = [];
        foreach ($workbook->xpath('//x:sheets/x:sheet') as $sheet) {
            $name = trim((string) $sheet['name']);
            $rid = trim((string) $sheet->attributes($workbookNs['r'] ?? null)['id']);
            $target = $relationships[$rid] ?? null;

            if ($target === null) {
                continue;
            }

            if ($this->startsWith($target, '/')) {
                $paths[$name] = ltrim($target, '/');
            } else {
                $paths[$name] = 'xl/' . ltrim($target, '/');
            }
        }

        return $paths;
    }

    private function parseBudgetSheet(): array
    {
        $sheetName = $this->findBudgetSheetName();
        $rows = $this->readSheetRows($sheetName);
        if (empty($rows)) {
            throw new RuntimeException('La hoja Presupuesto no contiene datos legibles.');
        }

        $meta = [
            'nombre' => $this->cleanText($rows[1][1] ?? 'Proyecto importado'),
            'oferente' => $this->findLabelValue($rows, 'oferente'),
            'ubicacion' => $this->findLabelValue($rows, 'ubicacion'),
            'fecha_oferta' => $this->parseDateValue($this->findLabelRawValue($rows, 'fecha')),
        ];

        $startRow = $this->findBudgetHeaderRow($rows);
        $items = [];
        $blankStreak = 0;

        foreach ($rows as $rowNumber => $cells) {
            if ($rowNumber <= $startRow) {
                continue;
            }

            $item = $this->cleanText($cells[1] ?? '');
            $codigo = $this->normalizeImportedCode($this->cleanText($cells[2] ?? ''), 'RUB');
            $descripcion = $this->cleanText($cells[3] ?? '');
            $unidad = $this->cleanText($cells[4] ?? '');
            $cantidad = $this->toDecimal($cells[5] ?? null);
            $precioUnitario = $this->toDecimal($cells[6] ?? null);
            $precioTotal = $this->toDecimal($cells[7] ?? null);

            if ($item === '' && $codigo === '' && $descripcion === '') {
                $blankStreak++;
                if ($blankStreak >= 25) {
                    break;
                }
                continue;
            }

            $blankStreak = 0;

            if ($codigo === '' && $descripcion === '' && $precioTotal <= 0) {
                continue;
            }

            if ($item === '' && $this->startsWithNormalized($descripcion, 'total')) {
                continue;
            }

            $isTitle = ($codigo === '' && $descripcion !== '');

            $items[] = [
                'type' => $isTitle ? 'titulo' : 'rubro',
                'item_numero' => $item,
                'codigo' => $codigo,
                'descripcion' => $descripcion,
                'unidad' => $unidad,
                'cantidad' => $cantidad,
                'precio_unitario' => $precioUnitario,
                'precio_total' => $precioTotal,
                'origen_hoja' => $codigo !== '' ? $codigo : 'Presupuesto',
            ];
        }

        return [
            'meta' => $meta,
            'rows' => $items,
        ];
    }

    private function createProject(PDO $db, array $meta): int
    {
        $stmt = $db->prepare("
            INSERT INTO proyectos (nombre, cliente, oferente, ubicacion, fecha_oferta, moneda, iva_pct, descripcion, estado)
            VALUES (?, NULL, ?, ?, ?, 'USD', 0.00, 'Importado desde Excel', 'activo')
        ");
        $stmt->execute([
            $meta['nombre'] ?: 'Proyecto importado',
            $meta['oferente'] ?: null,
            $meta['ubicacion'] ?: null,
            $meta['fecha_oferta'] ?: null,
        ]);

        return (int) $db->lastInsertId();
    }

    private function createPresupuesto(PDO $db, int $projectId, array $meta): int
    {
        $stmt = $db->prepare("
            INSERT INTO presupuestos (
                proyecto_id, nombre, version, estado, origen, fecha_presupuesto,
                oferente, ubicacion, moneda, observaciones
            ) VALUES (?, 'Importado desde Excel', 'v1', 'vigente', 'excel', ?, ?, ?, 'USD', ?)
        ");
        $stmt->execute([
            $projectId,
            $meta['fecha_oferta'] ?: null,
            $meta['oferente'] ?: null,
            $meta['ubicacion'] ?: null,
            'Importacion automatica desde archivo XLSX',
        ]);

        return (int) $db->lastInsertId();
    }

    private function insertChapter(PDO $db, int $presupuestoId, array $row, array &$chapterStack): int
    {
        $level = $this->getItemLevel($row['item_numero']);
        $type = $level === 1 ? 'area' : ($level === 2 ? 'capitulo' : 'subcapitulo');
        $parentId = $level > 1 ? ($chapterStack[$level - 1] ?? null) : null;

        $stmt = $db->prepare("
            INSERT INTO presupuesto_capitulos
                (presupuesto_id, parent_id, item_numero, codigo, nombre, tipo, nivel, orden, total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ");
        $stmt->execute([
            $presupuestoId,
            $parentId,
            $row['item_numero'] ?: null,
            null,
            $row['descripcion'],
            $type,
            $level,
            $this->orderFromItem($row['item_numero']),
            $row['precio_total'],
        ]);

        $chapterId = (int) $db->lastInsertId();

        $chapterStack[$level] = $chapterId;
        foreach (array_keys($chapterStack) as $stackLevel) {
            if ($stackLevel > $level) {
                unset($chapterStack[$stackLevel]);
            }
        }

        return $chapterId;
    }

    private function insertBudgetLine(PDO $db, int $presupuestoId, ?int $chapterId, array $row, int $order, ?int $rubroId = null): void
    {
        $stmt = $db->prepare("
            INSERT INTO presupuesto_lineas (
                presupuesto_id, capitulo_id, item_numero, rubro_id, rubro_codigo, descripcion,
                unidad, cantidad, precio_unitario, precio_total, tipo_linea, origen_hoja, orden
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ");
        $stmt->execute([
            $presupuestoId,
            $chapterId,
            $row['item_numero'] ?: null,
            $rubroId,
            $row['codigo'] ?: null,
            $row['descripcion'],
            $row['unidad'] ?: null,
            $row['cantidad'],
            $row['precio_unitario'],
            $row['precio_total'],
            $row['type'] === 'titulo' ? 'titulo' : 'rubro',
            $row['origen_hoja'] ?: null,
            $order,
        ]);
    }

    private function insertLegacyBudgetItem(PDO $db, int $projectId, ?int $rubroId, array $row, int $order): void
    {
        if ($rubroId === null) {
            return;
        }

        $stmt = $db->prepare("
            INSERT INTO presupuesto_items (
                proyecto_id, rubro_id, item_numero, cantidad, precio_unitario_cerrado,
                precio_total_cerrado, origen_hoja, orden
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ");
        $stmt->execute([
            $projectId,
            $rubroId,
            $row['item_numero'] ?: null,
            max(0.0001, $row['cantidad']),
            $row['precio_unitario'] > 0 ? $row['precio_unitario'] : null,
            $row['precio_total'] > 0 ? $row['precio_total'] : null,
            $row['origen_hoja'] ?: null,
            $order,
        ]);
    }

    private function importBudgetRubro(PDO $db, array $budgetRow): ?int
    {
        if ($budgetRow['codigo'] === '') {
            return null;
        }

        if (isset($this->rubroCache[$budgetRow['codigo']])) {
            return $this->rubroCache[$budgetRow['codigo']];
        }

        $apuData = $this->parseApuSheetForCode($budgetRow['codigo']);
        if ($apuData === null) {
            $apuData = [
                'codigo' => $budgetRow['codigo'],
                'nombre' => $budgetRow['descripcion'],
                'unidad' => $budgetRow['unidad'],
                'indirectos' => 0.00,
                'detalles' => [],
            ];
        }

        $rubroId = $this->upsertRubro($db, $apuData);
        $this->rubroCache[$budgetRow['codigo']] = $rubroId;

        return $rubroId;
    }

    private function upsertRubro(PDO $db, array $apuData): int
    {
        $this->assertFitsColumn($db, 'rubros', 'codigo', $apuData['codigo'], 'rubro');

        $find = $db->prepare("SELECT id FROM rubros WHERE codigo = ? LIMIT 1");
        $find->execute([$apuData['codigo']]);
        $existingId = $find->fetchColumn();

        if ($existingId) {
            $update = $db->prepare("
                UPDATE rubros
                SET nombre = ?, unidad = ?, descripcion = ?, indirectos = ?, activo = 1
                WHERE id = ?
            ");
            $update->execute([
                $apuData['nombre'],
                $apuData['unidad'] ?: 'U',
                'Importado desde Excel',
                $apuData['indirectos'],
                $existingId,
            ]);
            $rubroId = (int) $existingId;
        } else {
            $insert = $db->prepare("
                INSERT INTO rubros (codigo, nombre, unidad, descripcion, indirectos, activo)
                VALUES (?, ?, ?, 'Importado desde Excel', ?, 1)
            ");
            $insert->execute([
                $apuData['codigo'],
                $apuData['nombre'],
                $apuData['unidad'] ?: 'U',
                $apuData['indirectos'],
            ]);
            $rubroId = (int) $db->lastInsertId();
        }

        $delete = $db->prepare("DELETE FROM rubro_recursos WHERE rubro_id = ?");
        $delete->execute([$rubroId]);

        foreach ($apuData['detalles'] as $index => $detail) {
            $resourceId = $this->upsertResource($db, $detail);

            $insertDetail = $db->prepare("
                INSERT INTO rubro_recursos (
                    rubro_id, recurso_id, categoria, cantidad, tarifa, rendimiento, costo,
                    porcentaje, distancia, orden, observacion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ");
            $insertDetail->execute([
                $rubroId,
                $resourceId,
                $detail['categoria'],
                $detail['cantidad'],
                $detail['tarifa'],
                $detail['rendimiento'],
                $detail['costo'],
                $detail['porcentaje'],
                $detail['distancia'],
                $index + 1,
                'Importado desde Excel',
            ]);
        }

        return $rubroId;
    }

    private function upsertResource(PDO $db, array $detail): int
    {
        $this->assertFitsColumn($db, 'recursos', 'codigo', $detail['codigo'], 'recurso');

        $cacheKey = $detail['categoria'] . '|' . $detail['codigo'];
        if (isset($this->resourceCache[$cacheKey])) {
            return $this->resourceCache[$cacheKey];
        }

        $find = $db->prepare("SELECT id FROM recursos WHERE codigo = ? AND categoria = ? LIMIT 1");
        $find->execute([$detail['codigo'], $detail['categoria']]);
        $existingId = $find->fetchColumn();

        if ($existingId) {
            $update = $db->prepare("
                UPDATE recursos
                SET descripcion = ?, unidad = ?, precio = ?, activo = 1
                WHERE id = ?
            ");
            $update->execute([
                $detail['descripcion'],
                $detail['unidad'] ?: 'U',
                $detail['tarifa'],
                $existingId,
            ]);
            $resourceId = (int) $existingId;
        } else {
            $insert = $db->prepare("
                INSERT INTO recursos (codigo, descripcion, unidad, precio, categoria, activo)
                VALUES (?, ?, ?, ?, ?, 1)
            ");
            $insert->execute([
                $detail['codigo'],
                $detail['descripcion'],
                $detail['unidad'] ?: 'U',
                $detail['tarifa'],
                $detail['categoria'],
            ]);
            $resourceId = (int) $db->lastInsertId();
        }

        $this->resourceCache[$cacheKey] = $resourceId;

        return $resourceId;
    }

    private function parseApuSheetForCode(string $code): ?array
    {
        $sheetName = $this->findSheetByCode($code);
        if ($sheetName === null) {
            return null;
        }

        $rows = $this->readSheetRows($sheetName);
        if (empty($rows)) {
            return null;
        }

        $apu = [
            'codigo' => $this->cleanText($rows[3][2] ?? $code),
            'nombre' => $this->cleanText($rows[4][2] ?? $code),
            'unidad' => $this->cleanText($rows[5][2] ?? 'U'),
            'indirectos' => 0.00,
            'detalles' => [],
        ];

        $currentCategory = null;
        $inIndirectSection = false;

        foreach ($rows as $cells) {
            $col1 = $this->cleanText($cells[1] ?? '');
            $col2 = $this->cleanText($cells[2] ?? '');

            if ($this->sameNormalized($col1, 'Equipo y herramienta')) {
                $currentCategory = 'M';
                $inIndirectSection = false;
                continue;
            }
            if ($this->sameNormalized($col1, 'Materiales')) {
                $currentCategory = 'O';
                $inIndirectSection = false;
                continue;
            }
            if ($this->sameNormalized($col1, 'Transporte')) {
                $currentCategory = 'P';
                $inIndirectSection = false;
                continue;
            }
            if ($this->sameNormalized($col1, 'Mano de Obra')) {
                $currentCategory = 'N';
                $inIndirectSection = false;
                continue;
            }
            if ($this->sameNormalized($col1, 'COSTOS INDIRECTOS')) {
                $inIndirectSection = true;
                $currentCategory = null;
                continue;
            }

            if ($inIndirectSection && preg_match('/([\d\.,]+)\s*%/', $col1, $match)) {
                $apu['indirectos'] = $this->toDecimal($match[1]);
                $inIndirectSection = false;
                continue;
            }

            if ($currentCategory === null) {
                continue;
            }

            if (
                $col1 === '' ||
                $this->sameNormalized($col1, 'Codigo') ||
                $this->startsWithNormalized($col1, 'Subtotal') ||
                $this->startsWithNormalized($col1, 'Costo Directo Total') ||
                $this->startsWithNormalized($col1, 'Precio Unitario Total') ||
                $this->startsWithNormalized($col1, 'Son:')
            ) {
                continue;
            }

            if ($col2 === '') {
                continue;
            }

            $unidad = $this->cleanText($cells[3] ?? '');
            if ($currentCategory === 'N' && $unidad === '') {
                $unidad = 'HR';
            }

            $detailIndex = count($apu['detalles']) + 1;
            $detailCode = $this->normalizeDetailCode($col1, $apu['codigo'], $detailIndex);

            $apu['detalles'][] = [
                'codigo' => $detailCode,
                'descripcion' => $col2,
                'unidad' => $unidad,
                'categoria' => $currentCategory,
                'cantidad' => $this->toDecimal($cells[4] ?? null),
                'tarifa' => $this->toDecimal($cells[5] ?? null),
                'rendimiento' => $currentCategory === 'P' ? 0.0 : $this->toDecimal($cells[6] ?? null),
                'distancia' => $currentCategory === 'P' ? $this->toDecimal($cells[6] ?? null) : null,
                'costo' => $this->toDecimal($cells[7] ?? null),
                'porcentaje' => $this->parsePercentValue($cells[8] ?? null),
            ];
        }

        return $apu;
    }

    private function updatePresupuestoTotals(PDO $db, int $presupuestoId): void
    {
        $stmt = $db->prepare("
            SELECT COALESCE(SUM(precio_total), 0) AS total
            FROM presupuesto_lineas
            WHERE presupuesto_id = ? AND tipo_linea = 'rubro'
        ");
        $stmt->execute([$presupuestoId]);
        $total = (float) $stmt->fetchColumn();

        $update = $db->prepare("
            UPDATE presupuestos
            SET subtotal_oferta = ?, total_general = ?
            WHERE id = ?
        ");
        $update->execute([$total, $total, $presupuestoId]);
    }

    private function readSheetRows(string $sheetName): array
    {
        $sheetPath = $this->sheetPaths[$sheetName] ?? null;
        if ($sheetPath === null) {
            throw new RuntimeException("No se encontro la hoja {$sheetName} dentro del XLSX.");
        }

        $xmlString = $this->readZipEntry($sheetPath);
        if ($xmlString === null) {
            throw new RuntimeException("No se pudo leer la hoja {$sheetName}.");
        }

        $xml = simplexml_load_string($xmlString);
        if ($xml === false) {
            throw new RuntimeException("No se pudo interpretar la hoja {$sheetName}.");
        }

        $namespaces = $xml->getNamespaces(true);
        $xml->registerXPathNamespace('x', $namespaces[''] ?? 'http://schemas.openxmlformats.org/spreadsheetml/2006/main');

        $rows = [];
        foreach ($xml->xpath('//x:sheetData/x:row') as $row) {
            $rowIndex = (int) $row['r'];
            $cells = [];

            foreach ($row->c as $cell) {
                $reference = (string) $cell['r'];
                if (!preg_match('/([A-Z]+)\d+/', $reference, $match)) {
                    continue;
                }

                $columnIndex = $this->columnToIndex($match[1]);
                $cells[$columnIndex] = $this->readCellValue($cell);
            }

            $rows[$rowIndex] = $cells;
        }

        ksort($rows);

        return $rows;
    }

    private function readCellValue(SimpleXMLElement $cell): string
    {
        $type = (string) $cell['t'];
        $value = isset($cell->v) ? (string) $cell->v : '';

        if ($type === 's') {
            return (string) ($this->sharedStrings[(int) $value] ?? '');
        }

        if ($type === 'inlineStr') {
            return isset($cell->is->t) ? (string) $cell->is->t : '';
        }

        if ($type === 'b') {
            return $value === '1' ? '1' : '0';
        }

        return $value;
    }

    private function findBudgetSheetName(): string
    {
        foreach (array_keys($this->sheetPaths) as $name) {
            if ($this->sameNormalized($name, 'Presupuesto')) {
                return $name;
            }
        }

        foreach (array_keys($this->sheetPaths) as $name) {
            if ($this->startsWithNormalized($name, 'Presupuesto')) {
                return $name;
            }
        }

        throw new RuntimeException('No se encontro una hoja llamada Presupuesto.');
    }

    private function findSheetByCode(string $code): ?string
    {
        if (isset($this->sheetPaths[$code])) {
            return $code;
        }

        foreach (array_keys($this->sheetPaths) as $name) {
            if ($this->startsWith($name, $code . '(')) {
                return $name;
            }
        }

        return null;
    }

    private function findBudgetHeaderRow(array $rows): int
    {
        foreach ($rows as $rowNumber => $cells) {
            $col1 = $this->cleanText($cells[1] ?? '');
            $col2 = $this->cleanText($cells[2] ?? '');
            $col3 = $this->cleanText($cells[3] ?? '');

            if ($this->sameNormalized($col1, 'Item') && $this->sameNormalized($col2, 'Codigo') && $this->sameNormalized($col3, 'Descripcion')) {
                return $rowNumber;
            }
        }

        return 8;
    }

    private function findLabelValue(array $rows, string $label): ?string
    {
        $value = $this->findLabelRawValue($rows, $label);
        $value = $this->cleanText($value);

        return $value !== '' ? $value : null;
    }

    private function findLabelRawValue(array $rows, string $label): ?string
    {
        foreach ($rows as $rowNumber => $cells) {
            if ($rowNumber > 12) {
                break;
            }

            $col1 = $this->cleanText($cells[1] ?? '');
            if ($this->startsWithNormalized($col1, $label)) {
                return (string) ($cells[3] ?? $cells[2] ?? '');
            }
        }

        return null;
    }

    private function parseDateValue(?string $value): ?string
    {
        if ($value === null || trim($value) === '') {
            return null;
        }

        $value = trim($value);

        if (is_numeric($value)) {
            $days = (int) round((float) $value);
            if ($days > 20000 && $days < 80000) {
                $base = new DateTime('1899-12-30');
                $base->modify("+{$days} days");
                return $base->format('Y-m-d');
            }
        }

        $date = DateTime::createFromFormat('d/m/Y', $value);
        if ($date instanceof DateTime) {
            return $date->format('Y-m-d');
        }

        $timestamp = strtotime($value);
        return $timestamp ? date('Y-m-d', $timestamp) : null;
    }

    private function getItemLevel(string $item): int
    {
        if (!preg_match('/^\d+(?:\.\d+)*$/', $item)) {
            return 1;
        }

        return substr_count($item, '.') + 1;
    }

    private function orderFromItem(string $item): int
    {
        if ($item === '') {
            return 0;
        }

        $number = str_replace('.', '', $item);
        return ctype_digit($number) ? (int) $number : 0;
    }

    private function columnToIndex(string $letters): int
    {
        $index = 0;
        $letters = strtoupper($letters);
        foreach (str_split($letters) as $char) {
            $index = ($index * 26) + (ord($char) - 64);
        }

        return $index;
    }

    private function toDecimal($value): float
    {
        if ($value === null) {
            return 0.0;
        }

        $value = trim((string) $value);
        if ($value === '') {
            return 0.0;
        }

        if (is_numeric($value)) {
            return (float) $value;
        }

        $value = str_replace(' ', '', $value);
        if (str_contains($value, ',') && str_contains($value, '.')) {
            $value = str_replace('.', '', $value);
            $value = str_replace(',', '.', $value);
        } elseif (str_contains($value, ',')) {
            $value = str_replace(',', '.', $value);
        }

        return is_numeric($value) ? (float) $value : 0.0;
    }

    private function parsePercentValue($value): ?float
    {
        if ($value === null) {
            return null;
        }

        $value = trim((string) $value);
        if ($value === '') {
            return null;
        }

        $value = str_replace('%', '', $value);
        return $this->toDecimal($value);
    }

    private function cleanText($value): string
    {
        $text = trim((string) $value);
        $text = preg_replace('/\s+/', ' ', $text) ?? $text;
        return $text;
    }

    private function normalizeText(string $text): string
    {
        $text = $this->cleanText($text);
        $ascii = iconv('UTF-8', 'ASCII//TRANSLIT//IGNORE', $text);
        $ascii = $ascii !== false ? $ascii : $text;
        return strtolower($ascii);
    }

    private function normalizeImportedCode(string $code, string $prefix): string
    {
        $code = $this->cleanText($code);
        if ($code === '') {
            return '';
        }

        if ($this->looksLikeCode($code)) {
            return $this->truncateText($code, 100);
        }

        return $this->buildSyntheticCode($prefix, $code);
    }

    private function normalizeDetailCode(string $rawCode, string $apuCode, int $index): string
    {
        $rawCode = $this->cleanText($rawCode);

        if ($this->looksLikeCode($rawCode)) {
            return $this->truncateText($rawCode, 100);
        }

        $base = $apuCode !== '' ? $apuCode : 'APU';
        return $this->truncateText($this->buildSyntheticCode('DET-' . $base . '-' . $index, $rawCode), 100);
    }

    private function looksLikeCode(string $code): bool
    {
        if ($code === '') {
            return false;
        }

        $length = function_exists('mb_strlen') ? mb_strlen($code, 'UTF-8') : strlen($code);
        if ($length > 40) {
            return false;
        }

        if (preg_match('/\s/', $code)) {
            return false;
        }

        return preg_match('/^[A-Za-z0-9._#\/()\-]+$/', $code) === 1;
    }

    private function buildSyntheticCode(string $prefix, string $source): string
    {
        $prefix = strtoupper(preg_replace('/[^A-Za-z0-9\-]/', '-', $prefix) ?? 'IMP');
        $hash = strtoupper(substr(md5($source), 0, 10));
        return $this->truncateText($prefix . '-' . $hash, 100);
    }

    private function truncateText(string $text, int $maxLength): string
    {
        if (function_exists('mb_substr')) {
            return mb_substr($text, 0, $maxLength, 'UTF-8');
        }

        return substr($text, 0, $maxLength);
    }

    private function sameNormalized(string $left, string $right): bool
    {
        return $this->normalizeText($left) === $this->normalizeText($right);
    }

    private function startsWithNormalized(string $text, string $prefix): bool
    {
        return $this->startsWith($this->normalizeText($text), $this->normalizeText($prefix));
    }

    private function readZipEntry(string $path): ?string
    {
        $content = $this->zip->getFromName($path);
        return $content === false ? null : $content;
    }

    private function assertFitsColumn(PDO $db, string $table, string $column, ?string $value, string $label): void
    {
        if ($value === null || $value === '') {
            return;
        }

        $maxLength = $this->getColumnLength($db, $table, $column);
        if ($maxLength === null) {
            return;
        }

        $length = function_exists('mb_strlen') ? mb_strlen($value, 'UTF-8') : strlen($value);
        if ($length > $maxLength) {
            throw new RuntimeException(
                "El codigo del {$label} [{$value}] tiene {$length} caracteres y la columna {$table}.{$column} solo permite {$maxLength}. Ejecuta la migracion de ampliacion de codigos en la base usada por este sitio."
            );
        }
    }

    private function getColumnLength(PDO $db, string $table, string $column): ?int
    {
        $cacheKey = $table . '.' . $column;
        if (array_key_exists($cacheKey, $this->columnLengths)) {
            return $this->columnLengths[$cacheKey];
        }

        $sql = "
            SELECT CHARACTER_MAXIMUM_LENGTH
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = ?
              AND COLUMN_NAME = ?
            LIMIT 1
        ";

        $stmt = $db->prepare($sql);
        $stmt->execute([$table, $column]);
        $length = $stmt->fetchColumn();

        $this->columnLengths[$cacheKey] = $length !== false ? (int) $length : null;

        return $this->columnLengths[$cacheKey];
    }

    private function startsWith(string $text, string $prefix): bool
    {
        return substr($text, 0, strlen($prefix)) === $prefix;
    }
}
