"""
Servidor Central MatchSport (Red Local / Wi-Fi)
Diseñado para que cualquier usuario conectado al mismo Wi-Fi se conecte sin configuraciones complejas.
"""

import os
import sqlite3
import socket
import threading
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ==============================================================================
# CONFIGURACIÓN Y BASE DE DATOS
# ==============================================================================

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "matchsport.db")
PUERTO_HTTP = 8000
PUERTO_DISCOVERY = 8005

def obtener_conexion():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = obtener_conexion()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            deportes_favoritos TEXT NOT NULL,
            nivel TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creador_id INTEGER,
            deporte TEXT NOT NULL,
            nivel_requerido TEXT NOT NULL,
            hora TEXT NOT NULL,
            plazas_disponibles INTEGER NOT NULL,
            FOREIGN KEY (creador_id) REFERENCES usuarios (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inscripciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            partido_id INTEGER NOT NULL,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
            FOREIGN KEY (partido_id) REFERENCES partidos (id)
        )
    """)

    cursor.execute("SELECT COUNT(*) as total FROM partidos")
    total_partidos = cursor.fetchone()["total"]

    if total_partidos == 0:
        partidos_mock = [
            (None, "Pádel", "Principiante", "10:30", 3),
            (None, "Pádel", "Intermedio", "18:00", 2),
            (None, "Pádel", "Experto", "19:30", 1),
            (None, "Tenis", "Principiante", "09:30", 1),
            (None, "Tenis", "Intermedio", "17:30", 2),
            (None, "Tenis", "Experto", "20:30", 1),
            (None, "Fútbol", "Principiante", "19:00", 5),
            (None, "Fútbol", "Intermedio", "20:30", 4),
            (None, "Fútbol", "Experto", "21:00", 2),
            (None, "Running", "Principiante", "08:00", 4),
            (None, "Running", "Intermedio", "19:00", 3),
            (None, "Running", "Experto", "20:00", 2),
            (None, "Pádel", "Principiante", "17:30", 2),
            (None, "Fútbol", "Principiante", "18:00", 3),
            (None, "Tenis", "Principiante", "11:00", 2),
            (None, "Running", "Principiante", "12:30", 5),
            (None, "Pádel", "Intermedio", "12:30", 1),
            (None, "Pádel", "Intermedio", "20:30", 2),
        ]
        cursor.executemany("""
            INSERT INTO partidos (creador_id, deporte, nivel_requerido, hora, plazas_disponibles)
            VALUES (?, ?, ?, ?, ?)
        """, partidos_mock)
        conn.commit()

    conn.close()

# ==============================================================================
# MODELOS PYDANTIC
# ==============================================================================

class UsuarioCreate(BaseModel):
    nombre: str
    deportes_favoritos: str
    nivel: str

class PartidoCreate(BaseModel):
    creador_id: Optional[int] = None
    deporte: str
    nivel_requerido: str
    hora: str
    plazas_disponibles: int

class UnirseRequest(BaseModel):
    usuario_id: Optional[int] = None

# ==============================================================================
# FASTAPI APP
# ==============================================================================

app = FastAPI(title="MatchSport Local Network Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
def estado_servidor():
    return {"estado": "online", "mensaje": "Servidor MatchSport en Red Local listo."}

# ----------------- USUARIOS -----------------

@app.get("/usuarios")
def listar_usuarios():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/usuarios")
def registrar_usuario(usuario: UsuarioCreate):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO usuarios (nombre, deportes_favoritos, nivel)
        VALUES (?, ?, ?)
    """, (usuario.nombre, usuario.deportes_favoritos, usuario.nivel))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return {"id": user_id, "nombre": usuario.nombre, "deportes_favoritos": usuario.deportes_favoritos, "nivel": usuario.nivel}

# ----------------- PARTIDOS -----------------

