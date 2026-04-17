# GEOSIS-PRO en Odoo

## Objetivo

Reconstruir `GEOSIS-PRO` como una solucion completa en `Odoo`, tomando como base funcional el sistema actual en `PHP + MySQL`.

Esto no sera una migracion directa del codigo actual.
Sera una `reimplementacion por modulos en Odoo` con migracion de datos.

## Estado actual del sistema PHP

Tablas clave ya existentes en la app actual:

- `recursos`
- `rubros`
- `rubro_recursos`
- `proyectos`
- `presupuesto_items`
- `presupuestos`
- `presupuesto_capitulos`
- `presupuesto_lineas`

Flujos ya resueltos en la app actual:

- catalogo de recursos
- catalogo de rubros/APU
- detalle de recursos por rubro
- proyectos
- presupuestos
- importacion de Excel estilo InterPro
- recalculo y visualizacion web

## Decision recomendada

Si el objetivo es tener un producto serio, escalable y comercializable, la recomendacion es:

1. `Congelar la app PHP` como referencia funcional.
2. `Crear GEOSIS-PRO en Odoo` como addons personalizados.
3. `Migrar los datos` desde MySQL a Odoo.
4. `Desactivar gradualmente` la app PHP cuando el modulo Odoo ya cubra lo necesario.

## Version asumida

Para planificar, asumiremos `Odoo 17 Community`.

Si luego tu maquina virtual usa `Odoo 16` o `Odoo 18`, la estructura general cambia muy poco.

## Arquitectura recomendada en Odoo

No conviene hacer un solo modulo gigante.
Conviene separarlo asi:

### 1. `geosis_base`

Responsabilidad:

- configuracion general
- secuencias
- parametros de empresa
- catalogos base
- permisos iniciales

Dependencias sugeridas:

- `base`
- `mail`

Modelos sugeridos:

- `geosis.company.settings`
- `geosis.stage`
- `geosis.import.log`

### 2. `geosis_recursos`

Responsabilidad:

- catalogo de recursos
- clasificacion por categoria
- unidad
- precio
- estado activo/inactivo

Modelo principal:

- `geosis.resource`

Campos sugeridos:

- `name`
- `code`
- `category`
- `uom_id`
- `price`
- `active`
- `description`

Categorias:

- `M` equipos
- `N` mano de obra
- `O` materiales
- `P` transporte

### 3. `geosis_apu`

Responsabilidad:

- rubros/APU
- detalle de recursos por APU
- costos directos
- indirectos
- valor ofertado

Modelos principales:

- `geosis.apu`
- `geosis.apu.line`

Mapa desde MySQL:

- `rubros` -> `geosis.apu`
- `rubro_recursos` -> `geosis.apu.line`

Campos sugeridos en `geosis.apu`:

- `name`
- `code`
- `uom_id`
- `description`
- `indirect_percent`
- `direct_cost`
- `indirect_value`
- `total_cost`
- `active`

Campos sugeridos en `geosis.apu.line`:

- `apu_id`
- `resource_id`
- `category`
- `sequence`
- `quantity`
- `rate`
- `performance`
- `cost`
- `percentage`
- `distance`
- `note`

Logica clave:

- recalculo automatico del costo directo
- calculo de indirectos
- total ofertado

### 4. `geosis_presupuesto`

Responsabilidad:

- proyectos
- presupuestos
- capitulos
- lineas
- versionado
- totales

Modelos principales:

- `geosis.project`
- `geosis.budget`
- `geosis.budget.chapter`
- `geosis.budget.line`

Mapa desde MySQL:

- `proyectos` -> `geosis.project`
- `presupuestos` -> `geosis.budget`
- `presupuesto_capitulos` -> `geosis.budget.chapter`
- `presupuesto_lineas` -> `geosis.budget.line`
- `presupuesto_items` -> solo apoyo de migracion, no modelo final obligatorio

Campos sugeridos en `geosis.project`:

- `name`
- `code`
- `client_name`
- `offerer_name`
- `location`
- `start_date`
- `end_date`
- `offer_date`
- `currency_id`
- `vat_percent`
- `state`
- `description`

Campos sugeridos en `geosis.budget`:

- `name`
- `project_id`
- `version`
- `state`
- `origin`
- `budget_date`
- `currency_id`
- `direct_subtotal`
- `indirect_percent`
- `indirect_value`
- `offer_subtotal`
- `vat_percent`
- `vat_value`
- `total_amount`
- `note`

Campos sugeridos en `geosis.budget.chapter`:

- `budget_id`
- `parent_id`
- `item_number`
- `code`
- `name`
- `chapter_type`
- `level`
- `sequence`
- `total`

Campos sugeridos en `geosis.budget.line`:

- `budget_id`
- `chapter_id`
- `item_number`
- `apu_id`
- `apu_code`
- `description`
- `uom_id`
- `quantity`
- `price_unit`
- `price_total`
- `line_type`
- `is_optional`
- `origin_sheet`
- `sequence`
- `note`

Logica clave:

- recalculo por linea
- recalculo por capitulo
- recalculo general del presupuesto
- soporte para titulos y rubros

### 5. `geosis_import_excel`

Responsabilidad:

- asistente para importar Excel
- lectura de hoja `Presupuesto`
- creacion de APUs
- creacion de recursos
- vinculacion de hojas APU

Tipo de implementacion:

- `TransientModel` wizard

Modelos sugeridos:

- `geosis.import.wizard`
- `geosis.import.wizard.line` opcional

Entradas:

- archivo binario `.xlsx`
- nombre del archivo
- opcion de crear proyecto nuevo o reutilizar uno

