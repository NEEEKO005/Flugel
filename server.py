"""Servidor local Flugel: frontend estático y API JSON con SQLite."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "flugel.db"

DESTINATIONS = [
    {"id":"kyoto","name":"Kioto","country":"Japón","tag":"Cultura","type":"Ciudad","price":"3.480.000","rating":"4.9","flag":"🇯🇵","season":"Mar – May · Sep – Nov","visa":"No requerida*","vaccine":"No obligatoria*","image":"https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=900&q=80","desc":"Templos antiguos, senderos entre bambú y una ciudad que encuentra belleza en cada detalle."},
    {"id":"amalfi","name":"Costa Amalfitana","country":"Italia","tag":"Mar y sol","type":"Playa","price":"4.250.000","rating":"4.8","flag":"🇮🇹","season":"Abr – Jun · Sep – Oct","visa":"No requerida*","vaccine":"No obligatoria*","image":"https://images.unsplash.com/photo-1533587851505-d119e13fa0d7?auto=format&fit=crop&w=900&q=80","desc":"Pueblos de colores suspendidos sobre el Mediterráneo, perfectos para perderse sin prisa."},
    {"id":"patagonia","name":"Patagonia","country":"Argentina","tag":"Aventura","type":"Naturaleza","price":"2.890.000","rating":"4.9","flag":"🇦🇷","season":"Nov – Mar","visa":"No requerida*","vaccine":"No obligatoria*","image":"https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=900&q=80","desc":"Montañas, glaciares y horizontes abiertos para quienes buscan aventura en estado puro."},
    {"id":"bali","name":"Bali","country":"Indonesia","tag":"Escapada tropical","type":"Playa","price":"3.790.000","rating":"4.8","flag":"🇮🇩","season":"Abr – Oct","visa":"Consultar e-VOA*","vaccine":"Revisar recomendaciones*","image":"https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=900&q=80","desc":"Arrozales verdes, templos tranquilos y playas para bajar el ritmo y reconectar."},
    {"id":"lisboa","name":"Lisboa","country":"Portugal","tag":"City break","type":"Ciudad","price":"2.650.000","rating":"4.7","flag":"🇵🇹","season":"Mar – Jun · Sep – Oct","visa":"No requerida*","vaccine":"No obligatoria*","image":"https://images.unsplash.com/photo-1555881400-74d7acaacd8b?auto=format&fit=crop&w=900&q=80","desc":"Tranvías, azulejos y miradores al Atlántico en una ciudad hecha para caminar."},
    {"id":"santorini","name":"Santorini","country":"Grecia","tag":"Mar y sol","type":"Playa","price":"4.190.000","rating":"4.8","flag":"🇬🇷","season":"May – Jun · Sep","visa":"No requerida*","vaccine":"No obligatoria*","image":"https://images.unsplash.com/photo-1533105079780-92b9be482077?auto=format&fit=crop&w=900&q=80","desc":"Casas blancas frente al mar Egeo, tardes doradas y cenas con vista a la caldera."},
    {"id":"cartagena","name":"Cartagena","country":"Colombia","tag":"Historia","type":"Ciudad","price":"890.000","rating":"4.8","flag":"🇨🇴","season":"Dic – Abr","visa":"No aplica","vaccine":"Revisar zona*","image":"https://images.unsplash.com/photo-1583531352515-8884af319dc1?auto=format&fit=crop&w=900&q=80","desc":"Calles coloniales llenas de vida, balcones floridos y el Caribe a un paso."},
    {"id":"dolomites","name":"Dolomitas","country":"Italia","tag":"Naturaleza","type":"Naturaleza","price":"3.850.000","rating":"4.9","flag":"🇮🇹","season":"Jun – Sep · Dic – Mar","visa":"No requerida*","vaccine":"No obligatoria*","image":"https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=900&q=80","desc":"Picos rosados al atardecer, lagos alpinos y rutas para todos los ritmos."},
]
COUNTRIES = [
    {"flag":"🇯🇵","name":"Japón","region":"Asia oriental","season":"Mar – May · Sep – Nov","visa":"No requerida*","vaccine":"No obligatoria*"},
    {"flag":"🇮🇩","name":"Indonesia","region":"Sudeste asiático","season":"Abr – Oct","visa":"Consultar e-VOA*","vaccine":"Revisar recomendaciones*"},
    {"flag":"🇮🇹","name":"Italia","region":"Europa","season":"Abr – Jun · Sep – Oct","visa":"No requerida*","vaccine":"No obligatoria*"},
    {"flag":"🇦🇷","name":"Argentina","region":"Sudamérica","season":"Nov – Mar","visa":"No requerida*","vaccine":"No obligatoria*"},
]
DEMO_ACCOUNTS = [
    ("Valentina Ríos", "viajero@flugel.com", "Viaje2026!", "client"),
    ("Sofía · Flugel", "equipo@flugel.com", "Flugel2026!", "worker"),
]


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, salt TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('client','worker')));
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, user_id INTEGER REFERENCES users(id), name TEXT NOT NULL, email TEXT NOT NULL, destination TEXT NOT NULL, question TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Ya hecha', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS countries(name TEXT PRIMARY KEY, flag TEXT NOT NULL, region TEXT NOT NULL, season TEXT NOT NULL, visa TEXT NOT NULL, vaccine TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS trips(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id), city TEXT NOT NULL, country TEXT NOT NULL, date_from TEXT NOT NULL, date_to TEXT NOT NULL, duration TEXT NOT NULL, travelers TEXT NOT NULL, status TEXT NOT NULL, image TEXT NOT NULL, flight TEXT NOT NULL);
        """)
        for name, email, password, role in DEMO_ACCOUNTS:
            if not db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                salt = secrets.token_hex(16)
                digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 240_000).hex()
                db.execute("INSERT INTO users(name,email,salt,password_hash,role) VALUES(?,?,?,?,?)", (name,email,salt,digest,role))
        if db.execute("SELECT COUNT(*) FROM countries").fetchone()[0] == 0:
            db.executemany("INSERT INTO countries VALUES(:name,:flag,:region,:season,:visa,:vaccine)", COUNTRIES)
        if db.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 0:
            samples = [("Camila Torres","camila.t@email.com","Tokio, Japón","¿Necesito visa para una escala de 8 horas?","Ya hecha"),("Andrés Mejía","andres.m@email.com","Bali, Indonesia","Quiero confirmar vacunas para viajar en enero.","En proceso"),("Lucía Pardo","lucia.p@email.com","París, Francia","¿Puedo cambiar la fecha de mi reserva?","En proceso"),("Mateo Rojas","mateo.r@email.com","Cusco, Perú","¿Qué ropa recomiendan para esta temporada?","Finalizada")]
            for name,email,dest,question,status in samples:
                db.execute("INSERT INTO reports(code,name,email,destination,question,status,created_at) VALUES(?,?,?,?,?,?,?)", ("FL-"+str(2045+len(db.execute('SELECT id FROM reports').fetchall())),name,email,dest,question,status,datetime.now(timezone.utc).isoformat()))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 1_000_000:
                return {}
            return json.loads(self.rfile.read(size) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return {}

    def current_user(self, db):
        token = self.headers.get("Authorization", "").removeprefix("Bearer ")
        row = db.execute("SELECT users.* FROM sessions JOIN users ON users.id=sessions.user_id WHERE sessions.token=?", (token,)).fetchone() if token else None
        return row

    def do_GET(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            return super().do_GET()
        with connect() as db:
            if path == "/api/destinations":
                return self.send_json(DESTINATIONS)
            if path.startswith("/api/destinations/"):
                item = next((d for d in DESTINATIONS if d["id"] == path.rsplit("/",1)[-1]), None)
                return self.send_json(item or {"error":"Destino no encontrado"}, 200 if item else 404)
            if path == "/api/countries":
                return self.send_json([dict(r) for r in db.execute("SELECT * FROM countries ORDER BY name")])
            if path == "/api/reports":
                user = self.current_user(db)
                if not user or user["role"] != "worker": return self.send_json({"error":"Acceso solo para el equipo Flugel"},403)
                rows = db.execute("SELECT reports.*, COALESCE(users.name,reports.name) AS display_name FROM reports LEFT JOIN users ON users.id=reports.user_id ORDER BY reports.id DESC").fetchall()
                return self.send_json([self.report_json(r) for r in rows])
            if path == "/api/trips":
                user = self.current_user(db)
                if not user: return self.send_json({"error":"Inicia sesión para ver tus viajes"},401)
                rows = db.execute("SELECT * FROM trips WHERE user_id=? ORDER BY id DESC",(user["id"],)).fetchall()
                return self.send_json([dict(id=r["id"],city=r["city"],country=r["country"],**{"from":r["date_from"],"to":r["date_to"]},duration=r["duration"],travelers=r["travelers"],status=r["status"],image=r["image"],flight=r["flight"]) for r in rows])
            return self.send_json({"error":"Ruta no encontrada"},404)

    @staticmethod
    def report_json(row):
        name = row["display_name"] if "display_name" in row.keys() else row["name"]
        initials = "".join(part[0] for part in name.split()[:2]).upper()
        created = datetime.fromisoformat(row["created_at"])
        date = created.astimezone().strftime("%d %b, %H:%M")
        return {"id":row["code"],"name":name,"email":row["email"],"initials":initials,"dest":row["destination"],"question":row["question"],"date":date,"status":row["status"]}

    def do_POST(self):
        path, data = urlparse(self.path).path, self.body()
        with connect() as db:
            if path == "/api/auth/register" or path == "/api/auth/login":
                email = str(data.get("email", "")).strip().lower()
                password = str(data.get("password", ""))
                mode = "register" if path.endswith("register") else "login"
                if "@" not in email or len(password) < 6: return self.send_json({"error":"Ingresa un correo válido y una contraseña de al menos 6 caracteres."},400)
                if mode == "register":
                    if data.get("role", "client") != "client": return self.send_json({"error":"El registro está disponible para viajeros. El equipo Flugel usa su cuenta asignada."},403)
                    name = str(data.get("name", "")).strip()
                    if not name: return self.send_json({"error":"Escribe tu nombre completo."},400)
                    salt = secrets.token_hex(16)
                    digest = hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),240_000).hex()
                    try: db.execute("INSERT INTO users(name,email,salt,password_hash,role) VALUES(?,?,?,?,?)",(name,email,salt,digest,"client"))
                    except sqlite3.IntegrityError: return self.send_json({"error":"Ya existe una cuenta con ese correo."},409)
                    user = db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
                else:
                    user = db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
                    if not user: return self.send_json({"error":"Correo o contraseña incorrectos. Crea una cuenta si aún no tienes una."},401)
                    else:
                        digest=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(user["salt"]),240_000).hex()
                        if not secrets.compare_digest(digest,user["password_hash"]): return self.send_json({"error":"Correo o contraseña incorrectos."},401)
                        if data.get("role") == "worker" and user["role"] != "worker": return self.send_json({"error":"Esta cuenta no tiene acceso al equipo Flugel."},403)
                token=secrets.token_urlsafe(32)
                db.execute("INSERT INTO sessions VALUES(?,?,?)",(token,user["id"],datetime.now(timezone.utc).isoformat()))
                return self.send_json({"token":token,"user":{"name":user["name"],"email":user["email"],"role":user["role"]}})
            if path == "/api/reports":
                user=self.current_user(db)
                if not user: return self.send_json({"error":"Inicia sesión para enviar un reporte."},401)
                destination=str(data.get("destination"," ")).strip(); question=str(data.get("question"," ")).strip()
                if not destination or not question: return self.send_json({"error":"Completa el destino y tu pregunta."},400)
                code="FL-"+secrets.token_hex(3).upper()
                cur=db.execute("INSERT INTO reports(code,user_id,name,email,destination,question,status,created_at) VALUES(?,?,?,?,?,?,?,?)",(code,user["id"],user["name"],user["email"],destination,question,"Ya hecha",datetime.now(timezone.utc).isoformat()))
                row=db.execute("SELECT * FROM reports WHERE id=?",(cur.lastrowid,)).fetchone()
                return self.send_json(self.report_json(row),201)
            return self.send_json({"error":"Ruta no encontrada"},404)

    def do_PATCH(self):
        path, data = urlparse(self.path).path, self.body()
        with connect() as db:
            user=self.current_user(db)
            if not user or user["role"] != "worker": return self.send_json({"error":"Acceso solo para el equipo Flugel"},403)
            if path.startswith("/api/reports/"):
                code=path.rsplit("/",1)[-1]; status=data.get("status")
                if status not in ("Ya hecha","En proceso","Finalizada"): return self.send_json({"error":"Estado no válido"},400)
                db.execute("UPDATE reports SET status=? WHERE code=?",(status,code))
                row=db.execute("SELECT reports.*, reports.name AS display_name FROM reports WHERE code=?",(code,)).fetchone()
                return self.send_json(self.report_json(row) if row else {"error":"Reporte no encontrado"},200 if row else 404)
            if path.startswith("/api/countries/"):
                old_name=path.rsplit("/",1)[-1]
                country=db.execute("SELECT * FROM countries WHERE name=?",(old_name,)).fetchone()
                if not country: return self.send_json({"error":"País no encontrado"},404)
                values={key:str(data.get(key,country[key])).strip() for key in ("name","season","visa","vaccine")}
                if any(not value for value in values.values()): return self.send_json({"error":"Completa todos los datos."},400)
                try: db.execute("UPDATE countries SET name=?,season=?,visa=?,vaccine=? WHERE name=?",(values["name"],values["season"],values["visa"],values["vaccine"],old_name))
                except sqlite3.IntegrityError: return self.send_json({"error":"Ya existe ese país."},409)
                return self.send_json(dict(db.execute("SELECT * FROM countries WHERE name=?",(values["name"],)).fetchone()))
            return self.send_json({"error":"Ruta no encontrada"},404)

    def do_DELETE(self):
        if urlparse(self.path).path != "/api/auth/session": return self.send_json({"error":"Ruta no encontrada"},404)
        token=self.headers.get("Authorization", "").removeprefix("Bearer ")
        with connect() as db: db.execute("DELETE FROM sessions WHERE token=?",(token,))
        return self.send_json({"ok":True})


if __name__ == "__main__":
    init_db()
    host=os.environ.get("FLUGEL_HOST","127.0.0.1")
    port=int(os.environ.get("FLUGEL_PORT","8000"))
    print(f"Flugel disponible en http://{host}:{port}")
    ThreadingHTTPServer((host,port),Handler).serve_forever()
