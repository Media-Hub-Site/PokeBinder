from sqlalchemy.exc import IntegrityError
from MyQtApp.session import SessionLocal
from MyQtApp.models import UsuarioCarta, Cartas

def agregar_cartas_usuario(usuario_nombre, cartas_info):
    """
    Agrega una lista de cartas a un usuario específico indicando su id_api e idioma.
    cartas_info puede ser una lista de dicts [{'id_api': ..., 'idioma': ...}], tuplas (id_api, idioma), o cadenas id_api.
    Retorna la cantidad de cartas agregadas con éxito.
    """
    exitos = 0
    session = SessionLocal()
    try:
        for item in cartas_info:
            if isinstance(item, dict):
                carta_id = item.get("id_api")
                idioma = item.get("idioma", "es")
            elif isinstance(item, (tuple, list)):
                carta_id = item[0]
                idioma = item[1] if len(item) > 1 else "es"
            else:
                carta_id = str(item)
                idioma = "es"

            if not carta_id:
                continue

            # Verificar si ya existe esa carta en el idioma específico
            existe = session.query(UsuarioCarta).filter_by(
                usuario_nombre=usuario_nombre, carta_id=carta_id, idioma=idioma
            ).first()
            
            if not existe:
                nueva_carta = UsuarioCarta(usuario_nombre=usuario_nombre, carta_id=carta_id, idioma=idioma)
                session.add(nueva_carta)
                exitos += 1
                
        session.commit()
    except Exception as e:
        print(f"Error al agregar cartas: {e}")
        session.rollback()
    finally:
        session.close()
        
    return exitos

def eliminar_cartas_usuario(usuario_nombre, cartas_info):
    """
    Elimina una lista de cartas del inventario de un usuario específico respetando idioma.
    Retorna la cantidad de cartas eliminadas.
    """
    eliminados = 0
    session = SessionLocal()
    try:
        for item in cartas_info:
            if isinstance(item, dict):
                carta_id = item.get("id_api")
                idioma = item.get("idioma")
            elif isinstance(item, (tuple, list)):
                carta_id = item[0]
                idioma = item[1] if len(item) > 1 else None
            else:
                carta_id = str(item)
                idioma = None

            if not carta_id:
                continue

            q = session.query(UsuarioCarta).filter_by(usuario_nombre=usuario_nombre, carta_id=carta_id)
            if idioma:
                q = q.filter_by(idioma=idioma)
            
            registro = q.first()
            if registro:
                session.delete(registro)
                eliminados += 1
                
        session.commit()
    except Exception as e:
        print(f"Error al eliminar cartas: {e}")
        session.rollback()
    finally:
        session.close()
        
    return eliminados

def obtener_cartas_usuario(usuario_nombre):
    """
    Retorna todas las relaciones UsuarioCarta de un usuario.
    """
    session = SessionLocal()
    try:
        return session.query(UsuarioCarta).filter_by(usuario_nombre=usuario_nombre).all()
    finally:
        session.close()
