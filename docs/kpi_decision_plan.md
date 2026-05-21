# KPIs de Toma de Decisiones para GEOSIS-PRO

## Objetivo
Definir los KPIs más útiles y realistas para el sistema GEOSIS-PRO usando los datos que ya existen en:

- Proyectos
- Presupuestos
- Rubros contractuales
- Cronograma / tareas
- Libro de obra / bitácoras
- Planillas de avance
- Recursos / APU
- Índices INEC

La idea no es llenar el dashboard de números, sino mostrar indicadores accionables para gerencia, residentes y fiscalización.

## Principios
- Un KPI debe responder una decisión concreta.
- Debe salir de datos ya disponibles en el sistema.
- Debe tener semáforo o umbral para saber si está bien o mal.
- Debe mostrarse en el nivel correcto: ejecutivo, proyecto, obra o fiscalización.

---

## 1. Dashboard Ejecutivo
KPIs para gerente, dueño o director del proyecto.

### KPI 1. Avance físico acumulado del proyecto
- Propósito: saber cuánto de la obra ya está ejecutado.
- Fórmula:
  - `avance_fisico_pct = promedio ponderado de percent_executed de geosis.estimation.line`
  - Alternativa monetaria:
  - `avance_fisico_pct = total_accumulated / total_budget_amount * 100`
- Fuente:
  - `geosis.estimation.total_accumulated`
  - `geosis.estimation.line.percent_executed`
  - `geosis.project.total_budget_amount`
- Frecuencia: diaria
- Umbrales:
  - Verde: `>= plan esperado`
  - Amarillo: `entre -5% y -10% del plan`
  - Rojo: `> -10% del plan`
- Decisión:
  - acelerar recursos
  - reprogramar actividades
  - reforzar supervisión

### KPI 2. Monto ejecutado acumulado
- Propósito: saber cuánto valor económico ya se ha ejecutado.
- Fórmula:
  - `monto_ejecutado = suma(total_accumulated) de planillas del proyecto`
- Fuente:
  - `geosis.estimation.total_accumulated`
- Frecuencia: diaria
- Umbrales:
  - Informativo, con comparación contra presupuesto
- Decisión:
  - controlar flujo financiero
  - revisar ritmo de facturación

### KPI 3. Monto pendiente por ejecutar
- Propósito: saber cuánto falta económica y físicamente.
- Fórmula:
  - `monto_pendiente = total_budget_amount - monto_ejecutado`
- Fuente:
  - `geosis.project.total_budget_amount`
  - `geosis.estimation.total_accumulated`
- Frecuencia: diaria
- Decisión:
  - planificación financiera
  - priorización de obra

### KPI 4. Índice de atraso del proyecto
- Propósito: medir si la obra está retrasada en tareas.
- Fórmula:
  - `indice_atraso = tareas_vencidas_abiertas / total_tareas * 100`
- Fuente:
  - `project.task`
  - fechas `planned_date_end`, `date_deadline`
  - etapa abierta/cerrada
- Frecuencia: diaria
- Umbrales:
  - Verde: `< 10%`
  - Amarillo: `10% a 20%`
  - Rojo: `> 20%`
- Decisión:
  - redistribuir equipo
  - mover prioridades
  - revisar secuencia constructiva

### KPI 5. Tareas críticas activas
- Propósito: ver riesgo alto inmediato.
- Fórmula:
  - `count(project.task where is_critical = True and task abierta)`
- Fuente:
  - `project.task.is_critical`
- Frecuencia: diaria
- Umbrales:
  - Verde: `0`
  - Amarillo: `1 a 3`
  - Rojo: `> 3`
- Decisión:
  - atención gerencial
  - seguimiento diario

### KPI 6. Bitácoras aprobadas del período
- Propósito: validar disciplina operativa y trazabilidad legal.
- Fórmula:
  - `bitacoras_aprobadas / bitacoras_registradas * 100`
- Fuente:
  - `geosis.bitacora.state`
- Frecuencia: diaria / semanal
- Umbrales:
  - Verde: `>= 95%`
  - Amarillo: `80% a 94%`
  - Rojo: `< 80%`
- Decisión:
  - exigir regularización de reportes
  - revisar gestión del residente y fiscalización

---

## 2. Dashboard de Proyecto / Obra
KPIs para residente, supervisor y jefe de obra.

### KPI 7. Tareas abiertas
- Propósito: carga actual operativa.
- Fórmula:
  - `count(tareas en etapas no cerradas)`
- Fuente:
  - `project.task`
- Frecuencia: diaria
- Decisión:
  - balance de trabajo

### KPI 8. Tareas vencidas
- Propósito: detectar incumplimientos inmediatos.
- Fórmula:
  - `count(tareas abiertas con fecha fin < hoy)`
