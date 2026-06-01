# Plan de Implementacion y Mejora GEOSIS-PRO

## Objetivo

Convertir GEOSIS-PRO en una plataforma profesional, segura, mantenible y facil de usar para clientes reales, sin romper lo que ya esta funcionando.

La estrategia es:

1. Corregir errores criticos.
2. Proteger seguridad y permisos.
3. Ordenar fiscalizacion, planes, catalogos y portal.
4. Mejorar experiencia del cliente.
5. Profesionalizar reportes, trazabilidad, automatizaciones y soporte.

## Principio De Trabajo

No se debe cambiar todo de golpe. Cada fase debe probarse antes de pasar a la siguiente.

Antes de cada fase:

- Hacer respaldo de base de datos.
- Revisar `git status`.
- Crear commit o punto de restauracion.
- Probar flujos principales.
- Validar que portal, app movil y backend sigan funcionando.

## Flujos Que Deben Seguir Funcionando

- Login al portal.
- Dashboard.
- Gestion de equipo.
- Recursos.
- APUs / rubros.
- Indices INEC.
- Proyectos.
- Presupuestos.
- Importacion Excel.
- Gantt / cronograma.
- Tablero de tareas.
- Bitacoras / libro de obra.
- Planillas de avance.
- Avaluos.
- Hotmart / suscripciones.
- Reportes PDF.
- Exportacion MS Project.

## Fase 0: Respaldo y Diagnostico Inicial

### Tareas

- Crear respaldo de base de datos.
- Guardar estado actual funcional del codigo.
- Documentar modulos instalados en Odoo.
- Verificar que version de cada modulo esta activa.
- Revisar si `geosis_fiscalizacion` esta instalado en la base real.
- Revisar si existen datos creados en planillas de avance.
- Probar instalacion/actualizacion de modulos en un entorno de prueba.

### Pruebas Minimas

- Entrar al portal.
- Crear recurso.
- Crear APU.
- Crear proyecto.
- Crear presupuesto.
- Importar Excel.
- Generar cronograma.
- Registrar bitacora.
- Crear planilla.
- Crear avaluo.
- Verificar suscripcion Hotmart.

## Fase 1: Correcciones Criticas

### 1. Plantillas Publicas De Website

Problema:

- `geosis_website/controllers/main.py` renderiza paginas publicas como `/plataforma` y `/flujo`.
- Las plantillas existen en `views/geosis_website_templates.xml`.
- Ese archivo no esta cargado en `geosis_website/__manifest__.py`.

Accion:

- Agregar `views/geosis_website_templates.xml` al manifest.

Resultado esperado:

- `/plataforma` y `/flujo` no deben fallar por external ID inexistente.

### 2. Assets Publicos De Website

Problema:

- Existe `static/src/scss/geosis_website.scss`.
- En el manifest solo aparece cargado `geosis_portal.scss`.

Accion:

- Revisar si `geosis_website.scss` corresponde a la web publica.
- Si corresponde, cargarlo en `web.assets_frontend`.

Resultado esperado:

- Web publica y portal privado deben tener estilos correctamente cargados.

### 3. Error `models.UserError`

Problema:

- En `geosis_presupuesto/models/geosis_budget.py` se usa `models.UserError`.
- Eso es incorrecto.

Accion:

- Importar `UserError` desde `odoo.exceptions`.
- Usar `raise UserError(...)`.

Resultado esperado:

- La formula polinomica debe mostrar error controlado cuando no existan costos calculables.

### 4. Grupo Perito Inconsistente

Problema:

- En codigo aparece referencia a `geosis_base.group_geosis_perito`.
- El grupo real parece ser `geosis_base.group_geosis_portal_appraiser`.

Accion:

- Unificar el rol de perito valuador usando `group_geosis_portal_appraiser`.
- Eliminar o corregir referencias a `group_geosis_perito` si no existe.

Resultado esperado:

- Roles consistentes en portal, app movil y backend.

### 5. Errores Silenciosos

Problema:

- Hay varios `except Exception: pass`.
- Esto oculta errores reales.

