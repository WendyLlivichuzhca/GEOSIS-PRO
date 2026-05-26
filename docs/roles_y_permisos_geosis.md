# Roles y permisos GEOSIS-PRO

Este documento define los roles funcionales del sistema GEOSIS-PRO para separar claramente lo que puede hacer cada usuario en el portal web, backend de Odoo y app movil.

## Principio general

Los clientes finales y su personal no deben usar el backend tecnico de Odoo. Deben trabajar desde el portal GEOSIS o desde la app movil.

El backend de Odoo queda reservado para administracion tecnica, soporte, configuracion, auditoria y mantenimiento del sistema.

## Roles definidos

### 1. Superadministrador GEOSIS

Usuario interno de la empresa que opera GEOSIS-PRO.

Debe poder:
- Acceder al backend completo de Odoo.
- Configurar modulos, grupos, correo, plantillas y companias.
- Ver todas las empresas/clientes.
- Dar soporte tecnico.
- Auditar datos.
- Corregir incidencias operativas.

No representa a un cliente final.

### 2. Administrador cliente

Usuario principal de una empresa cliente, por ejemplo el gerente o administrador de la constructora.

Debe poder:
- Entrar al portal web GEOSIS.
- Ver dashboard completo de su propia empresa.
- Crear y gestionar su equipo.
- Crear y gestionar proyectos.
- Crear, importar y editar presupuestos.
- Gestionar rubros APU, recursos e indices.
- Generar cronograma.
- Ver y gestionar tablero de tareas.
- Asignar tareas a residentes o fiscalizadores.
- Ver libro de obra.
- Crear, revisar y controlar planillas de avance.
- Ver KPIs completos de decision.

No debe poder:
- Ver datos de otras empresas.
- Entrar a configuracion tecnica de Odoo.
- Ver Apps, Ajustes, Discusiones o menus tecnicos.

### 3. Residente de obra

Personal operativo de campo. Su trabajo principal es ejecutar y reportar avance.

Debe poder:
- Entrar a la app movil con su correo y contrasena.
- Ver solo proyectos/tareas asignadas.
- Registrar libro de obra.
- Subir fotos/evidencias.
- Reportar avance diario por tarea.
- Consultar su tablero operativo.
- Ver cronograma relacionado con sus tareas.

En portal web, si entra desde navegador, debe ver solo:
- Dashboard operativo limitado.
- Cronograma.
- Tablero de tareas.
- Libro de obra.

No debe poder:
- Crear presupuestos.
- Editar rubros APU.
- Editar recursos o indices.
- Importar Excel.
- Crear o eliminar proyectos.
- Crear usuarios en Mi Equipo.
- Aprobar planillas.
- Ver informacion de otras empresas.
- Entrar al backend de Odoo.

### 4. Fiscalizador / Supervisor

Usuario encargado de revisar, validar y aprobar avances.

Debe poder:
- Entrar al portal web GEOSIS.
- Entrar a la app movil si se requiere revision en campo.
- Ver proyectos asignados o de su empresa.
- Ver cronograma y tablero de tareas.
- Revisar libro de obra.
- Aprobar o rechazar bitacoras.
- Ver evidencias/fotos.
- Revisar planillas de avance.
- Aprobar o rechazar planillas si el flujo del cliente lo permite.
- Ver KPIs de control y alertas.

No debe poder:
- Crear usuarios en Mi Equipo.
- Editar presupuesto base.
- Editar catalogos maestros como recursos o indices.
- Importar Excel.
- Crear/eliminar proyectos.
- Entrar al backend tecnico de Odoo.

### 5. Consulta / Cliente auditor

Usuario de solo lectura, por ejemplo propietario, auditor externo o cliente que solo monitorea.

Debe poder:
- Entrar al portal web GEOSIS.
- Ver dashboard.
- Ver proyectos.
- Ver presupuesto en lectura.
- Ver cronograma.
- Ver tablero de tareas.
- Ver libro de obra en lectura.
- Ver planillas en lectura.
- Ver KPIs.

No debe poder:
- Crear, editar, aprobar o eliminar informacion.
- Gestionar equipo.
- Asignar tareas.
- Reportar avances.
- Entrar al backend tecnico de Odoo.

## Matriz de permisos por modulo