@app.get("/partidos")
def listar_partidos(
    deportes: Optional[str] = Query(None),
    nivel: Optional[str] = Query(None),
    franja: Optional[str] = Query(None)
):
    conn = obtener_conexion()
    cursor = conn.cursor()

    condiciones = ["p.plazas_disponibles > 0"]
    parametros = []

    if deportes and nivel:
        lista_deportes = [d.strip() for d in deportes.split(",") if d.strip()]
        if lista_deportes:
            placeholders = ",".join(["?"] * len(lista_deportes))
            condiciones.append(f"p.deporte IN ({placeholders})")
            condiciones.append("p.nivel_requerido = ?")
            parametros.extend(lista_deportes)
            parametros.append(nivel)

    if franja and franja != "Todos":
        if franja == "Mañanas (08:00 - 13:59)":
            condiciones.append("p.hora >= '08:00' AND p.hora < '14:00'")
        elif franja == "Tardes (14:00 - 19:59)":
            condiciones.append("p.hora >= '14:00' AND p.hora < '20:00'")
        elif franja == "Noches (20:00 - 23:59)":
            condiciones.append("p.hora >= '20:00' AND p.hora <= '23:59'")

    where_clause = " AND ".join(condiciones)
    query = f"""
        SELECT p.id, p.creador_id, p.deporte, p.nivel_requerido, p.hora, p.plazas_disponibles,
               u.nombre AS creador_nombre
        FROM partidos p
        LEFT JOIN usuarios u ON p.creador_id = u.id
        WHERE {where_clause}
        ORDER BY p.hora ASC
    """
    cursor.execute(query, parametros)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/partidos")
def publicar_partido(partido: PartidoCreate):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO partidos (creador_id, deporte, nivel_requerido, hora, plazas_disponibles)
        VALUES (?, ?, ?, ?, ?)
    """, (partido.creador_id, partido.deporte, partido.nivel_requerido, partido.hora, partido.plazas_disponibles))
    conn.commit()
    partido_id = cursor.lastrowid
    conn.close()
    return {"id": partido_id, **partido.dict()}

@app.post("/partidos/{partido_id}/unirse")
def unirse_partido(partido_id: int, req: UnirseRequest):
    conn = obtener_conexion()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE partidos
        SET plazas_disponibles = plazas_disponibles - 1
        WHERE id = ? AND plazas_disponibles > 0
    """, (partido_id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Sin plazas o partido no encontrado")

    if req.usuario_id:
        cursor.execute("""
            INSERT INTO inscripciones (usuario_id, partido_id)
            VALUES (?, ?)
        """, (req.usuario_id, partido_id))

    conn.commit()
    conn.close()
    return {"ok": True}

@app.get("/usuarios/{user_id}/partidos")
def partidos_del_usuario(user_id: int):
    conn = obtener_conexion()
    cursor = conn.cursor()
    query = """
        SELECT p.id, p.creador_id, p.deporte, p.nivel_requerido, p.hora, p.plazas_disponibles,
               u.nombre AS creador_nombre, i.fecha_registro
        FROM inscripciones i
        JOIN partidos p ON i.partido_id = p.id
        LEFT JOIN usuarios u ON p.creador_id = u.id
        WHERE i.usuario_id = ?
        ORDER BY p.hora ASC
    """
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ==============================================================================
# DETECCIÓN DE RED LOCAL Y AUTO-DISCOVERY
# ==============================================================================

def obtener_ip_local():
    """Detecta la IP Wi-Fi / LAN real de este ordenador."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def hilo_auto_discovery():
    """Escucha llamadas de auto-descubrimiento en el Wi-Fi para conectar automáticamente a los clientes."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", PUERTO_DISCOVERY))
        while True:
            data, addr = sock.recvfrom(1024)
            if data == b"MATCHSPORT_DISCOVER":
                # Responde al cliente con el puerto HTTP
                sock.sendto(f"MATCHSPORT_HERE:{PUERTO_HTTP}".encode(), addr)
    except Exception:
        pass

if __name__ == "__main__":
    ip_local = obtener_ip_local()

    # Iniciar auto-descubrimiento en segundo plano
    t_disc = threading.Thread(target=hilo_auto_discovery, daemon=True)
    t_disc.start()

    print("=" * 65)
    print(" 🚀  SERVIDOR MATCHSPORT (RED LOCAL / WI-FI)")
    print("=" * 65)
    print(f"  Tu IP en esta red local es:   {ip_local}")
    print(f"  Dirección para este PC:       http://localhost:{PUERTO_HTTP}")
    print(f"  Dirección para otros PCs:     http://{ip_local}:{PUERTO_HTTP}")
    print("=" * 65)
    print("  * Los otros ordenadores en este mismo Wi-Fi se conectarán")
    print("    automáticamente al abrir su aplicación.")
    print("  * Mantén esta ventana abierta mientras jueguen.")
    print("=" * 65 + "\n")

    uvicorn.run("servidor:app", host="0.0.0.0", port=PUERTO_HTTP, reload=False, log_level="warning")