Accion:

- Cambiar por logs controlados.
- Mostrar mensajes claros cuando aplique.

Resultado esperado:

- Los errores se pueden diagnosticar sin afectar al usuario con pantallas tecnicas.

## Fase 2: Fiscalizacion y Supervisor

### Situacion Actual

`geosis_fiscalizacion` si sirve para el usuario supervisor/fiscalizador. No debe eliminarse como modulo funcional.

El problema es que `geosis_fiscalizacion` y `geosis_proyectos` declaran el mismo modelo:

- `geosis.estimation`
- `geosis.estimation.line`

Eso puede causar conflicto porque ambos usan `_name = 'geosis.estimation'` con campos diferentes.

### Decision

- `geosis_proyectos` debe ser el dueno del modelo base de planillas.
- `geosis_fiscalizacion` debe convertirse en extension usando `_inherit = 'geosis.estimation'`.

### Acciones

- No eliminar `geosis_fiscalizacion`.
- Cambiar sus modelos duplicados para que extiendan el modelo base.
- Agregar campos propios de fiscalizacion:
  - fiscalizador/supervisor;
  - observaciones del supervisor;
  - fecha de revision;
  - firma del fiscalizador;
  - estado de revision;
  - motivo de rechazo.
- Crear vistas especificas para supervisor.
- Revisar permisos del supervisor.
- Probar planillas existentes.

### Flujo Esperado

1. Residente registra avance o bitacora.
2. Se genera o actualiza planilla.
3. Supervisor revisa.
4. Supervisor aprueba o rechaza.
5. Se guarda trazabilidad.

## Fase 3: Seguridad y Permisos

### Problema General

El portal usa mucho `sudo()`. No necesariamente esta mal, pero requiere validaciones estrictas.

### Acciones

- Auditar permisos de:
  - APUs;
  - recursos;
  - presupuestos;
  - proyectos;
  - planillas;
  - bitacoras;
  - avaluos;
  - fotos;
  - comparables;
  - indices INEC.
- Quitar permisos completos innecesarios para:
  - `base.group_portal`;
  - `base.group_user`.
- Usar grupos GEOSIS especificos:
  - administrador GEOSIS;
  - administrador cliente;
  - residente;
  - fiscalizador/supervisor;
  - perito valuador;
  - consulta.

### Helpers Seguros

Crear o reforzar:

- `_get_accessible_project`
- `_get_accessible_budget`
- `_get_accessible_apu`
- `_get_accessible_resource`
- `_get_accessible_estimation`
- `_get_accessible_avaluo`
- `_get_accessible_bitacora`

Cada helper debe validar:

- cliente;
- empresa;
- rol;
- ubicacion si aplica;
- plan si aplica;
- estado si aplica.

### Borrado

Evitar borrado directo por clientes.

Usar:

- archivar;
- cancelar;
- desactivar.

Aplicar especialmente en:

- proyectos;
- presupuestos;
- APUs;
- recursos;
- planillas;
- bitacoras;
- avaluos.

## Fase 4: Planes y Hotmart

### Lo Que Ya Existe

Los planes ya estan implementados en `geosis_hotmart`.

Planes:

- `professional` = Plan Profesional.
- `pyme` = Plan Constructor.
- `enterprise` = Plan Enterprise.

Limites actuales:

| Plan | Proyectos activos | Residentes | Premium |
| --- | ---: | ---: | --- |
| Profesional | 2 | 1 | No |
| Constructor/Pyme | 10 | 5 | Si |
| Enterprise | Ilimitado | Ilimitado | Si |

Funciones premium:

- Gantt.
- CPM / ruta critica.
- Formula polinomica.
- KPIs avanzados si aplica.

### Acciones

- No rehacer los planes.
- Mantener limites actuales.
- Documentar que `pyme` equivale comercialmente a `Constructor`.
- Crear panel "Mi Plan".
- Mostrar:
  - plan actual;
  - estado de suscripcion;
  - proyectos usados/permitidos;
  - residentes usados/permitidos;
  - funciones incluidas;
  - boton actualizar plan.
