# Distribución de KPIs por Pantalla en GEOSIS-PRO

## Objetivo
Definir exactamente:

- qué KPIs van en el `Dashboard principal`
- qué KPIs van en cada `módulo web`
- qué KPIs sí deben aparecer en `móvil`
- cómo mostrar cada KPI para que sirva a la toma de decisiones

La meta es evitar un dashboard saturado y, en cambio, construir una experiencia por niveles:

1. Resumen ejecutivo
2. Análisis por módulo
3. Operación móvil

---

## 1. Qué va en el Dashboard Principal Web

El `Dashboard principal` debe responder en menos de 10 segundos estas preguntas:

- ¿Cómo va la obra?
- ¿Qué está atrasado?
- ¿Qué está en riesgo?
- ¿Cuánto se ha ejecutado?
- ¿Qué requiere atención inmediata?

### KPIs que sí van en el Dashboard Principal

#### 1. Avance físico acumulado
- Tipo visual: tarjeta KPI + gauge o barra de progreso
- Motivo: es el principal indicador de estado real de obra

#### 2. Monto ejecutado acumulado
- Tipo visual: tarjeta KPI
- Motivo: conecta avance con impacto económico

#### 3. Monto pendiente por ejecutar
- Tipo visual: tarjeta KPI
- Motivo: muestra cuánto falta contractual y financieramente

#### 4. Tareas críticas activas
- Tipo visual: tarjeta KPI con color rojo
- Motivo: alerta inmediata

#### 5. Tareas vencidas
- Tipo visual: tarjeta KPI con semáforo
- Motivo: indica retraso operativo

#### 6. Bitácoras aprobadas del período
- Tipo visual: tarjeta KPI con porcentaje
- Motivo: mide disciplina de control diario

#### 7. Planillas por estado
- Tipo visual: gráfico dona o barras apiladas
- Estados:
  - borrador
  - presentada
  - aprobada
  - rechazada
- Motivo: muestra el flujo de cobro / fiscalización

#### 8. Proyectos activos / atrasados / terminados
- Tipo visual: tarjeta resumen o gráfico de barras
- Motivo: visión gerencial general

### KPIs que NO conviene poner en el Dashboard Principal
- composición del costo por categoría
- VAE %
- evidencias por día
- productividad por responsable
- recursos sin índice INEC
- detalles de clima
- avance por rubro individual

Esos son valiosos, pero ya son analíticos y deben vivir dentro de sus módulos.

---

## 2. Distribución por Módulo Web

## A. Dashboard Principal

### Objetivo
Resumen ejecutivo para gerencia y cliente.

### KPIs
- avance físico acumulado
- monto ejecutado acumulado
- monto pendiente por ejecutar
- tareas críticas activas
- tareas vencidas
- bitácoras aprobadas del período
- planillas por estado
- proyectos activos / atrasados / terminados

### Visualización sugerida
- primera fila:
  - 4 tarjetas KPI
- segunda fila:
  - 4 tarjetas KPI
- tercera fila:
  - gráfico de avance
  - gráfico de estados de planillas
- cuarta fila:
  - tabla de alertas críticas

---

## B. Proyectos

### Objetivo
Ver salud general de cada proyecto.

### KPIs
- estado del proyecto
- presupuesto total del proyecto
- número de presupuestos asociados
- avance físico acumulado por proyecto
- monto ejecutado acumulado
- monto pendiente
- índice de atraso del proyecto

### Visualización sugerida
- ficha superior por proyecto
- semáforo de estado
- mini resumen financiero

---

## C. Cronograma (Gantt)

### Objetivo
Tomar decisiones sobre tiempo y secuencia de ejecución.

### KPIs
- tareas abiertas
- tareas vencidas
- tareas críticas
- cumplimiento del cronograma
- porcentaje de tareas cerradas a tiempo
- índice de atraso

### Visualización sugerida
- tarjetas arriba del cronograma
- cronograma abajo
- bloque lateral de alertas:
  - tareas críticas
  - tareas próximas a vencer

### Decisiones que ayuda a tomar
- reprogramar
- mover recursos
- priorizar frentes de trabajo

---

## D. Tablero de Tareas

### Objetivo
Gestión diaria operativa.

### KPIs
- tareas abiertas por etapa
- tareas asignadas por responsable
- tareas vencidas
- tareas sin responsable
- tareas críticas

### Visualización sugerida
- tarjetas pequeñas arriba
- columnas kanban abajo
- filtros por responsable, etapa y estado

### Extra recomendado
- badge de “sin responsable”
- badge de “vencida”

---

## E. Libro de Obra

### Objetivo
Control diario, trazabilidad y auditoría.

### KPIs
- bitácoras registradas
- bitácoras aprobadas
- bitácoras pendientes
- bitácoras sin firma del contratista
- bitácoras sin firma del fiscalizador
- promedio de evidencias por día
- días con lluvia
- días productivos

### Visualización sugerida
- tarjetas KPI arriba
- línea de tiempo de bitácoras
- gráfico semanal de clima
- tabla de bitácoras observadas o pendientes

