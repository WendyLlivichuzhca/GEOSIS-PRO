# GEOSIS-PRO - Fase 0: Diagnostico Inicial

Fecha: 2026-06-01

Objetivo: dejar una linea base del sistema antes de modificar modulos funcionales. Esta fase sirve para reducir riesgo, saber que existe, detectar configuraciones delicadas y definir las pruebas minimas que deben repetirse antes y despues de cada mejora.

## 1. Estado del repositorio

- Rama actual: `main`.
- Estado Git al iniciar la revision: limpio, sin cambios pendientes visibles.
- Archivo de plan general existente: `docs/plan_implementacion_geosis_pro.md`.
- Confirmacion visual del usuario: Odoo reconoce 11 modulos GEOSIS cargados en Apps, incluyendo `geosis_fiscalizacion`.
- Confirmacion del usuario: todos los modulos GEOSIS estan instalados y actualizados en Odoo.
- Estado comercial: el producto esta en produccion tecnica, pero aun no esta vendido a clientes finales.
- Criterio de riesgo: al no tener clientes finales activos, se puede avanzar con correcciones de bajo riesgo; aun asi, se debe conservar respaldo antes de cambios de modelos, permisos o datos.

## 2. Inventario de modulos Odoo

Se detectaron 13 addons en `odoo_addons`:

| Modulo | Dependencias principales | Observacion |
| --- | --- | --- |
| `geosis_base` | `base` | Base de roles, grupos y modelos comunes. |
| `geosis_recursos` | `base`, `uom`, `geosis_base` | Catalogo de recursos, precios, categorias y ubicacion. |
| `geosis_apu` | `base`, `geosis_base`, `geosis_recursos` | Rubros/APUs y lineas de composicion. |
| `geosis_presupuesto` | `base`, `geosis_base`, `geosis_apu` | Presupuestos y partidas. |
| `geosis_proyectos` | `base`, `geosis_base`, `geosis_presupuesto`, `project`, `project_timeline` | Proyectos, tareas, cronograma y base de planillas. |
| `geosis_fiscalizacion` | `base`, `geosis_presupuesto` | Debe mantenerse para supervisor/fiscalizador, pero requiere revisar duplicacion de modelos. |
| `geosis_website` | `website`, `portal`, catalogos, presupuestos, proyectos, importacion, avaluos | Portal/web del cliente y sitio GEOSIS. |
| `geosis_mobile` | `base`, `geosis_base`, `geosis_proyectos` | API para app movil, bitacoras y reportes. |
| `geosis_avaluos` | `geosis_base`, `geosis_apu`, `geosis_mobile` | Avaluos como plus gratis; no debe bloquearse por plan. |
| `geosis_hotmart` | `base`, `geosis_base`, proyectos, presupuestos, website | Planes, limites comerciales y suscripcion. |
| `geosis_import_excel` | `base`, `uom`, catalogos, APU, presupuestos, proyectos | Importacion de archivos Excel. |
| `web_timeline` | `web` | Vista timeline base. |
| `project_timeline` | `project`, `web_timeline` | Timeline aplicado a proyectos. |

## 3. Validaciones tecnicas ejecutadas

| Validacion | Resultado |
| --- | --- |
| Revision de manifests y archivos declarados en `data` | OK, no faltan archivos declarados. |
| Compilacion Python con `python -m compileall -q odoo_addons` | OK. |
| Parseo XML de archivos en `odoo_addons` | OK, `XML_BAD_COUNT 0`. |
| Revision inicial de scripts de prueba | Existen scripts para avaluos y webhook Hotmart. |

Resultado: la base del codigo no muestra errores sintacticos inmediatos en Python/XML. Esto no reemplaza pruebas reales en Odoo, instalacion de modulos ni pruebas funcionales.

## 4. Configuracion y base de datos

Hallazgos:

- Existe configuracion PHP en `config/database.php`.
- Esa configuracion corresponde a una parte legacy/antigua que actualmente no se esta utilizando como producto principal.
- Como ya no se usa PHP para el flujo actual, no se priorizara esa base en las fases funcionales de GEOSIS-PRO.
- Aunque sea legacy, contiene credenciales en texto claro. No se debe eliminar sin confirmar despliegue, pero despues conviene retirarlo del repositorio activo o moverlo a variables de entorno si algun dia se reutiliza.
- No se encontro un archivo de configuracion Odoo tipo `.conf` dentro del repositorio.
- La app Flutter referencia una URL productiva y base Odoo en `geosis_app/lib/services/odoo_service.dart`.
- No se encontraron herramientas `mysql`, `mysqldump`, `psql` o `pg_dump` disponibles en PATH durante esta revision.

Pendiente obligatorio antes de cambios de alto impacto:

- Confirmar cual es la base de datos real de Odoo en produccion/staging.
- Sacar backup de Odoo antes de modificar modelos, seguridad, vistas o datos.
- No se requiere backup funcional de PHP si se confirma que ya no esta en uso.
- Confirmar si existe ambiente de pruebas/staging separado de produccion.

## 5. Observaciones criticas acumuladas