- Revisar si cancelacion de Hotmart debe:
  - desactivar usuario;
  - o dejar modo solo lectura.
- Registrar historial de eventos Hotmart.
- Ocultar o bloquear elegantemente botones premium no disponibles.

### Avaluos

Decision:

- Avaluos quedan como plus gratuito.
- No se bloquean por plan.
- Se controlan por rol.

Roles con acceso:

- administrador GEOSIS;
- administrador cliente;
- perito valuador.

## Fase 5: Catalogos Profesionales

### Situacion Actual

La ubicacion ya existe y esta bien. Sirve para precios regionales:

- Global;
- Cuenca;
- Quito;
- Guayaquil;
- Loja;
- otras ciudades.

Pero ubicacion no reemplaza propiedad ni permisos.

### Objetivo

Separar claramente:

- catalogo maestro GEOSIS;
- catalogo del cliente;
- catalogo del proyecto/presupuesto.

### Acciones

- Mantener `location`.
- Agregar alcance:
  - `global`;
  - `cliente`;
  - `proyecto`.
- Agregar propiedad:
  - `company_id`;
  - `partner_id` cuando aplique.
- Permitir copiar recurso/APU maestro a catalogo del cliente.
- Evitar que el cliente edite directamente el catalogo maestro.
- Mostrar al cliente:
  - recursos globales;
  - recursos de su ubicacion;
  - recursos propios.
- Congelar precios en presupuestos aprobados.
- Corregir logica donde `geosis_recursos` usa `geosis.apu.line` sin ser dueno de APU.

### Resultado Esperado

El cliente puede elegir rapido, pero no mezcla ni dana informacion de otros clientes.

## Fase 6: Validaciones De Negocio

Agregar validaciones para:

- No aprobar presupuesto sin lineas.
- No aprobar planilla sin lineas.
- Cantidades no negativas.
- Precios no negativos.
- VAE entre 0 y 100.
- Fecha fin mayor o igual a fecha inicio.
- Avance acumulado no mayor a cantidad contratada.
- Presupuesto aprobado no editable sin volver a borrador.
- Vida util de avaluo mayor a 0.
- Edad de construccion no negativa.
- Coordenadas validas.
- Recursos con unidad obligatoria.
- Duplicados controlados por ubicacion/cliente.
- Planilla no aprobable si no tiene supervisor cuando aplique.
- Bitacora no aprobable sin revision cuando aplique.

## Fase 7: Importacion Excel

### Situacion Actual

La importacion Excel es una funcion clave y debe mantenerse.

### Acciones

- Agregar previsualizacion antes de crear datos.
- Mostrar:
  - proyecto detectado;
  - presupuesto detectado;
  - APUs detectados;
  - recursos detectados;
  - duplicados;
  - errores por fila;
  - advertencias.
- Permitir confirmar o cancelar.
- Guardar log de importacion.
- Mostrar resumen final.
- Evitar creacion masiva si el archivo esta mal leido.

### Resultado Esperado

El cliente entiende que se va a crear antes de confirmar.

## Fase 8: GEOSIS Website

### Separacion De Areas

Separar claramente:

Web publica:

- inicio;
- contacto;
- servicios;
- nosotros;
- planes;
- pagina comercial;
- contacto/lead.

Portal privado:

- dashboard;
- proyectos;
- presupuestos;
- recursos;
- APUs;
- INEC;
- Gantt;
- tareas;
- bitacoras;
- planillas;
- avaluos;
- equipo;
- mi plan.

### Acciones

- Corregir manifest de `geosis_website`.
- Cargar templates publicos.
- Revisar assets publicos y del portal.
- Mejorar pagina de planes.
- Alinear nombres:
  - `pyme` = Constructor.
- Mantener avaluos como plus gratuito.
- Agregar panel "Mi Plan".
- Mejorar responsive.
- Mejorar navegacion.
- Mejorar mensajes de error.
- Profesionalizar reportes y paginas publicas.

## Fase 9: Portal y Refactor De Codigo

### Situacion Actual

