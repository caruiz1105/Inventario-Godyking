from flask import Flask, render_template, request, redirect, flash
import pandas as pd
import sqlite3

from db_supabase import *


app = Flask(__name__)

app.secret_key = "inventario-chips-secret"

# ==========================================
# INICIO
# ==========================================

@app.route("/")
def inicio():

    return render_template("inicio.html")


# ==========================================
# CHIPS
# ==========================================

@app.route("/chips")
def chips():

    conn = get_connection()

    chips = conn.execute("""
    SELECT
        c.id,
        c.iccid,
        c.estado,
        e.fecha_entrega,
        p.nombre AS persona,
        p.activo AS persona_activo
    FROM chips c
    LEFT JOIN entregas e
        ON e.id = (
            SELECT MAX(e2.id)
            FROM entregas e2
            WHERE e2.chip_id = c.id
        )
    LEFT JOIN personas p
        ON p.id = e.persona_id
    ORDER BY c.id
""").fetchall()


    # Total de chips

    total = conn.execute("""
        SELECT COUNT(*)
        FROM chips
    """).fetchone()[0]


    # Chips disponibles

    disponibles = conn.execute("""
        SELECT COUNT(*)
        FROM chips
        WHERE estado = 'Disponible'
    """).fetchone()[0]


    # Chips entregados

    entregados = conn.execute("""
        SELECT COUNT(*)
        FROM chips
        WHERE estado = 'Entregado'
    """).fetchone()[0]

    # Chips devueltos
    devueltos = conn.execute("""
        SELECT COUNT(*)
        FROM chips
        WHERE estado = 'Devuelto'
    """).fetchone()[0]


    # Personas habilitadas

    personas = conn.execute("""
        SELECT *
        FROM personas
        WHERE activo = 1
        ORDER BY nombre
    """).fetchall()


    conn.close()


    return render_template(
        "chips.html",

        chips=chips,

        total=total,

        disponibles=disponibles,

        entregados=entregados,

        personas=personas,

        devueltos=devueltos
    )


# ==========================================
# ENTREGAR CHIP
# ==========================================

@app.route("/entregar", methods=["POST"])
def entregar():

    chip_id = request.form.get("chip_id")
    persona_id = request.form.get("persona_id")
    fecha = request.form.get("fecha")

    # Validar datos
    if not chip_id or not persona_id or not fecha:
        flash("Completa todos los campos.")
        return redirect("/chips")

    conn = get_connection()

    # Buscar chip
    chip = conn.execute("""
        SELECT * FROM chips WHERE id = ?
    """, (chip_id,)).fetchone()

    if not chip:
        conn.close()
        flash("El chip no existe.")
        return redirect("/chips")

    # Verificar disponibilidad (ahora permite Disponible o Devuelto)
    if chip["estado"] not in ["Disponible", "Devuelto"]:
        conn.close()
        flash("Este chip no está disponible para entregar.")
        return redirect("/chips")

    # Verificar persona
    persona = conn.execute("""
        SELECT * FROM personas WHERE id = ? AND activo = 1
    """, (persona_id,)).fetchone()

    if not persona:
        conn.close()
        flash("La persona no existe o está deshabilitada.")
        return redirect("/chips")

    # Registrar entrega
    conn.execute("""
        INSERT INTO entregas (chip_id, persona_id, fecha_entrega)
        VALUES (?, ?, ?)
    """, (chip_id, persona_id, fecha))

    # Cambiar estado a Entregado
    conn.execute("""
        UPDATE chips SET estado = 'Entregado' WHERE id = ?
    """, (chip_id,))

    conn.commit()
    conn.close()

    flash("Chip entregado correctamente.")
    return redirect("/chips")
# ==========================================
# DEVOLVER CHIP
# ==========================================

@app.route("/devolver/<int:chip_id>", methods=["POST"])
def devolver_chip(chip_id):
    """Cambiar estado de un chip a Devuelto"""
    
    conn = get_connection()
    
    # Verificar que el chip existe y está entregado
    chip = conn.execute("""
        SELECT estado FROM chips WHERE id = ?
    """, (chip_id,)).fetchone()
    
    if not chip:
        conn.close()
        flash("El chip no existe.")
        return redirect("/chips")
    
    if chip["estado"] != "Entregado":
        conn.close()
        flash("Este chip no está entregado.")
        return redirect("/chips")
    
    # Cambiar estado a 'Devuelto'
    conn.execute("""
        UPDATE chips
        SET estado = 'Devuelto'
        WHERE id = ?
    """, (chip_id,))
    
    conn.commit()
    conn.close()
    
    flash("Chip marcado como devuelto correctamente.")
    return redirect("/chips")

# ==========================================
# ELIMINAR CHIP
# ==========================================