- Fuente:
  - `project.task`
- Frecuencia: diaria
- Decisión:
  - reprogramación diaria

### KPI 9. Cumplimiento del cronograma
- Propósito: comparar lo planificado con lo ejecutado.
- Fórmula propuesta:
  - `% tareas cerradas a tiempo = tareas cerradas antes o en fecha / tareas cerradas`
- Fuente:
  - `project.task`
  - fechas planificadas
  - estado / etapa
- Frecuencia: diaria / semanal
- Umbrales:
  - Verde: `>= 90%`
  - Amarillo: `75% a 89%`
  - Rojo: `< 75%`
- Decisión:
  - refuerzo por frente de trabajo

### KPI 10. Avance diario promedio por rubro
- Propósito: saber cuánto avanzan los rubros en campo.
- Fórmula:
  - `promedio(progress_increment diario por geosis.bitacora.task)`
- Fuente:
  - `geosis.bitacora.task.progress`
  - cálculo del incremento frente al día anterior
- Frecuencia: diaria
- Decisión:
  - detectar frentes improductivos

### KPI 11. Evidencias por día
- Propósito: medir calidad documental del reporte.
- Fórmula:
  - `promedio de geosis.bitacora.photo por bitácora`
- Fuente:
  - `geosis.bitacora.photo`
- Frecuencia: diaria / semanal
- Decisión:
  - exigir respaldo fotográfico suficiente

### KPI 12. Días con lluvia vs días productivos
- Propósito: entender impacto del clima.
- Fórmula:
  - `count(weather in rainy, storm)` y `count(weather in sunny, cloudy)`
- Fuente:
  - `geosis.bitacora.weather`
- Frecuencia: semanal / mensual
- Decisión:
  - justificar atrasos
  - ajustar programación

---

## 3. Dashboard de Costos y Presupuesto
KPIs para dirección financiera, presupuestador y control.

### KPI 13. Variación entre presupuesto y ejecutado
- Propósito: ver desviación económica.
- Fórmula:
  - `variacion_pct = (monto_ejecutado - monto_presupuestado_esperado) / monto_presupuestado_esperado * 100`
- Nota:
  - si no existe línea base temporal, arrancar con:
  - `monto_ejecutado / total_budget_amount * 100`
- Fuente:
  - `geosis.budget.total_amount`
  - `geosis.estimation.total_accumulated`
- Frecuencia: semanal / mensual
- Decisión:
  - revisar sobrecostos

### KPI 14. Costo directo del presupuesto
- Propósito: identificar magnitud base de obra.
- Fórmula:
  - `direct_cost`
- Fuente:
  - `geosis.budget.direct_cost`
- Frecuencia: al aprobar / cambiar presupuesto
- Decisión:
  - control base contractual

### KPI 15. Participación de indirectos
- Propósito: vigilar peso de gastos indirectos.
- Fórmula:
  - `indirect_value / total_amount * 100`
- Fuente:
  - `geosis.budget.indirect_value`
  - `geosis.budget.total_amount`
- Frecuencia: al aprobar presupuesto
- Decisión:
  - optimización de estructura de costos

### KPI 16. VAE % del presupuesto
- Propósito: cumplimiento y análisis contractual.
- Fórmula:
  - `vae_percent`
- Fuente:
  - `geosis.budget.vae_percent`
  - `geosis.apu.vae_percent`
- Frecuencia: al aprobar presupuesto
- Decisión:
  - validación contractual y local

### KPI 17. Composición del costo directo
- Propósito: saber en qué categoría se va el dinero.
- Fórmula:
  - `% materiales`
  - `% mano de obra`
  - `% equipos`
  - `% transporte`
- Fuente:
  - `geosis.apu.line.category`
  - `geosis.apu.line.cost`
- Frecuencia: al aprobar presupuesto / mensual
- Decisión:
  - foco de ahorro
  - sensibilidad ante inflación

### KPI 18. Recursos sin índice INEC
- Propósito: detectar debilidad de reajuste.
- Fórmula:
  - `count(geosis.resource where inec_index_id is null)`
- Fuente:
  - `geosis.resource.inec_index_id`
- Frecuencia: semanal
- Decisión:
  - completar trazabilidad de reajuste

---

## 4. Dashboard de Fiscalización
KPIs para control, auditoría y aprobación.

### KPI 19. Planillas en borrador / presentadas / aprobadas / rechazadas
- Propósito: control del pipeline de cobro.
- Fórmula:
  - conteo por estado
- Fuente:
  - `geosis.estimation.state`
- Frecuencia: diaria
- Decisión:
  - agilizar aprobación
  - detectar cuellos de botella

