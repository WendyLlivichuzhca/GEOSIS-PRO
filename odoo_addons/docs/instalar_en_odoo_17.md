# Instalar GEOSIS-PRO en tu Odoo 17

## Lo que vas a hacer tu

No necesitas programar.
Solo vas a copiar carpetas, revisar una ruta y actualizar Apps.

## Carpetas que debes copiar a tu VM

Copia estas dos carpetas:

- `odoo_addons/geosis_base`
- `odoo_addons/geosis_recursos`

Hacia esta ruta de tu VM:

- `/odoo/custom/addons`

Al final deberias tener algo asi:

```text
/odoo/custom/addons/geosis_base
/odoo/custom/addons/geosis_recursos
```

## Revisar tu archivo de configuracion

Abre:

```text
/etc/odoo-server.conf
```

Y revisa que `addons_path` incluya tu carpeta custom.

Debe verse parecido a esto:

```ini
addons_path = /odoo/odoo-server/addons,/odoo/custom/addons
```

Si no esta `/odoo/custom/addons`, agregalo.

## Reiniciar Odoo

En Ubuntu normalmente sera uno de estos comandos:

```bash
sudo systemctl restart odoo-server
```

o

```bash
sudo systemctl restart odoo
```

Si uno no funciona, prueba el otro.

## Activar modo desarrollador

En tu navegador:

1. entra a Odoo
2. ve a `Settings`
3. activa `Developer Mode`

## Actualizar la lista de Apps

Luego:

1. entra a `Apps`
2. busca `Update Apps List`
3. actualiza la lista

## Instalar los modulos

Instala en este orden:

1. `GEOSIS-PRO Base`
2. `GEOSIS-PRO Recursos`

## Que deberias ver luego

Despues de instalar:

- un menu principal `GEOSIS-PRO`
- un submenu `Catalogos`
- una opcion `Recursos`

## Si algo falla

Si Odoo no encuentra los modulos, revisa estas 3 cosas:

1. que las carpetas si esten en `/odoo/custom/addons`
2. que `addons_path` tenga esa ruta
3. que hayas reiniciado Odoo antes de actualizar Apps

## Siguiente paso despues de esto

Cuando esto ya funcione, el siguiente modulo que construiremos sera:

- `geosis_apu`

Ese sera el modulo donde viviran los rubros/APU y sus lineas de recursos.