@app.route("/eliminar/<int:chip_id>", methods=["POST"])
def eliminar_chip(chip_id):
    """Eliminar un chip permanentemente (solo si está Devuelto)"""
    
    conn = get_connection()
    
    chip = conn.execute("""
        SELECT estado FROM chips WHERE id = ?
    """, (chip_id,)).fetchone()
    
    if not chip:
        conn.close()
        flash("El chip no existe.")
        return redirect("/chips")
    
    if chip["estado"] != "Devuelto":
        conn.close()
        flash("Solo se pueden eliminar chips en estado 'Devuelto'.")
        return redirect("/chips")
    
    # Eliminar el chip
    conn.execute("DELETE FROM chips WHERE id = ?", (chip_id,))
    conn.commit()
    conn.close()
    
    flash("Chip eliminado permanentemente.")
    return redirect("/chips")

# ==========================================
# CELULARES 
# ==========================================

@app.route("/celulares")
def celulares():
    """Página de gestión de celulares"""
    conn = get_connection()

    celulares = conn.execute("""
        SELECT
            c.id,
            c.imei,
            c.modelo,
            c.marca,
            c.estado
        FROM celulares c
        ORDER BY c.id
    """).fetchall()

    total = conn.execute("SELECT COUNT(*) FROM celulares").fetchone()[0]
    disponibles = conn.execute("SELECT COUNT(*) FROM celulares WHERE estado = 'Disponible'").fetchone()[0]
    reservados = conn.execute("SELECT COUNT(*) FROM celulares WHERE estado = 'Reservado'").fetchone()[0]
    vendidos = conn.execute("SELECT COUNT(*) FROM celulares WHERE estado = 'Vendido'").fetchone()[0]

    conn.close()

    return render_template(
        "celulares.html",
        celulares=celulares,
        total=total,
        disponibles=disponibles,
        reservados=reservados,
        vendidos=vendidos
    )


@app.route("/celulares/agregar", methods=["POST"])
def agregar_celular():
    """Agregar un celular manualmente"""
    imei = request.form.get("imei", "").strip()
    modelo = request.form.get("modelo", "").strip()
    marca = request.form.get("marca", "").strip()

    if not imei or not modelo or not marca:
        flash("Todos los campos son obligatorios.")
        return redirect("/celulares")

    conn = get_connection()

    try:
        conn.execute("""
            INSERT INTO celulares (imei, modelo, marca, estado)
            VALUES (?, ?, ?, 'Disponible')
        """, (imei, modelo, marca))
        conn.commit()
        flash(f"✅ Celular {modelo} ({imei}) agregado correctamente.")
    except sqlite3.IntegrityError:
        flash(f"❌ El IMEI {imei} ya existe.")
    except Exception as e:
        flash(f"❌ Error al agregar: {str(e)}")
    finally:
        conn.close()

    return redirect("/celulares")


@app.route("/celulares/reservar/<int:celular_id>", methods=["POST"])
def reservar_celular(celular_id):
    """Cambiar estado de un celular a Reservado"""
    conn = get_connection()

    celular = conn.execute("""
        SELECT estado FROM celulares WHERE id = ?
    """, (celular_id,)).fetchone()

    if not celular:
        conn.close()
        flash("❌ El celular no existe.")
        return redirect("/celulares")

    if celular["estado"] != "Disponible":
        conn.close()
        flash(f"❌ El celular está '{celular['estado']}', no se puede reservar.")
        return redirect("/celulares")

    conn.execute("""
        UPDATE celulares SET estado = 'Reservado' WHERE id = ?
    """, (celular_id,))

    conn.commit()
    conn.close()

    flash("✅ Celular reservado correctamente.")
    return redirect("/celulares")


@app.route("/celulares/vender/<int:celular_id>", methods=["POST"])
def vender_celular(celular_id):
    """Cambiar estado de un celular a Vendido"""
    conn = get_connection()

    celular = conn.execute("""
        SELECT estado FROM celulares WHERE id = ?
    """, (celular_id,)).fetchone()

    if not celular:
        conn.close()
        flash("❌ El celular no existe.")
        return redirect("/celulares")

    if celular["estado"] not in ["Disponible", "Reservado"]:
        conn.close()
        flash(f"❌ El celular está '{celular['estado']}', no se puede vender.")
        return redirect("/celulares")

    conn.execute("""
        UPDATE celulares SET estado = 'Vendido' WHERE id = ?
    """, (celular_id,))

    conn.commit()
    conn.close()

    flash("✅ Celular marcado como vendido.")
    return redirect("/celulares")


@app.route("/celulares/cancelar_reserva/<int:celular_id>", methods=["POST"])
def cancelar_reserva(celular_id):
    """Cancelar reserva de un celular (vuelve a Disponible)"""
    conn = get_connection()

    celular = conn.execute("""
        SELECT estado FROM celulares WHERE id = ?
    """, (celular_id,)).fetchone()

    if not celular:
        conn.close()
        flash("❌ El celular no existe.")
        return redirect("/celulares")

    if celular["estado"] != "Reservado":
        conn.close()
        flash(f"❌ El celular está '{celular['estado']}', no tiene reserva activa.")
        return redirect("/celulares")

    conn.execute("""
        UPDATE celulares SET estado = 'Disponible' WHERE id = ?
    """, (celular_id,))

    conn.commit()
    conn.close()

    flash("✅ Reserva cancelada. El celular vuelve a estar disponible.")
    return redirect("/celulares")