| Modulo | Superadmin GEOSIS | Admin cliente | Residente | Fiscalizador | Consulta |
| --- | --- | --- | --- | --- | --- |
| Backend Odoo | Total | No | No | No | No |
| Dashboard portal | Total | Total empresa | Limitado | Control | Lectura |
| Mi Equipo | Total | Crear/activar/desactivar | No | No | No |
| Rubros APU | Total | Crear/editar | No | Lectura opcional | Lectura |
| Recursos | Total | Crear/editar | No | Lectura opcional | Lectura |
| Indices INEC | Total | Crear/editar | No | Lectura opcional | Lectura |
| Mapa bases de datos | Total | Total empresa | No | Lectura opcional | Lectura |
| Proyectos | Total | Crear/editar | Ver asignados | Ver asignados/empresa | Lectura |
| Presupuestos | Total | Crear/editar/importar | No | Lectura | Lectura |
| Importar Excel | Total | Si | No | No | No |
| Cronograma | Total | Gestionar | Ver asignado | Ver/controlar | Lectura |
| Tablero de tareas | Total | Gestionar/asignar | Actualizar sus tareas | Revisar/controlar | Lectura |
| Crear etapas | Total | Si | No | No o solo si se autoriza | No |
| Asignar responsables | Total | Si | No | Opcional | No |
| Cambiar estado tarea | Total | Si | Solo sus tareas | Si para revision | No |
| Libro de Obra | Total | Ver/controlar | Crear reporte | Revisar/aprobar | Lectura |
| Fotos/evidencias | Total | Ver | Subir | Ver/aprobar | Ver |
| Planillas de avance | Total | Crear/revisar | No | Revisar/aprobar | Lectura |
| App movil | Soporte | Opcional | Principal | Opcional | No |

## Reglas de acceso clave

### Aislamiento por empresa

Todo usuario cliente debe quedar vinculado a su `commercial_partner_id`.

Regla obligatoria:
- Una empresa solo ve su propia informacion.
- Un colaborador solo pertenece al equipo de su empresa.
- Ningun cliente ve personal, proyectos, presupuestos, bitacoras o planillas de otra empresa.

### Acceso por asignacion

Para residentes, no basta con pertenecer a la empresa. Deben ver principalmente lo asignado a ellos.

Regla recomendada:
- Residente ve tareas donde `user_id` o responsable sea su usuario.
- Si una tarea no tiene responsable, el administrador debe asignarla antes de que aparezca al residente.

### Portal vs backend

Los roles cliente deben quedar como `base.group_portal`, no como `base.group_user`.

Solo el equipo tecnico GEOSIS debe tener `base.group_user`.

## Pruebas necesarias

### Prueba 1: Residente

1. Crear un colaborador con rol Residente de Obra desde Mi Equipo.
2. Confirmar que recibe correo y crea contrasena.
3. Iniciar sesion con ese usuario.
4. Verificar que no entra a Discuss ni backend.
5. Verificar que entra al portal GEOSIS.
6. Verificar que no ve Mi Equipo, Rubros, Recursos, Indices, Presupuestos ni Importar Excel.
7. Verificar que puede ver Cronograma, Tablero y Libro de Obra.
8. Verificar que en app movil puede iniciar sesion.
9. Verificar que solo aparecen proyectos/tareas asignadas.

### Prueba 2: Fiscalizador

1. Crear un colaborador con rol Fiscalizador / Supervisor.
2. Confirmar que no entra al backend.
3. Verificar que ve cronograma, tablero, libro de obra y planillas.
4. Verificar que puede revisar/aprobar segun el flujo definido.
5. Verificar que no puede crear equipo, presupuestos ni importar Excel.

### Prueba 3: Administrador cliente

1. Iniciar sesion como usuario principal de la empresa.
2. Verificar acceso completo al portal de su empresa.
3. Verificar Mi Equipo.
4. Verificar creacion de colaborador.
5. Verificar que no puede ver datos de otra empresa.

### Prueba 4: Acceso directo por URL

Con un residente, intentar abrir manualmente:
- `/web`
- `/my/team`
- `/my/budgets`
- `/my/import-excel`
- `/my/resources`
- `/my/inec-indices`

Resultado esperado:
- Backend bloqueado.
- Rutas administrativas redirigidas o denegadas.

## Implementacion pendiente

1. Crear helper central de permisos en el controlador portal.
2. Proteger rutas por rol, no solo ocultar menus.
3. Ajustar API movil para filtrar por usuario asignado.
4. Agregar rol Consulta si se decide vender acceso de auditoria.
5. Agregar pruebas manuales o automatizadas de permisos.
