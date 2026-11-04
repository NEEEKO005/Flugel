# Flugel

Prototipo web de viajes con frontend HTML, CSS y JavaScript, y backend Python con SQLite.

## Iniciar

1. Instala Python 3.10 o superior.
2. Abre una terminal en esta carpeta y ejecuta `python server.py`.
3. Visita [http://127.0.0.1:8000](http://127.0.0.1:8000).

La base `data/flugel.db` se crea automáticamente. Para borrar los datos locales de prueba, detén el servidor y elimina ese archivo.

La página siempre inicia sin sesión en el formulario de acceso; al recargar, cierra la sesión anterior. **Mis viajes** requiere iniciar sesión. Cuentas incluidas:

- Viajero: `viajero@flugel.com` / `Viaje2026!`
- Equipo Flugel: `equipo@flugel.com` / `Flugel2026!`

## Funciones MVP

- Crear cuenta de viajero e iniciar/cerrar sesión.
- Explorar, buscar y filtrar destinos; consultar temporada, visa y vacunas.
- Enviar reportes desde la interfaz de viajero.
- Entrar a Equipo Flugel para consultar reportes, cambiar su estado y editar datos de países.

También puedes crear otras cuentas de viajeros desde **Crear cuenta**. Las imágenes requieren internet. La información de visa, vacunas y temporada es ilustrativa; debe verificarse con fuentes oficiales.

## Despliegue en Vercel

El archivo `vercel.json` dirige `/api/*` a una funcion Python que reutiliza las rutas del backend. Las cuentas demo estan disponibles en el despliegue.

Si no hay una base configurada, la funcion usa SQLite en `/tmp`, que es temporal. Conecta PostgreSQL en Vercel y define `DATABASE_URL` (o `POSTGRES_URL`) para conservar cuentas, sesiones, reportes y cambios de destinos entre ejecuciones.

Para Vercel, puedes instalar una base Neon desde **Storage / Marketplace** y conectarla al proyecto. Vercel agrega las variables de conexion; vuelve a desplegar despues de instalar la dependencia `psycopg` declarada en `requirements.txt`.