@app.route("/celulares/eliminar/<int:celular_id>", methods=["POST"])
def eliminar_celular(celular_id):
    """Eliminar un celular permanentemente (solo si está Disponible)"""
    conn = get_connection()

    celular = conn.execute("""
        SELECT estado FROM celulares WHERE id = ?
    """, (celular_id,)).fetchone()

    if not celular:
        conn.close()
        flash("❌ El celular no existe.")
        return redirect("/celulares")

    # Solo permite eliminar si está Disponible
    if celular["estado"] != "Disponible":
        conn.close()
        flash(f"❌ No se puede eliminar. El celular está '{celular['estado']}'.")
        return redirect("/celulares")

    # Eliminar el celular
    conn.execute("DELETE FROM celulares WHERE id = ?", (celular_id,))
    conn.commit()
    conn.close()

    flash("✅ Celular eliminado permanentemente.")
    return redirect("/celulares")

# ==========================================
# IMPORTAR EXCEL
# ==========================================

@app.route("/importar", methods=["POST"])
def importar_excel():

    archivo = request.files.get("archivo")


    if not archivo:

        flash("No seleccionaste ningún archivo.")

        return redirect("/chips")


    try:

        # Leer Excel como texto
        df = pd.read_excel(
            archivo,
            dtype=str
        )


        if df.empty:

            flash("El archivo Excel está vacío.")

            return redirect("/chips")


        # Primera columna = ICCID
        columna_iccid = df.columns[0]


        conn = get_connection()


        nuevos = 0

        duplicados = 0


        for valor in df[columna_iccid]:

            if pd.isna(valor):

                continue


            iccid = str(valor).strip()


            if not iccid:

                continue


            try:

                conn.execute("""
                    INSERT INTO chips (
                        iccid,
                        estado
                    )

                    VALUES (?, 'Disponible')
                """, (iccid,))


                nuevos += 1


            except sqlite3.IntegrityError:

                duplicados += 1


            except Exception:

                duplicados += 1


        conn.commit()

        conn.close()


        flash(
            f"Importación completada. "
            f"Nuevos: {nuevos}. "
            f"Duplicados: {duplicados}."
        )


    except Exception as error:

        print("ERROR:", error)

        flash(
            "Ocurrió un error al importar el Excel."
        )


    return redirect("/chips")

# ==========================================
# GESTIÓN DE PERSONAS
# ==========================================

@app.route("/personas")
def personas():
    """Página de gestión de personas"""
    conn = get_connection()
    
    # Obtener todas las personas (habilitadas y deshabilitadas)
    personas = conn.execute("""
        SELECT id, nombre, activo
        FROM personas
        ORDER BY nombre
    """).fetchall()
    
    conn.close()
    
    return render_template("personas.html", personas=personas)


@app.route("/personas/toggle/<int:persona_id>", methods=["POST"])
def toggle_persona(persona_id):
    """Habilitar o deshabilitar una persona"""
    conn = get_connection()
    
    # Obtener estado actual
    persona = conn.execute("""
        SELECT activo FROM personas WHERE id = ?
    """, (persona_id,)).fetchone()
    
    if not persona:
        conn.close()
        flash("La persona no existe.")
        return redirect("/personas")
    
    # Cambiar estado (si está activo -> 0, si está inactivo -> 1)
    nuevo_estado = 0 if persona["activo"] == 1 else 1
    
    conn.execute("""
        UPDATE personas
        SET activo = ?
        WHERE id = ?
    """, (nuevo_estado, persona_id))
    
    conn.commit()
    conn.close()
    
    estado_texto = "habilitada" if nuevo_estado == 1 else "deshabilitada"
    flash(f"Persona {estado_texto} correctamente.")
    
    return redirect("/personas")


@app.route("/personas/agregar", methods=["POST"])
def agregar_persona():
    """Agregar una nueva persona"""
    nombre = request.form.get("nombre", "").strip()
    
    if not nombre:
        flash("El nombre es obligatorio.")
        return redirect("/personas")
    
    conn = get_connection()
    
    try:
        conn.execute("""
            INSERT INTO personas (nombre, activo)
            VALUES (?, 1)
        """, (nombre,))
        conn.commit()
        flash(f"Persona '{nombre}' agregada correctamente.")
    except sqlite3.IntegrityError:
        flash(f"La persona '{nombre}' ya existe.")
    except Exception as e:
        flash(f"Error al agregar: {str(e)}")
    finally:
        conn.close()
    
    return redirect("/personas")


# ==========================================
# EJECUTAR SERVIDOR
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )