import sqlite3
import os

DATABASE = "data/inventario.db"


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def devolver_chip(chip_id):
    """Cambia el estado de un chip a 'Devuelto'"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar que el chip existe y está entregado
        cursor.execute('SELECT estado FROM chips WHERE id = ?', (chip_id,))
        chip = cursor.fetchone()
        
        if not chip:
            return False, "El chip no existe"
        
        if chip['estado'] != 'Entregado':
            return False, "El chip no está entregado, no se puede devolver"
        
        # Cambiar estado a 'Devuelto'
        cursor.execute('''
            UPDATE chips 
            SET estado = 'Devuelto' 
            WHERE id = ?
        ''', (chip_id,))
        
        conn.commit()
        return True, "Chip devuelto correctamente"
    
    except Exception as e:
        conn.rollback()
        return False, f"Error al devolver: {str(e)}"
    finally:
        conn.close()


def inicializar_bd():

    os.makedirs("data", exist_ok=True)

    conn = get_connection()

    # Tabla de personas
    conn.execute("""
        CREATE TABLE IF NOT EXISTS personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            activo INTEGER NOT NULL DEFAULT 1
        )
    """)

    # Tabla de chips
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            iccid TEXT UNIQUE NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Disponible'
        )
    """)

    # Tabla de entrega de chips
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entregas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chip_id INTEGER NOT NULL,
            persona_id INTEGER NOT NULL,
            fecha_entrega TEXT NOT NULL,

            FOREIGN KEY (chip_id)
                REFERENCES chips(id),

            FOREIGN KEY (persona_id)
                REFERENCES personas(id)
        )
    """)

    # ====== NUEVA TABLA DE CELULARES ======
    conn.execute("""
        CREATE TABLE IF NOT EXISTS celulares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imei TEXT UNIQUE NOT NULL,
            modelo TEXT NOT NULL,
            marca TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Disponible'
        )
    """)

    # ====== NUEVA TABLA DE ENTREGAS DE CELULARES ======
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entregas_celulares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            celular_id INTEGER NOT NULL,
            persona_id INTEGER NOT NULL,
            fecha_entrega TEXT NOT NULL,
            FOREIGN KEY (celular_id) REFERENCES celulares(id),
            FOREIGN KEY (persona_id) REFERENCES personas(id)
        )
    """)

    # Personas iniciales
    personas = [
        "Antonio",
        "Carlos",
        "Cristhian",
        "Esther",
        "Jhon",
        "Juan Carlos",
        "Kelly",
        "Maria",
        "Renzo",
        "Syomara",
        "Yoder"
    ]

    # Solo agrega las personas que todavía no existen
    for nombre in personas:
        conn.execute("""
            INSERT OR IGNORE INTO personas (nombre)
            VALUES (?)
        """, (nombre,))

    conn.commit()
    conn.close()
    
    