1. `geosis_fiscalizacion` no debe eliminarse. Debe servir para supervisor/fiscalizador.
2. La base de planillas debe vivir en `geosis_proyectos`; `geosis_fiscalizacion` debe extenderla con `_inherit`, no duplicar modelos como `geosis.estimation`.
3. `geosis_website` tiene templates publicos para `/plataforma` y `/flujo`, pero el manifest debe revisarse para asegurar que se carguen.
4. Revisar assets publicos de `geosis_website`, especialmente si `geosis_website.scss` debe entrar en bundles.
5. `geosis_presupuesto` debe corregir el uso de `UserError` para evitar errores en tiempo de ejecucion.
6. `geosis_recursos` no deberia depender directamente de `geosis.apu.line`; hay riesgo de acoplamiento circular funcional.
7. `geosis_mobile` debe alinear el grupo de perito/appraiser con el grupo real definido en `geosis_base`.
8. El portal usa mucho `sudo()`; hay que agregar helpers de acceso para evitar que un cliente vea datos de otro.
9. Los permisos de portal sobre APU/APU lines parecen demasiado amplios y deben endurecerse.
10. Los permisos de bitacoras moviles para usuarios internos deben revisarse por rol.
11. La ubicacion en recursos si tiene sentido: sirve para precios regionales y seleccion por zona. Debe reforzarse con reglas de alcance.
12. Catalogos deben separarse por alcance: maestro GEOSIS, cliente/empresa y proyecto/presupuesto.
13. Los planes ya existen en codigo: Profesional, Constructor/Pyme y Enterprise.
14. Avaluos van como plus gratis, no como funcion premium bloqueada por plan.
15. Falta panel claro de `Mi Plan`, estado de suscripcion y limites visibles para el cliente.
16. Debe definirse comportamiento por falta de pago: lectura, bloqueo parcial o suspension.
17. Se requiere auditoria de cambios: quien creo, edito, aprobo, elimino o importo informacion.
18. Deben evitarse borrados peligrosos; preferir archivar, cancelar o desactivar.
19. Reportes PDF/Excel deben verse profesionales y llevar marca del cliente.
20. El sitio `geosis_website` tambien entra en el plan: landing, planes, contacto, servicios, textos comerciales, conversion y coherencia visual.

## 6. Checklist funcional base

Estas pruebas deben ejecutarse manualmente en ambiente de pruebas antes de Fase 1 y repetirse despues de cada bloque importante:

- Instalar/actualizar modulos GEOSIS desde cero en una base limpia.
- Crear empresa/cliente.
- Crear usuarios por rol: administrador, constructor, residente, supervisor/fiscalizador, perito.
- Validar login portal y separacion por cliente.
- Crear recurso con ubicacion.
- Crear rubro APU usando recursos.
- Crear presupuesto desde APUs.
- Editar precio de recurso y validar impacto esperado.
- Importar Excel de presupuesto/APU.
- Crear proyecto desde presupuesto.
- Generar cronograma/Gantt.
- Crear tareas y revisar ruta critica si el plan lo permite.
- Registrar bitacora/libro de obra.
- Revisar flujo de supervisor/fiscalizador.
- Generar planilla de avance.
- Crear avaluo.
- Exportar PDF de presupuesto.
- Exportar PDF de APU.
- Exportar reportes de avance/bitacora/avaluo.
- Validar plan Profesional: maximo 2 proyectos activos y 1 residente.
- Validar plan Constructor/Pyme: maximo 10 proyectos activos y 5 residentes.
- Validar plan Enterprise: sin limites practicos.
- Validar que Avaluos funcione como plus gratis.
- Validar bloqueo o restriccion cuando la suscripcion este inactiva.
- Probar app movil: login, proyectos, reportes, fotos, bitacora y avaluos.
- Validar que un cliente no pueda ver datos de otro cliente.

## 7. Riesgos antes de implementar

| Riesgo | Impacto | Accion recomendada |
| --- | --- | --- |
| No hay backup confirmado | Alto | Hacer backup antes de tocar modelos/datos. |
| Credenciales PHP legacy en codigo | Medio | Confirmar que no se usa, luego retirar o aislar fuera del producto activo. |
| Falta ambiente staging confirmado | Alto | Probar primero fuera de produccion. |
| Duplicacion de modelos de planillas | Alto | Corregir con migracion cuidadosa, sin borrar datos. |
| Permisos amplios en portal/API | Alto | Revisar access CSV, record rules y controladores. |
| Uso excesivo de `sudo()` | Alto | Encapsular validaciones de propiedad/acceso. |
| URL productiva hardcodeada en Flutter | Medio | Separar config dev/staging/prod. |
| Reportes sin estandar profesional | Medio | Crear plantillas con marca, firma y trazabilidad. |

## 8. Criterio para pasar a Fase 1

Se puede pasar a Fase 1 cuando:

- Exista backup confirmado o un punto claro de restauracion.
- Se sepa si se trabajara en staging o produccion. En este caso, el usuario confirma produccion tecnica sin clientes vendidos.
- El checklist base tenga resultados conocidos o se pruebe despues de cada correccion.
- El cliente confirme que `geosis_fiscalizacion` se mantiene como modulo de supervisor/fiscalizador.
- Se acepte que la primera implementacion sera tecnica y conservadora: corregir errores claros sin cambiar el comportamiento funcional visible mas de lo necesario.

## 9. Primera Fase 1 recomendada

Orden propuesto:

1. Corregir `UserError` en presupuesto.
2. Cargar templates faltantes de `geosis_website`.
3. Revisar/cargar assets publicos del website si corresponde.
4. Alinear grupo de perito en `geosis_mobile`.
5. Preparar refactor de `geosis_fiscalizacion` para extender planillas sin romper datos.
6. Agregar pruebas o checklist tecnico para validar instalacion/actualizacion de modulos.
