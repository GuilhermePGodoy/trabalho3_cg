import os
from OpenGL.GL import *


def _find_first_file(folder, extensions):
    entries = sorted(os.listdir(folder))
    for name in entries:
        lower = name.lower()
        for ext in extensions:
            if lower.endswith(ext):
                return os.path.join(folder, name)
    return None


def resolve_obj_and_texture(folder):
    obj_path = _find_first_file(folder, [".obj"])
    if obj_path is None:
        raise FileNotFoundError(f".obj nao encontrado em: {folder}")

    texture_path = _find_first_file(folder, [".png", ".jpg", ".jpeg"])
    if texture_path is None:
        raise FileNotFoundError(f"textura nao encontrada em: {folder}")

    return obj_path, texture_path


def parse_mtl(mtl_path):
    """Lê um arquivo .mtl e mapeia o nome do material para o arquivo de textura."""
    materials = {}
    current_mat = None
    if not mtl_path or not os.path.exists(mtl_path):
        return materials

    for line in open(mtl_path, "r"):
        if line.startswith('#'): continue
        values = line.split()
        if not values: continue
        
        if values[0] == 'newmtl':
            current_mat = values[1]
        elif values[0] == 'map_Kd' and current_mat:
            # Junta com espaço caso o arquivo da textura tenha nome com espaços
            materials[current_mat] = " ".join(values[1:])
            
    return materials


def build_object(vertice_inicial, quantos_vertices, texture_id, name=None):
    return {
        "name": name,
        "vertice_inicial": vertice_inicial,
        "quantos_vertices": quantos_vertices,
        "texture_id": texture_id,
    }


def draw_object(obj, model_matrix, program):
    loc_model = glGetUniformLocation(program, "model")
    glUniformMatrix4fv(loc_model, 1, GL_TRUE, model_matrix)
    
    # obj pode ser uma lista de partes (sub-objetos) ou um dicionário único
    if isinstance(obj, list):
        for part in obj:
            glBindTexture(GL_TEXTURE_2D, part["texture_id"])
            glDrawArrays(GL_TRIANGLES, part["vertice_inicial"], part["quantos_vertices"])
    else:
        glBindTexture(GL_TEXTURE_2D, obj["texture_id"])
        glDrawArrays(GL_TRIANGLES, obj["vertice_inicial"], obj["quantos_vertices"])