`geosis_website/controllers/portal.py` concentra demasiadas responsabilidades.

### Accion

Dividir progresivamente en:

- `portal_dashboard.py`
- `portal_projects.py`
- `portal_budgets.py`
- `portal_apu.py`
- `portal_resources.py`
- `portal_inec.py`
- `portal_bitacoras.py`
- `portal_estimations.py`
- `portal_avaluos.py`
- `portal_team.py`
- `portal_subscription.py`

### Regla

Primero estabilizar. Luego dividir. El refactor debe mover codigo sin cambiar comportamiento.

## Fase 10: Experiencia Del Cliente

### Objetivo

Que GEOSIS-PRO no se sienta como Odoo tecnico, sino como una plataforma guiada.

### Flujo Ideal

1. Crear empresa.
2. Crear equipo.
3. Seleccionar ubicacion.
4. Crear proyecto o importar Excel.
5. Elegir plantilla/APUs.
6. Ajustar cantidades y precios.
7. Generar presupuesto.
8. Aprobar presupuesto.
9. Generar cronograma.
10. Registrar bitacoras.
11. Crear planillas de avance.
12. Solicitar/gestionar avaluos.
13. Exportar reportes.

### Mejoras UX

- Dashboard por rol.
- Estados claros.
- Botones principales visibles.
- Menos textos tecnicos.
- Asistentes paso a paso.
- Alertas:
  - tareas vencidas;
  - presupuesto sin aprobar;
  - planillas pendientes;
  - bitacoras por revisar;
  - limite de plan alcanzado;
  - suscripcion vencida.
- Ocultar botones premium o mostrar aviso claro.

## Fase 11: Reportes Profesionales

### Reportes A Mejorar

- PDF de presupuesto.
- PDF de APU.
- PDF de bitacora.
- PDF de planilla.
- PDF de avaluo.
- Informe ejecutivo de proyecto.
- Exportacion Excel.
- Exportacion MS Project.

### Caracteristicas

- Portada con marca del cliente.
- Logo.
- Datos de proyecto.
- Firmas.
- Sello digital si aplica.
- Evidencia fotografica.
- Historial de aprobaciones.
- Resumen ejecutivo.
- Totales claros.
- Secciones bien ordenadas.

## Fase 12: Trazabilidad y Auditoria

### Modelos Clave

Agregar historial a:

- proyectos;
- presupuestos;
- APUs;
- recursos;
- planillas;
- bitacoras;
- avaluos;
- cambios de plan/suscripcion;
- importaciones Excel.

### Registrar

- creado por;
- modificado por;
- aprobado por;
- fecha de aprobacion;
- estado anterior;
- estado nuevo;
- observaciones;
- firmas;
- evidencias;
- cambios de precio.

## Fase 13: Automatizaciones

### Automatizaciones Recomendadas

- Notificar al supervisor cuando residente sube bitacora.
- Notificar al cliente cuando se aprueba presupuesto.
- Recordar tareas vencidas.
- Alertar avance atrasado.
- Alertar planillas pendientes.
- Alertar limite de plan cercano.
- Enviar reportes automaticamente.
- Generar planillas sugeridas desde bitacoras.
- Avisar vencimiento o cancelacion de suscripcion.

## Fase 14: App Movil

### Mantener y Fortalecer

La app movil aporta valor en campo.

### Analizar

- Roles y permisos.
- Proyectos visibles.
- Bitacoras.
- Avaluos.
- Fotos.
- Firmas.
- GPS.
- Sincronizacion.
- Modo offline.
- Compresion de imagenes.
- Manejo de errores de conexion.
- Mensajes claros si no sincroniza.

### Resultado Esperado

El residente/perito puede trabajar en campo sin depender de un flujo tecnico.

## Fase 15: Rendimiento y Escalabilidad

### Acciones

- Optimizar busquedas.
- Revisar paginacion.
- Agregar indices en campos clave:
  - ubicacion;
  - codigo;
  - cliente;
  - compania;
  - estado;
  - fechas.