### KPI 20. Tiempo promedio de aprobación de planillas
- Propósito: medir la velocidad del proceso de validación.
- Requisito:
  - idealmente guardar fecha de envío y fecha de aprobación
- Estado actual:
  - no está completo todavía
- Decisión:
  - mejorar flujo de revisión

### KPI 21. Bitácoras sin firma del contratista
- Propósito: riesgo documental.
- Fórmula:
  - `count(bitácoras con signature_contractor vacío)`
- Fuente:
  - `geosis.bitacora.signature_contractor`
- Frecuencia: diaria
- Decisión:
  - exigir regularización legal

### KPI 22. Bitácoras sin firma del fiscalizador
- Propósito: control de aprobación incompleta.
- Fórmula:
  - `count(bitácoras aprobadas sin signature_inspector)`
- Fuente:
  - `geosis.bitacora.signature_inspector`
- Frecuencia: diaria
- Decisión:
  - evitar reportes sin respaldo

### KPI 23. Bitácoras con evidencia insuficiente
- Propósito: calidad del soporte de obra.
- Fórmula:
  - `count(bitácoras con menos de N fotos)`
- Fuente:
  - `geosis.bitacora.photo_ids`
- Frecuencia: semanal
- Decisión:
  - subir estándar de evidencia

---

## 5. Dashboard de Productividad y Personal
KPIs para gestión de personal y frentes de trabajo.

### KPI 24. Productividad por responsable
- Propósito: comparar desempeño operativo.
- Fórmula:
  - `avance reportado acumulado / número de días reportados por user_id`
- Fuente:
  - `geosis.bitacora.user_id`
  - `geosis.bitacora.task.progress`
- Frecuencia: semanal
- Decisión:
  - reforzar acompañamiento o redistribución

### KPI 25. Tareas asignadas por responsable
- Propósito: medir carga de trabajo.
- Fórmula:
  - `count(project.task por user_id o user_ids)`
- Fuente:
  - `project.task.user_id / user_ids`
- Frecuencia: diaria
- Decisión:
  - balanceo de responsabilidades

### KPI 26. Colaboradores activos por empresa
- Propósito: medir estructura operativa.
- Fuente:
  - `res.users.active`
  - módulo `Mi Equipo`
- Frecuencia: diaria
- Decisión:
  - control de acceso
  - crecimiento de equipo

---

## KPIs Prioritarios para Implementar Primero
Si hay que empezar con lo más útil, recomiendo este orden:

### Fase 1. KPIs esenciales
- Avance físico acumulado
- Monto ejecutado acumulado
- Monto pendiente por ejecutar
- Tareas críticas activas
- Bitácoras aprobadas del período
- Planillas por estado

### Fase 2. KPIs operativos
- Tareas vencidas
- Cumplimiento del cronograma
- Avance diario promedio por rubro
- Días con lluvia vs productivos
- Evidencias por día

### Fase 3. KPIs de costos y calidad
- Composición del costo directo
- VAE %
- Recursos sin índice INEC
- Bitácoras sin firma
- Bitácoras con evidencia insuficiente

---

## Recomendación de Ubicación en la Interfaz

### Dashboard principal
- Avance físico acumulado
- Monto ejecutado acumulado
- Monto pendiente
- Tareas críticas
- Planillas pendientes

### Vista del proyecto
- Cumplimiento del cronograma
- Tareas abiertas/vencidas
- Avance por rubro
- Bitácoras del período

### Libro de obra
- Bitácoras aprobadas
- Evidencias promedio
- Días productivos / lluvia

### Presupuestos / planillas
- Ejecutado vs contratado
- VAE
- composición del costo

---

## Semáforos recomendados

### Verde
- dentro del plan

### Amarillo
- desviación moderada

### Rojo
- requiere acción inmediata

Ejemplos:
- Tareas vencidas > 20%: rojo
- Bitácoras aprobadas < 80%: rojo
- Avance físico por debajo del plan en más de 10 puntos: rojo

---

## KPIs que requieren datos extra para una segunda etapa
Estos conviene dejarlos para una fase posterior:

- rendimiento real por cuadrilla
- costo real diario vs costo presupuestado diario
- uso de maquinaria por horas
- costo por frente de trabajo
- desviación tiempo-costo tipo SPI/CPI formal

Estos necesitan capturas nuevas o más estructura en bitácoras y equipos.

---

## Siguiente Paso Recomendado
Implementar primero un tablero ejecutivo con 6 KPIs:

1. Avance físico acumulado
2. Monto ejecutado acumulado
3. Monto pendiente por ejecutar
4. Tareas críticas activas
5. Tareas vencidas
6. Bitácoras aprobadas del período

Después construir dashboards secundarios por:
- obra
- fiscalización
- costos