### Decisiones
- exigir formalización documental
- justificar retrasos por clima
- detectar mala calidad de reporte

---

## F. Planillas de Avance

### Objetivo
Control de ejecución valorizada y flujo de aprobación.

### KPIs
- ejecutado del período
- ejecutado acumulado
- pendiente por ejecutar
- planillas por estado
- porcentaje valorizado del contrato
- rubros más ejecutados

### Visualización sugerida
- tarjetas KPI arriba
- gráfico de evolución acumulada
- gráfico de estados
- tabla de planillas

### Decisiones
- preparar cobro
- detectar retraso en aprobación
- revisar rubros con baja ejecución

---

## G. Presupuestos

### Objetivo
Control técnico-financiero de la oferta y contrato.

### KPIs
- costo directo
- valor de indirectos
- subtotal
- IVA
- total general
- VAE %
- número de rubros
- duración contractual estimada

### Visualización sugerida
- resumen financiero superior
- dona de composición económica
- ranking de capítulos más costosos

### Decisiones
- afinar ofertas
- detectar rubros pesados
- revisar estructura de costos

---

## H. Rubros APU

### Objetivo
Análisis técnico de rubros.

### KPIs
- costo directo promedio por rubro
- rubros más costosos
- rubros sin recursos completos
- rubros sin ubicación
- rubros inactivos

### Visualización sugerida
- tabla con filtros
- ranking de rubros

---

## I. Recursos

### Objetivo
Control de insumos y sensibilidad de precios.

### KPIs
- total de recursos activos
- distribución por categoría
- recursos sin índice INEC
- recursos por ubicación
- precio promedio por categoría

### Visualización sugerida
- gráfico de pastel por categoría
- tabla con alertas de índice faltante

### Decisiones
- mejorar trazabilidad
- revisar sensibilidad al reajuste

---

## J. Mi Equipo

### Objetivo
Gestionar el personal del cliente en el portal.

### KPIs
- colaboradores activos
- colaboradores inactivos
- residentes registrados
- fiscalizadores registrados
- tareas por responsable
- productividad por responsable

### Visualización sugerida
- resumen superior
- tabla de personal
- ranking simple de actividad

### Decisiones
- balancear personal
- desactivar accesos innecesarios
- detectar responsables saturados

---

## 3. Qué sí debe ir en Móvil

La app móvil no debe ser un dashboard ejecutivo completo.

Debe ser `operativa`, rápida y enfocada en campo.

## KPIs que sí van en móvil

### Para residente
- tareas de hoy
- tareas vencidas
- tareas críticas
- avance reportado hoy
- bitácora de hoy enviada / pendiente
- número de fotos subidas hoy

### Para supervisor o fiscalizador
- bitácoras pendientes de revisar
- bitácoras aprobadas hoy
- alertas críticas del proyecto
- tareas vencidas del proyecto

### Visualización móvil sugerida
- 4 tarjetas pequeñas arriba
- lista de pendientes abajo
- botón grande de acción:
  - reportar bitácora
  - subir evidencia
  - revisar pendientes

## KPIs que NO conviene llevar a móvil
- VAE %
- composición detallada de costos
- análisis de presupuesto por capítulos
- comparativas históricas complejas
- muchos gráficos de barras o tablas grandes

Eso es mejor en web.

---

## 4. Reparto Final Recomendado

## Web Frontend

### Dashboard Principal
- avance físico acumulado
- monto ejecutado acumulado
- monto pendiente
- tareas críticas
- tareas vencidas
- bitácoras aprobadas
- planillas por estado
- proyectos por estado

### Dashboard por Módulo
- cronograma: KPIs de tiempo
- tareas: KPIs operativos
- libro de obra: KPIs documentales y clima
- planillas: KPIs de ejecución valorizada
- presupuestos: KPIs financieros
- recursos/APU: KPIs técnicos
- mi equipo: KPIs de personal

## Móvil
- solo KPIs de ejecución diaria y alertas

---

## 5. Orden de Implementación Recomendado

## Fase 1. Dashboard Ejecutivo Web
- avance físico acumulado
- monto ejecutado acumulado
- monto pendiente
- tareas críticas
- tareas vencidas
- bitácoras aprobadas
- planillas por estado

## Fase 2. Módulos Operativos Web
- cronograma
- tablero de tareas
- libro de obra
- planillas

## Fase 3. Costos y Técnica
- presupuestos
- recursos
- APU
- índices INEC

## Fase 4. Móvil
- mini dashboard de campo
- pendientes del día
- alertas

---

## 6. Recomendación Final

No poner todos los KPIs en un solo dashboard.

La mejor estructura es:

1. `Dashboard principal`
   Resumen ejecutivo para decidir rápido.

2. `Dashboards por módulo`
   Análisis más profundo según tema.

3. `Móvil`
   Solo operación y alertas de campo.

Esta estructura evita saturación, mejora la comprensión del cliente y hace que cada pantalla tenga sentido.

