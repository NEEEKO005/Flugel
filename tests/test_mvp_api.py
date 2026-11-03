"""Integration checks for the MVP API using an isolated SQLite database."""
import json
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server as flugel


class FlugelApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = Path(__file__).resolve().parents[1] / "data" / "flugel-test.db"
        cls.test_db.unlink(missing_ok=True)
        flugel.DB_PATH = cls.test_db
        flugel.init_db()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), flugel.Handler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)
        cls.test_db.unlink(missing_ok=True)

    def call(self, method, path, body=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = json.dumps(body).encode() if body is not None else None
        request = Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urlopen(request) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read())

    def test_login_registration_and_session(self):
        status, created = self.call("POST", "/api/auth/register", {
            "name": "Prueba Viajera", "email": "prueba@example.com",
            "password": "ClaveSegura9", "role": "client",
        })
        self.assertEqual(status, 200)
        self.assertEqual(created["user"]["role"], "client")
        self.assertEqual(self.call("POST", "/api/auth/register", {
            "name": "Duplicada", "email": "prueba@example.com",
            "password": "ClaveSegura9",
        })[0], 409)
        self.assertEqual(self.call("POST", "/api/auth/login", {
            "email": "viajero@flugel.com", "password": "Viaje2026!", "role": "worker",
        })[0], 403)
        self.assertEqual(self.call("POST", "/api/auth/login", {
            "email": "equipo@flugel.com", "password": "Flugel2026!", "role": "client",
        })[0], 403)
        self.assertEqual(self.call("POST", "/api/auth/login", {
            "email": "prueba@example.com", "password": "incorrecta",
            "role": "client",
        })[0], 401)
        status, login = self.call("POST", "/api/auth/login", {
            "email": "prueba@example.com", "password": "ClaveSegura9",
            "role": "client",
        })
        self.assertEqual(status, 200)
        token = login["token"]
        self.assertEqual(self.call("DELETE", "/api/auth/session", token=token)[0], 200)
        self.assertEqual(self.call("GET", "/api/trips", token=token)[0], 401)

    def test_auth_validation_and_unknown_routes(self):
        self.assertEqual(self.call("POST", "/api/auth/login", {
            "email": "not-an-email", "password": "ClaveSegura9", "role": "client",
        })[0], 400)
        self.assertEqual(self.call("POST", "/api/auth/login", {
            "email": "nadie@example.com", "password": "12345", "role": "client",
        })[0], 400)
        self.assertEqual(self.call("POST", "/api/auth/login", {
            "email": "nadie@example.com", "password": "ClaveSegura9", "role": "client",
        })[0], 401)
        self.assertEqual(self.call("POST", "/api/auth/register", {
            "name": "Invitada", "email": "mal-correo", "password": "ClaveSegura9",
        })[0], 400)
        self.assertEqual(self.call("POST", "/api/auth/register", {
            "name": "Invitada", "email": "invitada@example.com", "password": "12345",
        })[0], 400)
        self.assertEqual(self.call("POST", "/api/auth/register", {
            "email": "invitada@example.com", "password": "ClaveSegura9",
        })[0], 400)
        self.assertEqual(self.call("POST", "/api/auth/register", {
            "name": "Empleado", "email": "empleado@example.com",
            "password": "ClaveSegura9", "role": "worker",
        })[0], 403)
        self.assertEqual(self.call("GET", "/api/no-existe")[0], 404)
        self.assertEqual(self.call("DELETE", "/api/no-existe")[0], 404)

    def test_destinations_and_trip_access(self):
        status, destinations = self.call("GET", "/api/destinations")
        self.assertEqual(status, 200)
        self.assertEqual(len(destinations), 8)
        self.assertTrue(all({"season", "visa", "vaccine"} <= item.keys() for item in destinations))
        status, kyoto = self.call("GET", "/api/destinations/kyoto")
        self.assertEqual(status, 200)
        self.assertEqual(kyoto["name"], "Kioto")
        self.assertEqual(self.call("GET", "/api/trips")[0], 401)
        status, login = self.call("POST", "/api/auth/login", {
            "email": "viajero@flugel.com", "password": "Viaje2026!", "role": "client",
        })
        self.assertEqual(status, 200)
        self.assertEqual(self.call("GET", "/api/trips", token=login["token"]), (200, []))
        worker_status, worker = self.call("POST", "/api/auth/login", {
            "email": "equipo@flugel.com", "password": "Flugel2026!", "role": "worker",
        })
        self.assertEqual(worker_status, 200)
        self.assertEqual(self.call("GET", "/api/trips", token=worker["token"])[0], 403)

    def test_reports_create_list_and_update(self):
        worker_status, worker = self.call("POST", "/api/auth/login", {
            "email": "equipo@flugel.com", "password": "Flugel2026!", "role": "worker",
        })
        client_status, client = self.call("POST", "/api/auth/login", {
            "email": "viajero@flugel.com", "password": "Viaje2026!", "role": "client",
        })
        self.assertEqual(worker_status, 200)
        self.assertEqual(client_status, 200)
        self.assertEqual(self.call("GET", "/api/reports")[0], 403)
        self.assertEqual(self.call("POST", "/api/reports", {"destination": "", "question": "Consulta"}, client["token"])[0], 400)
        self.assertEqual(self.call("PATCH", "/api/reports/FL-2048", {"status": "Finalizada"}, client["token"])[0], 403)
        self.assertEqual(self.call("POST", "/api/reports", {"destination": "Kioto", "question": "¿Qué temporada recomiendan?"})[0], 401)
        status, report = self.call("POST", "/api/reports", {
            "destination": "Kioto", "question": "¿Qué temporada recomiendan?",
        }, token=client["token"])
        self.assertEqual(status, 201)
        self.assertEqual(report["question"], "¿Qué temporada recomiendan?")
        status, reports = self.call("GET", "/api/reports", token=worker["token"])
        self.assertEqual(status, 200)
        self.assertTrue(any(item["id"] == report["id"] for item in reports))
        status, updated = self.call("PATCH", f"/api/reports/{report['id']}", {"status": "En proceso"}, worker["token"])
        self.assertEqual(status, 200)
        self.assertEqual(updated["status"], "En proceso")
        status, finalized = self.call("PATCH", f"/api/reports/{report['id']}", {"status": "Finalizada"}, worker["token"])
        self.assertEqual(status, 200)
        self.assertEqual(finalized["status"], "Finalizada")
        _, reports = self.call("GET", "/api/reports", token=worker["token"])
        self.assertTrue(any(item["id"] == report["id"] and item["status"] == "Finalizada" for item in reports))
        self.assertEqual(self.call("PATCH", f"/api/reports/{report['id']}", {"status": "invalid"}, worker["token"])[0], 400)
        self.assertEqual(self.call("PATCH", "/api/reports/FL-INEXISTENTE", {"status": "Finalizada"}, worker["token"])[0], 404)

    def test_country_patch_rejects_unauthorized_invalid_and_duplicate_updates(self):
        _, worker = self.call("POST", "/api/auth/login", {
            "email": "equipo@flugel.com", "password": "Flugel2026!", "role": "worker",
        })
        _, client = self.call("POST", "/api/auth/login", {
            "email": "viajero@flugel.com", "password": "Viaje2026!", "role": "client",
        })
        japan = "/api/countries/" + quote("Japón")
        self.assertEqual(self.call("PATCH", japan, {"name": "Japón"})[0], 403)
        self.assertEqual(self.call("PATCH", japan, {"name": "Japón"}, client["token"])[0], 403)
        self.assertEqual(self.call("PATCH", "/api/countries/NoExiste", {"name": "NoExiste"}, worker["token"])[0], 404)
        self.assertEqual(self.call("PATCH", japan, {"name": "", "season": "", "visa": "", "vaccine": ""}, worker["token"])[0], 400)
        self.assertEqual(self.call("PATCH", japan, {"name": "Indonesia", "season": "T", "visa": "V", "vaccine": "V"}, worker["token"])[0], 409)

    def test_country_edit_handles_accents_and_persists(self):
        _, worker = self.call("POST", "/api/auth/login", {
            "email": "equipo@flugel.com", "password": "Flugel2026!", "role": "worker",
        })
        _, client = self.call("POST", "/api/auth/login", {
            "email": "viajero@flugel.com", "password": "Viaje2026!", "role": "client",
        })
        self.assertEqual(self.call("PATCH", "/api/countries/Jap%C3%B3n", {"name": "Japón"})[0], 403)
        self.assertEqual(self.call("PATCH", "/api/countries/Jap%C3%B3n", {"name": "Japón"}, client["token"])[0], 403)
        status, countries = self.call("GET", "/api/countries")
        self.assertEqual(status, 200)
        japan = next(country for country in countries if country["name"] == "Japón")
        status, changed = self.call("PATCH", f"/api/countries/{quote('Japón')}", {
            "name": "Japón", "season": "Octubre–abril", "visa": "Consultar consulado",
            "vaccine": "Revisar recomendaciones",
        }, worker["token"])
        self.assertEqual(status, 200)
        self.assertEqual(changed["season"], "Octubre–abril")
        _, countries = self.call("GET", "/api/countries")
        persisted = next(country for country in countries if country["name"] == japan["name"])
        self.assertEqual(persisted["visa"], "Consultar consulado")

    def test_landing_page_requires_login_and_disables_navigation(self):
        request = Request(self.base + "/")
        with urlopen(request) as response:
            html = response.read().decode("utf-8")
            self.assertIn("no-store", response.headers.get("Cache-Control", ""))
        self.assertIn('id="view-login"', html)
        self.assertIn('type="email" id="email"', html)
        self.assertIn('type="password" id="password"', html)
        self.assertIn('minlength="6"', html)
        self.assertIn('data-role="client"', html)
        self.assertIn('data-role="worker"', html)
        self.assertIn('data-view="home" disabled aria-disabled="true"', html)
        self.assertIn('data-view="trips" disabled aria-disabled="true"', html)
        self.assertIn('data-view="reports" disabled aria-disabled="true"', html)
        self.assertIn('data-view="countries" disabled aria-disabled="true"', html)
        self.assertIn('<option value="Activos" selected>Solicitudes activas</option>', html)
        self.assertIn("app.js?v=flugel-auth-fix-20261103d", html)
        with urlopen(self.base + "/app.js") as response:
            script = response.read().decode("utf-8")
        self.assertNotIn("Conéctate al servidor Flugel para iniciar sesión", script)
        self.assertIn("$('#auth-form').onsubmit=handleAuth", script)
        self.assertNotIn("$('#google-signin')", script)
        self.assertIn("updateNavigationAccess()", script)
        self.assertIn("requiredRole=view==='trips'?'client'", script)
        self.assertIn("['reports','countries'].includes(view)?'worker'", script)
        self.assertIn("currentUser?.role", script)
        self.assertIn("$('#add-country,[data-edit-country],.status-select')", script)
        self.assertIn("status==='Activos'?r.status!=='Finalizada'", script)


if __name__ == "__main__":
    unittest.main()
