from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import pyodbc
import datetime
import re
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = 'clave_secreta_seguridad_ascension'

CONN_STR = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=DESKTOP-49EPOO1;"
    "Database=SeguridadCiudadana;"
    "Trusted_Connection=yes;"
)

# --- 1. LOGIN Y SEGURIDAD ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form['username']
        psw_input = request.form['password']
        
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT PasswordHash FROM Usuarios WHERE Username = ?", (user_input,))
        user_db = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_db and check_password_hash(user_db[0], psw_input):
            session['user'] = user_input
            return redirect(url_for('index_principal'))
        return "Usuario o contraseña incorrectos"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# --- 2. RUTA PRINCIPAL (PROTEGIDA) ---
@app.route('/')
def index_principal():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    ahora_servidor = datetime.datetime.now()
    turno_actual = obtener_turno_automatico(ahora_servidor)
    fecha_pantalla = ahora_servidor.strftime("%d/%m/%Y %H:%M:%S")
    codigo_auto = obtener_siguiente_codigo()
    return render_template('index.html', turno=turno_actual, fecha_hora=fecha_pantalla, codigo_siguiente=codigo_auto)

# --- 3. FUNCIONES DE APOYO ---
def obtener_siguiente_codigo():
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT Codigo FROM PatrullajeAreasPriorizadas")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        max_numero = 92
        for row in rows:
            if row[0]:
                numeros = re.findall(r'\d+', str(row[0]))
                if numeros:
                    valor_num = int(numeros[-1])
                    if valor_num > max_numero:
                        max_numero = valor_num
        return f"SC-MDA-{str(max_numero + 1).zfill(3)}"
    except:
        return "SC-MDA-093"

def obtener_turno_automatico(hora_evaluar):
    hora = hora_evaluar.time()
    if datetime.time(6, 0) <= hora < datetime.time(14, 0): return "MAÑANA"
    if datetime.time(14, 0) <= hora < datetime.time(22, 0): return "TARDE"
    return "NOCHE"

@app.route('/api/patrullaje', methods=['POST'])
def registrar_patrullaje():
    if 'user' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    data = request.json
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        query = """INSERT INTO PatrullajeAreasPriorizadas (Codigo, Fecha_Hora, Tipo_Patrullaje, Sector_SubSector, Modalidad_Patrullaje, Turno, Latitud, Longitud, Altitud, Precision_Metros, Imagen_Evidencia, Observaciones)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        cursor.execute(query, (obtener_siguiente_codigo(), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                               data.get('Tipo_Patrullaje'), data.get('Sector_SubSector'), data.get('Modalidad_Patrullaje'), 
                               obtener_turno_automatico(datetime.datetime.now()), data.get('Latitud', 0), data.get('Longitud', 0), 
                               3680.0, 5.0, data.get('Imagen_Evidencia', 'pendiente.jpg'), data.get('Observaciones', '')))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "éxito"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)