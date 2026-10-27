"""
MatchSport - Cliente de Escritorio (Red Local / Wi-Fi)
Detecta y se conecta automáticamente al servidor MatchSport en la red local.
"""

import os
import socket
import requests
import tkinter.messagebox as messagebox
import customtkinter as ctk

# ==============================================================================
# CONFIGURACIÓN Y COMUNICACIÓN DE RED LOCAL
# ==============================================================================

DEFAULT_SERVER_URL = "http://127.0.0.1:8000"
PUERTO_DISCOVERY = 8005

DEPORTES_DISPONIBLES = ["Pádel", "Tenis", "Fútbol", "Running"]
NIVELES_DISPONIBLES = ["Principiante", "Intermedio", "Experto"]
HORARIOS_SUGERIDOS = [
    "08:00", "09:30", "11:00", "12:30",
    "16:00", "17:30", "19:00", "20:30", "22:00"
]

ICONOS_DEPORTE = {
    "Pádel": "🎾",
    "Tenis": "🎾",
    "Fútbol": "⚽",
    "Running": "🏃"
}

def api_check_health(base_url):
    """Comprueba si el servidor responde."""
    try:
        r = requests.get(f"{base_url}/", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False

def buscar_servidor_en_wifi():
    """
    Intenta localizar el servidor MatchSport en la red local:
    1. Si está en este mismo PC (localhost:8000), se conecta al instante.
    2. Si está en otro PC del mismo Wi-Fi, envía una señal de auto-detección.
    """
    # 1. Probar primero si el servidor está en este mismo ordenador
    if api_check_health("http://127.0.0.1:8000"):
        return "http://127.0.0.1:8000"

    # 2. Intentar auto-descubrimiento en el Wi-Fi por broadcast UDP
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(1.2)
        sock.sendto(b"MATCHSPORT_DISCOVER", ("255.255.255.255", PUERTO_DISCOVERY))
        data, addr = sock.recvfrom(1024)
        sock.close()
        if data.startswith(b"MATCHSPORT_HERE:"):
            puerto = data.decode().split(":")[1]
            return f"http://{addr[0]}:{puerto}"
    except Exception:
        pass

    return "http://127.0.0.1:8000"

def api_obtener_usuarios(base_url):
    try:
        r = requests.get(f"{base_url}/usuarios", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

def api_crear_usuario(base_url, nombre, deportes_favoritos, nivel):
    payload = {
        "nombre": nombre,
        "deportes_favoritos": deportes_favoritos,
        "nivel": nivel
    }
    r = requests.post(f"{base_url}/usuarios", json=payload, timeout=3)
    if r.status_code == 200:
        return r.json()
    raise Exception(r.text)

def api_buscar_partidos(base_url, deportes_str=None, nivel=None, franja=None):
    params = {}
    if deportes_str:
        params["deportes"] = deportes_str
    if nivel:
        params["nivel"] = nivel
    if franja and franja != "Todos":
        params["franja"] = franja
    try:
        r = requests.get(f"{base_url}/partidos", params=params, timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

def api_crear_partido(base_url, creador_id, deporte, nivel, hora, plazas):
    payload = {
        "creador_id": creador_id,
        "deporte": deporte,
        "nivel_requerido": nivel,
        "hora": hora,
        "plazas_disponibles": plazas
    }
    r = requests.post(f"{base_url}/partidos", json=payload, timeout=3)
    if r.status_code == 200:
        return r.json()
    raise Exception(r.text)

def api_unirse_partido(base_url, partido_id, usuario_id=None):
    payload = {"usuario_id": usuario_id}
    try:
        r = requests.post(f"{base_url}/partidos/{partido_id}/unirse", json=payload, timeout=3)
        return r.status_code == 200
    except Exception:
        return False

def api_obtener_mis_partidos(base_url, usuario_id):
    if not usuario_id:
        return []
    try:
        r = requests.get(f"{base_url}/usuarios/{usuario_id}/partidos", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

# ==============================================================================
# MODAL: CONEXIÓN EN RED LOCAL
# ==============================================================================

class ConfigServidorDialog(ctk.CTkToplevel):
    def __init__(self, parent, server_url, on_guardar):
        super().__init__(parent)
        self.server_url = server_url
        self.on_guardar = on_guardar

        self.title("Conexión en Red Local (Wi-Fi)")
        self.geometry("450x270")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 225
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 135
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        self._construir_ui()

    def _construir_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=20)

        lbl_t = ctk.CTkLabel(
            container,
            text="📡 Conexión en Red Local (Wi-Fi)",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        lbl_t.pack(anchor="w", pady=(0, 4))

        lbl_desc = ctk.CTkLabel(
            container,
            text="Si este es el PC anfitrión, usa 'http://127.0.0.1:8000'.\nSi juegas desde otro portátil, pon la IP local del anfitrión:",
            font=ctk.CTkFont(size=12),
            text_color="gray70",
            justify="left"
        )
        lbl_desc.pack(anchor="w", pady=(0, 10))

        self.entry_url = ctk.CTkEntry(container, placeholder_text="http://192.168.1.XX:8000")
        self.entry_url.insert(0, self.server_url)
        self.entry_url.pack(fill="x", pady=(0, 15))

        btn_box = ctk.CTkFrame(container, fg_color="transparent")
        btn_box.pack(fill="x")

        btn_auto = ctk.CTkButton(
            btn_box,
            text="🔍 Buscar en Wi-Fi",
            width=130,
            command=self._buscar_auto
        )
        btn_auto.pack(side="left")

        btn_guardar = ctk.CTkButton(
            btn_box,
            text="Conectar",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#2fa572",
            hover_color="#1e734e",
            width=110,
            command=self._guardar
        )
        btn_guardar.pack(side="right")

    def _buscar_auto(self):
        url_encontrada = buscar_servidor_en_wifi()
        if api_check_health(url_encontrada):
            self.entry_url.delete(0, "end")
            self.entry_url.insert(0, url_encontrada)
            messagebox.showinfo("Encontrado", f"¡Servidor localizado en la red local!\n{url_encontrada}", parent=self)
        else:
            messagebox.showwarning(
                "No encontrado",
                "No se detectó el servidor automáticamente.\nVerifica que 'iniciar_servidor.bat' esté corriendo en el PC anfitrión.",
                parent=self
            )

    def _guardar(self):
        nueva_url = self.entry_url.get().strip().rstrip("/")
        if not nueva_url:
            nueva_url = DEFAULT_SERVER_URL
        self.on_guardar(nueva_url)
        self.destroy()

# ==============================================================================
# MODAL: PUBLICAR PARTIDO
# ==============================================================================

class CrearPartidoDialog(ctk.CTkToplevel):
    def __init__(self, parent, server_url, usuario_actual=None, al_guardar=None):
        super().__init__(parent)
        self.parent = parent
        self.server_url = server_url
        self.usuario_actual = usuario_actual
        self.al_guardar = al_guardar

        self.title("Publicar Nuevo Partido")
        self.geometry("440x480")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 220
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 240
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        self._construir_ui()

    def _construir_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=20)

        lbl_titulo = ctk.CTkLabel(
            container,
            text="➕ Publicar Partido en Red Local",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_titulo.pack(anchor="w", pady=(0, 4))

        if self.usuario_actual:
            txt_creador = f"Organizado por: {self.usuario_actual['nombre']}"
        else:
            txt_creador = "Organizador: Anónimo (ningún perfil activo)"

        lbl_creador = ctk.CTkLabel(container, text=txt_creador, font=ctk.CTkFont(size=12), text_color="gray60")
        lbl_creador.pack(anchor="w", pady=(0, 15))

        lbl_dep = ctk.CTkLabel(container, text="Deporte:", font=ctk.CTkFont(weight="bold"))
        lbl_dep.pack(anchor="w", pady=(4, 2))
        self.combo_dep = ctk.CTkComboBox(container, values=DEPORTES_DISPONIBLES, state="readonly")
        self.combo_dep.set(DEPORTES_DISPONIBLES[0])
        self.combo_dep.pack(fill="x", pady=(0, 10))

        lbl_niv = ctk.CTkLabel(container, text="Nivel Requerido:", font=ctk.CTkFont(weight="bold"))
        lbl_niv.pack(anchor="w", pady=(4, 2))
        self.combo_niv = ctk.CTkComboBox(container, values=NIVELES_DISPONIBLES, state="readonly")
        if self.usuario_actual and self.usuario_actual.get("nivel") in NIVELES_DISPONIBLES:
            self.combo_niv.set(self.usuario_actual["nivel"])
        else:
            self.combo_niv.set(NIVELES_DISPONIBLES[0])
        self.combo_niv.pack(fill="x", pady=(0, 10))

        lbl_hora = ctk.CTkLabel(container, text="🕒 Hora para quedar:", font=ctk.CTkFont(weight="bold"))
        lbl_hora.pack(anchor="w", pady=(4, 2))
        self.combo_hora = ctk.CTkComboBox(container, values=HORARIOS_SUGERIDOS)
        self.combo_hora.set("19:00")
        self.combo_hora.pack(fill="x", pady=(0, 10))

        lbl_plz = ctk.CTkLabel(container, text="Plazas Libres:", font=ctk.CTkFont(weight="bold"))
        lbl_plz.pack(anchor="w", pady=(4, 2))
        self.combo_plz = ctk.CTkComboBox(
            container,
            values=["1", "2", "3", "4", "5", "6", "8", "10", "12"],
            state="readonly"
        )
        self.combo_plz.set("3")
        self.combo_plz.pack(fill="x", pady=(0, 20))

        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(5, 0))

        btn_cancelar = ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            fg_color="gray40",
            hover_color="gray50",
            width=100,
            command=self.destroy
        )
        btn_cancelar.pack(side="left")

        btn_guardar = ctk.CTkButton(
            btn_frame,
            text="Publicar Partido",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#2fa572",
            hover_color="#1e734e",
            command=self._guardar
        )
        btn_guardar.pack(side="right", fill="x", expand=True, padx=(10, 0))

    def _guardar(self):
        deporte = self.combo_dep.get()
        nivel = self.combo_niv.get()
        hora = self.combo_hora.get().strip()
        if not hora:
            messagebox.showwarning("Hora requerida", "Por favor indica la hora para quedar.", parent=self)
            return

        try:
            plazas = int(self.combo_plz.get())
            if plazas <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning("Valor inválido", "El número de plazas debe ser mayor que 0.", parent=self)
            return

        creador_id = self.usuario_actual["id"] if self.usuario_actual else None

        try:
            partido = api_crear_partido(self.server_url, creador_id, deporte, nivel, hora, plazas)
            if self.al_guardar:
                self.al_guardar(partido["id"], deporte, nivel, hora, plazas)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error al publicar", f"No se pudo guardar el partido:\n{e}", parent=self)

# ==============================================================================
# APLICACIÓN PRINCIPAL (CLIENTE GUI)
# ==============================================================================

class MatchSportApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MatchSport - Conecta con Jugadores (Red Local)")
        self.geometry("1060x720")
        self.minsize(920, 640)

        # Autodescubrimiento inicial en red local
        self.server_url = buscar_servidor_en_wifi()
        self.servidor_conectado = False
        self.usuario_actual = None
        self.check_vars = {}
        self.solo_compatibles_var = ctk.BooleanVar(value=True)

        self._crear_header()
        self._crear_cuerpo()
        self._crear_barra_estado()

        self._reconectar_servidor()

    def _crear_header(self):
        header_frame = ctk.CTkFrame(self, corner_radius=0, height=60)
        header_frame.pack(fill="x", padx=0, pady=0)

        titulo = ctk.CTkLabel(
            header_frame,
            text="🏆 MatchSport",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        titulo.pack(side="left", padx=20, pady=12)

        subtitulo = ctk.CTkLabel(
            header_frame,
            text="Partidos entre jugadores de esta red local",
            font=ctk.CTkFont(size=13),
            text_color="gray60"
        )
        subtitulo.pack(side="left", padx=5, pady=12)

        self.tema_switch = ctk.CTkSwitch(
            header_frame,
            text="Modo Oscuro",
            command=self._alternar_tema,
            onvalue="dark",
            offvalue="light"
        )
        self.tema_switch.select()
        self.tema_switch.pack(side="right", padx=15, pady=12)

        self.btn_servidor = ctk.CTkButton(
            header_frame,
            text="📡 Red Wi-Fi...",
            width=115,
            height=28,
            font=ctk.CTkFont(size=12),
            command=self._abrir_config_servidor
        )
        self.btn_servidor.pack(side="right", padx=10, pady=12)

    def _crear_cuerpo(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=15, pady=10)

        main_container.grid_columnconfigure(0, weight=4)
        main_container.grid_columnconfigure(1, weight=6)
        main_container.grid_rowconfigure(0, weight=1)

        # Panel Izquierdo
        self.panel_izq = ctk.CTkFrame(main_container, corner_radius=12)
        self.panel_izq.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)

        lbl_izq_titulo = ctk.CTkLabel(
            self.panel_izq,
            text="👤 Perfil de Jugador",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_izq_titulo.pack(anchor="w", padx=20, pady=(15, 5))

        lbl_perfil_existente = ctk.CTkLabel(
            self.panel_izq,
            text="Seleccionar jugador en esta red:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray70"
        )
        lbl_perfil_existente.pack(anchor="w", padx=20, pady=(5, 2))

        self.combo_usuarios = ctk.CTkComboBox(
            self.panel_izq,
            values=["(Nuevo perfil)"],
            command=self._al_seleccionar_usuario,
            state="readonly"
        )
        self.combo_usuarios.pack(fill="x", padx=20, pady=(0, 10))

        separador = ctk.CTkFrame(self.panel_izq, height=2, fg_color="gray30")
        separador.pack(fill="x", padx=20, pady=(0, 10))

        lbl_nombre = ctk.CTkLabel(self.panel_izq, text="Nombre del Jugador:", font=ctk.CTkFont(weight="bold"))
        lbl_nombre.pack(anchor="w", padx=20, pady=(5, 2))

        self.entry_nombre = ctk.CTkEntry(self.panel_izq, placeholder_text="Ej: Alex García")
        self.entry_nombre.pack(fill="x", padx=20, pady=(0, 12))

        lbl_deportes = ctk.CTkLabel(self.panel_izq, text="Deportes favoritos:", font=ctk.CTkFont(weight="bold"))
        lbl_deportes.pack(anchor="w", padx=20, pady=(5, 2))

        deportes_frame = ctk.CTkFrame(self.panel_izq, fg_color="transparent")
        deportes_frame.pack(fill="x", padx=20, pady=(0, 12))

        for deporte in DEPORTES_DISPONIBLES:
            var = ctk.BooleanVar(value=False)
            self.check_vars[deporte] = var
            icono = ICONOS_DEPORTE.get(deporte, "🎯")
            chk = ctk.CTkCheckBox(deportes_frame, text=f"{icono} {deporte}", variable=var)
            chk.pack(anchor="w", pady=4)

        lbl_nivel = ctk.CTkLabel(self.panel_izq, text="Nivel de Juego:", font=ctk.CTkFont(weight="bold"))
        lbl_nivel.pack(anchor="w", padx=20, pady=(5, 2))

        self.combo_nivel = ctk.CTkComboBox(self.panel_izq, values=NIVELES_DISPONIBLES, state="readonly")
        self.combo_nivel.set(NIVELES_DISPONIBLES[0])
        self.combo_nivel.pack(fill="x", padx=20, pady=(0, 20))

        self.btn_guardar = ctk.CTkButton(
            self.panel_izq,
            text="💾 Guardar Perfil en Red",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._guardar_perfil
        )
        self.btn_guardar.pack(fill="x", padx=20, pady=(5, 15))

        # Panel Derecho
        self.panel_der = ctk.CTkFrame(main_container, corner_radius=12)
        self.panel_der.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)

        header_der = ctk.CTkFrame(self.panel_der, fg_color="transparent")
        header_der.pack(fill="x", padx=15, pady=(12, 4))

        lbl_der_titulo = ctk.CTkLabel(
            header_der,
            text="🏆 Partidos de la Red",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_der_titulo.pack(side="left")

        btn_crear_partido = ctk.CTkButton(
            header_der,
            text="➕ Publicar Partido",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2fa572",
            hover_color="#1e734e",
            width=135,
            height=30,
            command=self._abrir_modal_crear_partido
        )
        btn_crear_partido.pack(side="right")

        self.tabview = ctk.CTkTabview(self.panel_der, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        self.tab_disponibles = self.tabview.add("⚽ Partidos Disponibles")
        self.tab_horarios = self.tabview.add("🕒 Horarios para Quedar")
        self.tab_mis_partidos = self.tabview.add("📅 Mis Partidos")

        self._construir_pestana_disponibles()
        self._construir_pestana_horarios()
        self._construir_pestana_mis_partidos()

    def _construir_pestana_disponibles(self):
        barra_filtros = ctk.CTkFrame(self.tab_disponibles, fg_color="transparent")
        barra_filtros.pack(fill="x", padx=10, pady=(6, 6))

        self.lbl_filtro_activo = ctk.CTkLabel(
            barra_filtros,
            text="Guarda o selecciona un perfil para ver emparejamientos compatibles.",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray70",
            wraplength=330,
            justify="left"
        )
        self.lbl_filtro_activo.pack(side="left", fill="x", expand=True)

        self.chk_solo_compatibles = ctk.CTkCheckBox(
            barra_filtros,
            text="Solo compatibles",
            variable=self.solo_compatibles_var,
            font=ctk.CTkFont(size=12),
            command=self._actualizar_partidos
        )
        self.chk_solo_compatibles.pack(side="right")

        self.scroll_disponibles = ctk.CTkScrollableFrame(self.tab_disponibles, corner_radius=8)
        self.scroll_disponibles.pack(fill="both", expand=True, padx=5, pady=(0, 5))

    def _construir_pestana_horarios(self):
        barra_franjas = ctk.CTkFrame(self.tab_horarios, fg_color="transparent")
        barra_franjas.pack(fill="x", padx=10, pady=(6, 6))

        lbl_franja = ctk.CTkLabel(barra_franjas, text="Filtrar por franja:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_franja.pack(side="left", padx=(0, 8))

        self.combo_franja = ctk.CTkComboBox(
            barra_franjas,
            values=[
                "Todos",
                "Mañanas (08:00 - 13:59)",
                "Tardes (14:00 - 19:59)",
                "Noches (20:00 - 23:59)"
            ],
            state="readonly",
            command=lambda _: self._actualizar_pestana_horarios()
        )
        self.combo_franja.set("Todos")
        self.combo_franja.pack(side="left", fill="x", expand=True)

        self.scroll_horarios = ctk.CTkScrollableFrame(self.tab_horarios, corner_radius=8)
        self.scroll_horarios.pack(fill="both", expand=True, padx=5, pady=(0, 5))

    def _construir_pestana_mis_partidos(self):
        barra_info = ctk.CTkFrame(self.tab_mis_partidos, fg_color="transparent")
        barra_info.pack(fill="x", padx=10, pady=(6, 6))

        self.lbl_mis_partidos_info = ctk.CTkLabel(
            barra_info,
            text="Partidos agendados a los que te has unido con la hora confirmada.",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray70"
        )
        self.lbl_mis_partidos_info.pack(side="left")

        self.scroll_mis_partidos = ctk.CTkScrollableFrame(self.tab_mis_partidos, corner_radius=8)
        self.scroll_mis_partidos.pack(fill="both", expand=True, padx=5, pady=(0, 5))

    def _crear_barra_estado(self):
        self.status_frame = ctk.CTkFrame(self, corner_radius=0, height=30)
        self.status_frame.pack(fill="x", side="bottom")

        self.lbl_status = ctk.CTkLabel(
            self.status_frame,
            text="Conectando...",
            font=ctk.CTkFont(size=11),
            text_color="gray70"
        )
        self.lbl_status.pack(side="left", padx=15, pady=4)

    # ==========================================================================
    # LÓGICA DE CONEXIÓN
    # ==========================================================================

    def _reconectar_servidor(self):
        online = api_check_health(self.server_url)
        self.servidor_conectado = online

        if online:
            self.lbl_status.configure(
                text=f"🟢 Conectado al Servidor MatchSport ({self.server_url})"
            )
            self._actualizar_selector_usuarios()
            self._actualizar_partidos()
        else:
            self.lbl_status.configure(
                text=f"🔴 No se encontró el servidor en {self.server_url}. Asegúrate de abrir 'iniciar_servidor.bat'."
            )
            self._limpiar_contenedor(self.scroll_disponibles)
            self._mostrar_mensaje_en_frame(
                self.scroll_disponibles,
                f"No se detecta el servidor en {self.server_url}.\n\n"
                "• En este PC: abre 'iniciar_servidor.bat'.\n"
                "• En otro PC: pulsa '📡 Red Wi-Fi...' arriba y dale a '🔍 Buscar en Wi-Fi'."
            )

    def _abrir_config_servidor(self):
        ConfigServidorDialog(
            parent=self,
            server_url=self.server_url,
            on_guardar=self._guardar_nueva_url_servidor
        )

    def _guardar_nueva_url_servidor(self, nueva_url):
        self.server_url = nueva_url
        self._reconectar_servidor()

    def _alternar_tema(self):
        modo = self.tema_switch.get()
        ctk.set_appearance_mode(modo)
        if modo == "dark":
            self.tema_switch.configure(text="Modo Oscuro")
        else:
            self.tema_switch.configure(text="Modo Claro")

    def _actualizar_selector_usuarios(self):
        usuarios = api_obtener_usuarios(self.server_url)
        self.mapa_usuarios = {}

        opciones = ["(Crear nuevo perfil)"]
        for u in usuarios:
            etiqueta = f"{u['nombre']} (#{u['id']} - {u['nivel']})"
            self.mapa_usuarios[etiqueta] = u
            opciones.append(etiqueta)

        self.combo_usuarios.configure(values=opciones)
        if len(opciones) > 1:
            self.combo_usuarios.set(opciones[1])
            self._al_seleccionar_usuario(opciones[1])
        else:
            self.combo_usuarios.set(opciones[0])

    def _al_seleccionar_usuario(self, seleccion):
        if seleccion == "(Crear nuevo perfil)" or seleccion not in self.mapa_usuarios:
            self.usuario_actual = None
            self.entry_nombre.delete(0, "end")
            for var in self.check_vars.values():
                var.set(False)
            self.combo_nivel.set(NIVELES_DISPONIBLES[0])
            self.lbl_filtro_activo.configure(
                text="Completa el formulario y pulsa 'Guardar' para registrarte en la red."
            )
            self._actualizar_partidos()
            self._actualizar_pestana_mis_partidos()
            return

        usuario = self.mapa_usuarios[seleccion]
        self.usuario_actual = dict(usuario)

        self.entry_nombre.delete(0, "end")
        self.entry_nombre.insert(0, usuario["nombre"])

        deportes_usuario = [d.strip() for d in usuario["deportes_favoritos"].split(",")]
        for dep, var in self.check_vars.items():
            var.set(dep in deportes_usuario)

        if usuario["nivel"] in NIVELES_DISPONIBLES:
            self.combo_nivel.set(usuario["nivel"])

        self._actualizar_partidos()
        self._actualizar_pestana_mis_partidos()

    def _guardar_perfil(self):
        nombre = self.entry_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Campo obligatorio", "Por favor, introduce tu nombre.")
            return

        deportes_seleccionados = [
            dep for dep, var in self.check_vars.items() if var.get()
        ]
        if not deportes_seleccionados:
            messagebox.showwarning(
                "Deportes requeridos",
                "Por favor, selecciona al menos un deporte favorito."
            )
            return

        deportes_str = ", ".join(deportes_seleccionados)
        nivel = self.combo_nivel.get()

        try:
            nuevo_user = api_crear_usuario(self.server_url, nombre, deportes_str, nivel)
            self.usuario_actual = nuevo_user
            self.lbl_status.configure(
                text=f"🟢 Perfil de '{nombre}' sincronizado en la red local ({self.server_url})."
            )
            self._actualizar_selector_usuarios()
            self._actualizar_partidos()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")

    def _abrir_modal_crear_partido(self):
        if not self.servidor_conectado and not api_check_health(self.server_url):
            messagebox.showwarning("Servidor Desconectado", "No se puede publicar: el servidor no responde en la red.")
            return

        CrearPartidoDialog(
            parent=self,
            server_url=self.server_url,
            usuario_actual=self.usuario_actual,
            al_guardar=self._al_crear_partido
        )

    def _al_crear_partido(self, partido_id, deporte, nivel, hora, plazas):
        self.lbl_status.configure(
            text=f"✅ Partido #{partido_id} de {deporte} a las {hora} publicado en la red local."
        )
        self._actualizar_partidos()
        self._actualizar_pestana_horarios()

    def _actualizar_partidos(self):
        if not self.servidor_conectado and not api_check_health(self.server_url):
            return

        solo_compatibles = self.solo_compatibles_var.get()

        if solo_compatibles and self.usuario_actual:
            user = self.usuario_actual
            deportes_str = user["deportes_favoritos"]
            nivel = user["nivel"]

            self.lbl_filtro_activo.configure(
                text=f"🎯 Filtro para {user['nombre']}: [{deportes_str}] | Nivel: {nivel}"
            )
            partidos = api_buscar_partidos(self.server_url, deportes_str, nivel)
        elif solo_compatibles and not self.usuario_actual:
            self.lbl_filtro_activo.configure(
                text="Selecciona o crea un perfil para filtrar por afinidad."
            )
            self._limpiar_contenedor(self.scroll_disponibles)
            self._mostrar_mensaje_en_frame(
                self.scroll_disponibles,
                "Crea o selecciona un perfil a la izquierda, o desmarca 'Solo compatibles'."
            )
            self._actualizar_pestana_horarios()
            return
        else:
            self.lbl_filtro_activo.configure(
                text="🌐 Mostrando todos los partidos disponibles en la red local."
            )
            partidos = api_buscar_partidos(self.server_url)

        self._limpiar_contenedor(self.scroll_disponibles)

        if not partidos:
            self._mostrar_mensaje_en_frame(
                self.scroll_disponibles,
                "No hay partidos disponibles con los criterios actuales.\n"
                "¡Sé el primero en publicar uno con '➕ Publicar Partido'!"
            )
        else:
            for partido in partidos:
                self._crear_tarjeta_partido(self.scroll_disponibles, partido)

        self._actualizar_pestana_horarios()

    def _actualizar_pestana_horarios(self):
        if not self.servidor_conectado and not api_check_health(self.server_url):
            return

        franja = self.combo_franja.get() if hasattr(self, "combo_franja") else "Todos"
        partidos = api_buscar_partidos(self.server_url, franja=franja)

        self._limpiar_contenedor(self.scroll_horarios)

        if not partidos:
            self._mostrar_mensaje_en_frame(
                self.scroll_horarios,
                f"No hay partidos programados en la franja ({franja})."
            )
            return

        for partido in partidos:
            self._crear_tarjeta_partido(self.scroll_horarios, partido)

    def _actualizar_pestana_mis_partidos(self):
        self._limpiar_contenedor(self.scroll_mis_partidos)

        if not self.usuario_actual:
            self._mostrar_mensaje_en_frame(
                self.scroll_mis_partidos,
                "Selecciona o crea un perfil para ver tus quedadas agendadas."
            )
            return

        mis_partidos = api_obtener_mis_partidos(self.server_url, self.usuario_actual["id"])

        if not mis_partidos:
            self._mostrar_mensaje_en_frame(
                self.scroll_mis_partidos,
                f"¡Hola {self.usuario_actual['nombre']}! Aún no te has unido a ningún partido.\n"
                "Explora los partidos disponibles o por horarios y únete a uno."
            )
            return

        for partido in mis_partidos:
            self._crear_tarjeta_mi_partido(self.scroll_mis_partidos, partido)

    def _limpiar_contenedor(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def _mostrar_mensaje_en_frame(self, frame, texto):
        lbl = ctk.CTkLabel(
            frame,
            text=f"ℹ️ {texto}",
            font=ctk.CTkFont(size=13),
            text_color="gray60"
        )
        lbl.pack(pady=40)

    def _crear_tarjeta_partido(self, parent_frame, partido):
        card = ctk.CTkFrame(parent_frame, corner_radius=10, fg_color=("gray85", "gray20"))
        card.pack(fill="x", padx=5, pady=6)

        deporte = partido["deporte"]
        icono = ICONOS_DEPORTE.get(deporte, "🏆")

        header_card = ctk.CTkFrame(card, fg_color="transparent")
        header_card.pack(fill="x", padx=12, pady=(10, 4))

        lbl_deporte = ctk.CTkLabel(
            header_card,
            text=f"{icono} {deporte}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        lbl_deporte.pack(side="left")

        lbl_hora = ctk.CTkLabel(
            header_card,
            text=f"🕒 Quedada a las {partido['hora']}",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1f538d",
            corner_radius=6,
            text_color="white",
            padx=10,
            pady=3
        )
        lbl_hora.pack(side="left", padx=12)

        plazas = partido["plazas_disponibles"]
        badge_color = "#2fa572" if plazas > 1 else "#e58e26"
        lbl_plazas = ctk.CTkLabel(
            header_card,
            text=f"👥 {plazas} plazas libres",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=badge_color
        )
        lbl_plazas.pack(side="right")

        detalles_frame = ctk.CTkFrame(card, fg_color="transparent")
        detalles_frame.pack(fill="x", padx=12, pady=(0, 10))

        creador_txt = f"  |  👤 Org: {partido['creador_nombre']}" if partido.get("creador_nombre") else ""
        lbl_info = ctk.CTkLabel(
            detalles_frame,
            text=f"🏅 Nivel requerido: {partido['nivel_requerido']}{creador_txt}",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        lbl_info.pack(side="left")

        btn_unirse = ctk.CTkButton(
            detalles_frame,
            text="Unirse al Partido",
            width=135,
            height=28,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144870",
            command=lambda pid=partido["id"], dep=deporte, h=partido["hora"]: self._unirse(pid, dep, h)
        )
        btn_unirse.pack(side="right")

    def _crear_tarjeta_mi_partido(self, parent_frame, partido):
        card = ctk.CTkFrame(parent_frame, corner_radius=10, fg_color=("gray85", "gray22"))
        card.pack(fill="x", padx=5, pady=6)

        deporte = partido["deporte"]
        icono = ICONOS_DEPORTE.get(deporte, "🏆")

        header_card = ctk.CTkFrame(card, fg_color="transparent")
        header_card.pack(fill="x", padx=12, pady=(10, 4))

        lbl_deporte = ctk.CTkLabel(
            header_card,
            text=f"{icono} {deporte}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        lbl_deporte.pack(side="left")

        lbl_hora = ctk.CTkLabel(
            header_card,
            text=f"🕒 Quedada confirmada: {partido['hora']}",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2fa572",
            corner_radius=6,
            text_color="white",
            padx=10,
            pady=3
        )
        lbl_hora.pack(side="left", padx=12)

        lbl_estado = ctk.CTkLabel(
            header_card,
            text="✅ ¡Apuntado!",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2fa572"
        )
        lbl_estado.pack(side="right")

        detalles_frame = ctk.CTkFrame(card, fg_color="transparent")
        detalles_frame.pack(fill="x", padx=12, pady=(0, 10))

        creador_txt = f"  |  👤 Org: {partido['creador_nombre']}" if partido.get("creador_nombre") else ""
        lbl_info = ctk.CTkLabel(
            detalles_frame,
            text=f"🏅 Nivel: {partido['nivel_requerido']}{creador_txt}  |  👥 Plazas restantes: {partido['plazas_disponibles']}",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        lbl_info.pack(side="left")

    def _unirse(self, partido_id, deporte, hora):
        user_id = self.usuario_actual["id"] if self.usuario_actual else None
        exito = api_unirse_partido(self.server_url, partido_id, user_id)
        if exito:
            self.lbl_status.configure(
                text=f"✅ ¡Te has unido al partido de {deporte} a las {hora}! Sincronizado en la red local."
            )
            self._actualizar_partidos()
            self._actualizar_pestana_mis_partidos()
        else:
            messagebox.showinfo("Aviso", "No quedan plazas disponibles o el servidor no respondió.")
            self._actualizar_partidos()

# ==============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# ==============================================================================

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    app = MatchSportApp()
    app.mainloop()

