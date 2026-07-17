from sqlalchemy.exc import IntegrityError
from MyQtApp.session import SessionLocal
from MyQtApp.models import UsuarioCarta, Cartas

def agregar_cartas_usuario(usuario_nombre, cartas_ids):
    """
    Agrega una lista de IDs de cartas a un usuario específico.
    Retorna la cantidad de cartas agregadas con éxito.
    """
    exitos = 0
    session = SessionLocal()
    try:
        for carta_id in cartas_ids:
            # Verificar si ya existe
            existe = session.query(UsuarioCarta).filter_by(
                usuario_nombre=usuario_nombre, carta_id=carta_id
            ).first()
            
            if not existe:
                nueva_carta = UsuarioCarta(usuario_nombre=usuario_nombre, carta_id=carta_id)
                session.add(nueva_carta)
                exitos += 1
                
        session.commit()
    except Exception as e:
        print(f"Error al agregar cartas: {e}")
        session.rollback()
    finally:
        session.close()
        
    return exitos

def eliminar_cartas_usuario(usuario_nombre, cartas_ids):
    """
    Elimina una lista de IDs de cartas del inventario de un usuario específico.
    Retorna la cantidad de cartas eliminadas.
    """
    eliminados = 0
    session = SessionLocal()
    try:
        for carta_id in cartas_ids:
            # Buscar y borrar (sin hardcoded raw sql)
            registro = session.query(UsuarioCarta).filter_by(
                usuario_nombre=usuario_nombre, carta_id=carta_id
            ).first()
            
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
