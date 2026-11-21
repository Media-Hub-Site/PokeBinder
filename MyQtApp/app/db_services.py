from sqlalchemy.exc import IntegrityError
from MyQtApp.session import SessionLocal
from MyQtApp.models import UsuarioCarta, Cartas, Categoria

def agregar_cartas_usuario(usuario_nombre, cartas_info, categoria=None):
    """
    Agrega una lista de cartas a un usuario específico indicando su id_api e idioma.
    cartas_info puede ser una lista de dicts [{'id_api': ..., 'idioma': ...}], tuplas (id_api, idioma), o cadenas id_api.
    categoria: nombre opcional de la categoría asignada.
    Retorna la cantidad de cartas agregadas con éxito.
    """
    exitos = 0
    session = SessionLocal()
    try:
        for item in cartas_info:
            if isinstance(item, dict):
                carta_id = item.get("id_api")
                idioma = item.get("idioma", "es")
                item_cat = item.get("categoria", categoria)
            elif isinstance(item, (tuple, list)):
                carta_id = item[0]
                idioma = item[1] if len(item) > 1 else "es"
                item_cat = categoria
            else:
                carta_id = str(item)
                idioma = "es"
                item_cat = categoria

            if not carta_id:
                continue

            # Verificar si ya existe esa carta en el idioma específico
            existe = session.query(UsuarioCarta).filter_by(
                usuario_nombre=usuario_nombre, carta_id=carta_id, idioma=idioma
            ).first()
            
            if not existe:
                nueva_carta = UsuarioCarta(
                    usuario_nombre=usuario_nombre,
                    carta_id=carta_id,
                    idioma=idioma,
                    categoria=item_cat
                )
                session.add(nueva_carta)
                exitos += 1
            else:
                # Si ya existía y el usuario asignó explícitamente una carpeta, actualizarla
                if item_cat:
                    existe.categoria = item_cat
                
        session.commit()
    except Exception as e:
        print(f"Error al agregar cartas: {e}")
        session.rollback()
    finally:
        session.close()
        
    return exitos


def obtener_categorias_usuario(usuario_nombre):
    """Retorna la lista de nombres de categorías creadas por el usuario."""
    session = SessionLocal()
    try:
        cats = session.query(Categoria.nombre).filter_by(usuario_nombre=usuario_nombre).order_by(Categoria.nombre.asc()).all()
        return [c[0] for c in cats]
    finally:
        session.close()


def crear_categoria_usuario(usuario_nombre, nombre_categoria):
    """Crea una nueva categoría para el usuario si no existe."""
    nombre = nombre_categoria.strip()
    if not nombre:
        return False
    session = SessionLocal()
    try:
        existe = session.query(Categoria).filter_by(usuario_nombre=usuario_nombre, nombre=nombre).first()
        if not existe:
            cat = Categoria(usuario_nombre=usuario_nombre, nombre=nombre)
            session.add(cat)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        print(f"Error al crear categoría: {e}")
        return False
    finally:
        session.close()


def eliminar_categoria_usuario(usuario_nombre, nombre_categoria):
    """Elimina una categoría del usuario y desvincula las cartas de esa categoría."""
    session = SessionLocal()
    try:
        session.query(Categoria).filter_by(usuario_nombre=usuario_nombre, nombre=nombre_categoria).delete()
        session.query(UsuarioCarta).filter_by(usuario_nombre=usuario_nombre, categoria=nombre_categoria).update({"categoria": None})
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error al eliminar categoría: {e}")
        return False
    finally:
        session.close()

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