Salidas:

- proyecto
- presupuesto
- capitulos
- lineas
- APUs
- recursos
- log de importacion

### 6. `geosis_reportes`

Responsabilidad:

- reportes PDF
- impresion de presupuesto
- impresion de ficha APU
- reportes resumidos

Tecnologia:

- `QWeb PDF`

Reportes iniciales:

- presupuesto general
- ficha APU
- resumen por capitulos

## Estructura sugerida de carpetas

```text
custom_addons/
  geosis_base/
    __init__.py
    __manifest__.py
    security/
      ir.model.access.csv
    data/
      sequences.xml
      geosis_data.xml
    models/
      __init__.py
      settings.py
    views/
      settings_views.xml
      menus.xml

  geosis_recursos/
    __init__.py
    __manifest__.py
    security/
      ir.model.access.csv
    models/
      __init__.py
      geosis_resource.py
    views/
      geosis_resource_views.xml
      menus.xml

  geosis_apu/
    __init__.py
    __manifest__.py
    security/
      ir.model.access.csv
    models/
      __init__.py
      geosis_apu.py
      geosis_apu_line.py
    views/
      geosis_apu_views.xml
      menus.xml

  geosis_presupuesto/
    __init__.py
    __manifest__.py
    security/
      ir.model.access.csv
    models/
      __init__.py
      geosis_project.py
      geosis_budget.py
      geosis_budget_chapter.py
      geosis_budget_line.py
    views/
      geosis_project_views.xml
      geosis_budget_views.xml
      menus.xml

  geosis_import_excel/
    __init__.py
    __manifest__.py
    security/
      ir.model.access.csv
    wizard/
      __init__.py
      import_budget_wizard.py
    views/
      import_budget_wizard_views.xml

  geosis_reportes/
    __init__.py
    __manifest__.py
    report/
      budget_report.xml
      budget_report_template.xml
      apu_report.xml
      apu_report_template.xml
```

## Mapa de datos: MySQL -> Odoo

| MySQL | Odoo | Nota |
|---|---|---|
| `recursos` | `geosis.resource` | Catalogo maestro |
| `rubros` | `geosis.apu` | APU/rubro |
| `rubro_recursos` | `geosis.apu.line` | Lineas del APU |
| `proyectos` | `geosis.project` | Proyecto base |
| `presupuestos` | `geosis.budget` | Cabecera/version |
| `presupuesto_capitulos` | `geosis.budget.chapter` | Estructura jerarquica |
| `presupuesto_lineas` | `geosis.budget.line` | Detalle final |
| `presupuesto_items` | apoyo temporal | No debe ser el modelo final principal |

## Orden recomendado de construccion

### Fase 1. Base tecnica

- levantar repositorio de addons
- configurar `addons_path`
- crear `geosis_base`
- crear menus raiz
- crear grupos y permisos

### Fase 2. Recursos

- crear modelo `geosis.resource`
- vistas tree/form/search
- filtros por categoria
- activar/inactivar recursos

### Fase 3. APU

- crear modelo `geosis.apu`
- crear lineas `geosis.apu.line`
- recalculos automaticos
- vista ficha APU

### Fase 4. Presupuesto

- crear proyecto
- crear presupuesto
- crear capitulos
- crear lineas
- recalculo general

### Fase 5. Importacion Excel

- wizard de importacion
- lectura de archivo
- validacion de estructura
- creacion masiva de registros
- log de importacion

### Fase 6. Reportes

- PDF presupuesto
- PDF ficha APU
- resumen general

### Fase 7. Comercializacion y control

- usuarios y roles finos
- portal o acceso cliente
- suscripciones o licenciamiento
- auditoria

## Seguridad recomendada

Grupos iniciales:

- `GEOSIS Administrador`
- `GEOSIS Presupuestador`
- `GEOSIS Consulta`

Permisos sugeridos:

- administrador: todo
- presupuestador: crear y editar recursos, APUs, presupuestos
- consulta: solo lectura

## Estrategia de migracion de datos

Orden recomendado:

1. migrar recursos
2. migrar APUs
3. migrar lineas de APU
4. migrar proyectos
5. migrar presupuestos
6. migrar capitulos
7. migrar lineas de presupuesto

Recomendacion practica:

- guardar el `id_legacy` de MySQL en Odoo para trazabilidad
- migrar primero una base pequeña de prueba
- validar totales antes de migrar todo

Campos legacy recomendados:

- `legacy_mysql_id`
- `legacy_source`

## Lo que NO conviene hacer

- no intentar copiar el codigo PHP dentro de Odoo
- no meter todos los modelos en un solo modulo
- no migrar datos sin probar primero calculos y totales
- no apagar la app PHP hasta validar reportes e importacion

## MVP recomendado en Odoo

La primera version util de Odoo deberia incluir solo esto:

- recursos
- APUs
- proyectos
- presupuestos
- importacion Excel
- PDF de presupuesto
- PDF de ficha APU

Con eso ya puedes operar y luego crecer.

## Siguiente paso recomendado

El siguiente paso real ya no es mas teoria.
Es este:

1. crear la carpeta de addons personalizados
2. generar `geosis_base`
3. generar `geosis_recursos`
4. generar el menu principal `GEOSIS-PRO`

## Decision de trabajo

Si seguimos por esta ruta, el proximo entregable deberia ser:

`scaffold inicial de los addons Odoo de GEOSIS-PRO`

Eso ya incluye:

- estructura de carpetas
- manifiestos
- init
- seguridad base
- menu principal