- Evitar calculos pesados en dashboard.
- Optimizar conteos globales.
- Revisar cargas de imagenes/fotos.
- Revisar importaciones grandes.
- Optimizar catalogos grandes de recursos/APUs.

## Fase 16: Legal, Soporte y Operacion

### Legal

- Terminos y condiciones.
- Politica de privacidad.
- Manejo de datos de clientes.
- Responsabilidad sobre avaluos.
- Evidencia legal de bitacoras.
- Historial de aprobaciones.

### Soporte

- Manual de usuario.
- Manual administrador.
- Guia de importacion Excel.
- Videos cortos.
- Boton de ayuda.
- Centro de soporte.
- Logs para diagnostico.

### Operacion

- Backups automaticos.
- Revision de errores.
- Monitoreo de webhooks Hotmart.
- Control de clientes activos.
- Control de suscripciones.

## Fase 17: Pruebas

### Pruebas Tecnicas

- Instalacion limpia de modulos.
- Actualizacion de modulos.
- Pruebas de XML.
- Pruebas de Python.
- Pruebas de seguridad por rol.
- Pruebas de permisos por cliente.

### Pruebas Funcionales

- Crear usuario por Hotmart.
- Aplicar limites de plan.
- Crear equipo.
- Limitar residentes.
- Crear proyecto.
- Crear presupuesto.
- Importar Excel.
- Aprobar presupuesto.
- Generar cronograma.
- Gantt bloqueado en Profesional.
- Formula bloqueada en Profesional.
- Avaluos disponibles como plus.
- Subir bitacora.
- Aprobar bitacora.
- Generar planilla.
- Revisar planilla como fiscalizador.
- Crear avaluo.
- Subir fotos.
- Exportar reportes.

## Orden Seguro De Implementacion

1. Respaldo y diagnostico.
2. Correcciones criticas.
3. Fiscalizacion como extension.
4. Seguridad y permisos.
5. Planes / Hotmart / panel Mi Plan.
6. Catalogos por ubicacion, cliente y proyecto.
7. Validaciones de negocio.
8. Importacion Excel con previsualizacion.
9. GEOSIS Website.
10. Flujo guiado del cliente.
11. Reportes profesionales.
12. Trazabilidad.
13. Automatizaciones.
14. App movil.
15. Rendimiento.
16. Legal, soporte y operacion.
17. Pruebas completas.

## Arquitectura Objetivo

- `geosis_base`: seguridad base, roles, menus e indices comunes.
- `geosis_recursos`: recursos regionales y catalogo base.
- `geosis_apu`: rubros/APUs.
- `geosis_presupuesto`: presupuestos y formula polinomica.
- `geosis_proyectos`: proyectos y planillas base.
- `geosis_fiscalizacion`: supervisor/fiscalizador como extension.
- `geosis_mobile`: app movil, campo y bitacoras.
- `geosis_avaluos`: avaluos gratuitos como plus.
- `geosis_website`: web publica y portal cliente.
- `geosis_hotmart`: suscripciones, limites y planes.

## Resultado Esperado

GEOSIS-PRO debe quedar como una plataforma donde el cliente puede:

1. Comprar un plan.
2. Entrar al portal.
3. Crear su equipo.
4. Seleccionar ubicacion.
5. Crear o importar un proyecto.
6. Usar recursos y APUs.
7. Generar presupuesto.
8. Aprobar presupuesto.
9. Generar cronograma.
10. Registrar bitacoras.
11. Revisar con supervisor.
12. Generar planillas.
13. Gestionar avaluos gratis como plus.
14. Exportar reportes profesionales.
15. Ver uso de su plan.
16. Trabajar con seguridad por rol y cliente.

## Prioridad Practica

Si se quiere empezar sin riesgo, el primer paquete debe ser:

1. Corregir manifest de `geosis_website`.
2. Corregir `models.UserError`.
3. Corregir referencia del grupo perito.
4. Revisar `geosis_fiscalizacion` como extension.
5. Reforzar permisos criticos.
6. Crear panel "Mi Plan".
7. Probar todos los flujos actuales.

