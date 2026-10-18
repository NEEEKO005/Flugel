# Flugel

Prototipo web de viajes con frontend HTML, CSS y JavaScript, y backend Python con SQLite.

## Iniciar

1. Instala Python 3.10 o superior.
2. Abre una terminal en esta carpeta y ejecuta `python server.py`.
3. Visita [http://127.0.0.1:8000](http://127.0.0.1:8000).

La base `data/flugel.db` se crea automáticamente. Para borrar los datos locales de prueba, detén el servidor y elimina ese archivo.

La página inicia en el formulario de acceso. Cuentas incluidas:

- Viajero: `viajero@flugel.com` / `Viaje2026!`
- Equipo Flugel: `equipo@flugel.com` / `Flugel2026!`

## Funciones MVP

- Crear cuenta de viajero e iniciar/cerrar sesión.
- Explorar, buscar y filtrar destinos; consultar temporada, visa y vacunas.
- Enviar reportes desde la interfaz de viajero.
- Entrar a Equipo Flugel para consultar reportes, cambiar su estado y editar datos de países.

También puedes crear otras cuentas de viajeros desde **Crear cuenta**. Las imágenes requieren internet. La información de visa, vacunas y temporada es ilustrativa; debe verificarse con fuentes oficiales.
