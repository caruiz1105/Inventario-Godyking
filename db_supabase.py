import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Obtener la URL de Supabase desde las variables de entorno
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    """Obtiene una conexión a Supabase"""
    if not DATABASE_URL:
        raise Exception("DATABASE_URL no configurada en variables de entorno")
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def obtener_personas_activas():
    """Obtiene todas las personas activas"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM personas WHERE activo = 1 ORDER BY nombre')
    personas = cursor.fetchall()
    conn.close()
    return personas

def obtener_todas_personas():
    """Obtiene todas las personas (incluyendo desactivadas)"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM personas ORDER BY nombre')
    personas = cursor.fetchall()
    conn.close()
    return personas

def obtener_chips():
    """Obtiene todos los chips con su información de entrega"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('''
        SELECT 
            c.id,
            c.iccid,
            c.estado,
            e.fecha_entrega,
            p.nombre as persona,
            p.activo as persona_activo
        FROM chips c
        LEFT JOIN entregas e ON c.id = e.chip_id
        LEFT JOIN personas p ON e.persona_id = p.id
        ORDER BY c.id
    ''')
    chips = cursor.fetchall()
    conn.close()
    return chips

def contar_chips():
    """Cuenta total de chips"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM chips')
    total = cursor.fetchone()[0]
    conn.close()
    return total

def contar_chips_estado(estado):
    """Cuenta chips por estado"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM chips WHERE estado = %s', (estado,))
    total = cursor.fetchone()[0]
    conn.close()
    return total

def importar_iccid(iccid):
    """Importa un ICCID a la base de datos"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO chips (iccid, estado)
            VALUES (%s, 'Disponible')
            ON CONFLICT (iccid) DO NOTHING
        ''', (iccid,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al importar {iccid}: {e}")
        return False
    finally:
        conn.close()

def buscar_iccid(termino):
    """Busca ICCID por los últimos dígitos"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('''
        SELECT 
            c.id,
            c.iccid,
            c.estado,
            e.fecha_entrega,
            p.nombre as persona,
            p.activo as persona_activo
        FROM chips c
        LEFT JOIN entregas e ON c.id = e.chip_id
        LEFT JOIN personas p ON e.persona_id = p.id
        WHERE c.iccid LIKE %s
        ORDER BY c.id
    ''', (f'%{termino}',))
    resultados = cursor.fetchall()
    conn.close()
    return resultados

def entregar_chip(chip_id, persona_id, fecha):
    """Registra la entrega de un chip"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Verificar que el chip existe y está disponible
        cursor.execute('SELECT estado FROM chips WHERE id = %s', (chip_id,))
        chip = cursor.fetchone()
        if not chip:
            return False, "El chip no existe"
        if chip[0] != 'Disponible':
            return False, "Este chip ya fue entregado"
        
        # Verificar persona activa
        cursor.execute('SELECT activo FROM personas WHERE id = %s', (persona_id,))
        persona = cursor.fetchone()
        if not persona:
            return False, "La persona no existe"
        if persona[0] != 1:
            return False, "La persona está deshabilitada"
        
        # Registrar entrega
        cursor.execute('''
            INSERT INTO entregas (chip_id, persona_id, fecha_entrega)
            VALUES (%s, %s, %s)
        ''', (chip_id, persona_id, fecha))
        
        # Actualizar estado
        cursor.execute('''
            UPDATE chips SET estado = 'Entregado' WHERE id = %s
        ''', (chip_id,))
        
        conn.commit()
        return True, "Chip entregado exitosamente"
    except Exception as e:
        conn.rollback()
        return False, f"Error al entregar: {str(e)}"
    finally:
        conn.close()

def devolver_chip(chip_id):
    """Cambia el estado de un chip a 'Devuelto'"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT estado FROM chips WHERE id = %s', (chip_id,))
        chip = cursor.fetchone()
        if not chip:
            return False, "El chip no existe"
        if chip[0] != 'Entregado':
            return False, "El chip no está entregado"
        
        cursor.execute('UPDATE chips SET estado = %s WHERE id = %s', ('Devuelto', chip_id))
        conn.commit()
        return True, "Chip devuelto correctamente"
    except Exception as e:
        conn.rollback()
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

# ========================
# FUNCIONES PARA CELULARES
# ========================

def obtener_celulares():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('''
        SELECT c.id, c.imei, c.modelo, c.marca, c.estado
        FROM celulares c
        ORDER BY c.id
    ''')
    celulares = cursor.fetchall()
    conn.close()
    return celulares

def contar_celulares():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM celulares')
    total = cursor.fetchone()[0]
    conn.close()
    return total

def contar_celulares_estado(estado):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM celulares WHERE estado = %s', (estado,))
    total = cursor.fetchone()[0]
    conn.close()
    return total

def agregar_celular(imei, modelo, marca):
    """Agrega un nuevo celular"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO celulares (imei, modelo, marca, estado)
            VALUES (%s, %s, %s, 'Disponible')
        ''', (imei, modelo, marca))
        conn.commit()
        return True, "Celular agregado correctamente"
    except Exception as e:
        conn.rollback()
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def cambiar_estado_celular(celular_id, nuevo_estado):
    """Cambia el estado de un celular"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT estado FROM celulares WHERE id = %s', (celular_id,))
        celular = cursor.fetchone()
        if not celular:
            return False, "El celular no existe"
        
        cursor.execute('UPDATE celulares SET estado = %s WHERE id = %s', (nuevo_estado, celular_id))
        conn.commit()
        return True, f"Estado cambiado a '{nuevo_estado}'"
    except Exception as e:
        conn.rollback()
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def eliminar_celular(celular_id):
    """Elimina un celular (solo si está Disponible)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT estado FROM celulares WHERE id = %s', (celular_id,))
        celular = cursor.fetchone()
        if not celular:
            return False, "El celular no existe"
        if celular[0] != 'Disponible':
            return False, f"No se puede eliminar. El celular está '{celular[0]}'"
        
        cursor.execute('DELETE FROM celulares WHERE id = %s', (celular_id,))
        conn.commit()
        return True, "Celular eliminado correctamente"
    except Exception as e:
        conn.rollback()
        return False, f"Error: {str(e)}"
    finally:
        conn.close()