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
    """
    Lê um arquivo .mtl e retorna um dicionário mapeando o nome do material
    para um dicionário com seus parâmetros Phong:
        {
            "map_Kd": str | None,   # caminho da textura difusa
            "Ka": [r, g, b],        # cor ambiente
            "Kd": [r, g, b],        # cor difusa
            "Ks": [r, g, b],        # cor especular
            "Ns": float,            # expoente especular (brilho)
            "d":  float,            # opacidade (1.0 = opaco)
        }
    Valores padrão Phong razoáveis são usados para campos ausentes.
    """
    materials = {}
    current_mat = None

    if not mtl_path or not os.path.exists(mtl_path):
        return materials

    def _default():
        return {
            "map_Kd": None,
            "Ka": [0.2, 0.2, 0.2],
            "Kd": [0.8, 0.8, 0.8],
            "Ks": [0.0, 0.0, 0.0],
            "Ns": 32.0,
            "d":  1.0,
        }

    for line in open(mtl_path, "r", errors="replace"):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        values = line.split()
        if not values:
            continue

        if values[0] == 'newmtl':
            current_mat = values[1]
            materials[current_mat] = _default()

        elif current_mat is None:
            continue  # ignora linhas antes do primeiro newmtl

        elif values[0] == 'map_Kd':
            materials[current_mat]["map_Kd"] = " ".join(values[1:])

        elif values[0] == 'Ka' and len(values) >= 4:
            materials[current_mat]["Ka"] = [float(values[1]), float(values[2]), float(values[3])]

        elif values[0] == 'Kd' and len(values) >= 4:
            materials[current_mat]["Kd"] = [float(values[1]), float(values[2]), float(values[3])]

        elif values[0] == 'Ks' and len(values) >= 4:
            materials[current_mat]["Ks"] = [float(values[1]), float(values[2]), float(values[3])]

        elif values[0] == 'Ns' and len(values) >= 2:
            # Ns no .mtl costuma vir em escala 0-1000; OpenGL espera >= 1
            ns_val = float(values[1])
            materials[current_mat]["Ns"] = max(1.0, ns_val)

        elif values[0] in ('d', 'Tr') and len(values) >= 2:
            # 'd' é opacidade direta; 'Tr' é transparência (1-d)
            val = float(values[1])
            materials[current_mat]["d"] = val if values[0] == 'd' else 1.0 - val

    return materials


def build_object(vertice_inicial, quantos_vertices, texture_id, name=None, material=None):
    """
    material deve ser o dicionário retornado por parse_mtl para aquele material,
    ou None (nesse caso serão usados defaults neutros no draw_object).
    """
    return {
        "name": name,
        "vertice_inicial": vertice_inicial,
        "quantos_vertices": quantos_vertices,
        "texture_id": texture_id,
        "material": material,   # dict com Ka, Kd, Ks, Ns, d — ou None
    }


# Uniforms de material enviados para o fragment shader.
# Os nomes devem coincidir exatamente com os declarados no fragment_shader.fs.
_MATERIAL_DEFAULTS = {
    "Ka": [0.2, 0.2, 0.2],
    "Kd": [0.8, 0.8, 0.8],
    "Ks": [0.0, 0.0, 0.0],
    "Ns": 32.0,
    "d":  1.0,
}


def _upload_material(program, mat):
    """Envia os parâmetros de material para os uniforms do shader."""
    m = mat if mat is not None else _MATERIAL_DEFAULTS

    Ka = m.get("Ka", _MATERIAL_DEFAULTS["Ka"])
    Kd = m.get("Kd", _MATERIAL_DEFAULTS["Kd"])
    Ks = m.get("Ks", _MATERIAL_DEFAULTS["Ks"])
    Ns = m.get("Ns", _MATERIAL_DEFAULTS["Ns"])
    d  = m.get("d",  _MATERIAL_DEFAULTS["d"])

    glUniform3f(glGetUniformLocation(program, "material.Ka"), *Ka)
    glUniform3f(glGetUniformLocation(program, "material.Kd"), *Kd)
    glUniform3f(glGetUniformLocation(program, "material.Ks"), *Ks)
    glUniform1f(glGetUniformLocation(program, "material.Ns"), Ns)
    glUniform1f(glGetUniformLocation(program, "material.d"),  d)


def draw_object(obj, model_matrix, program):
    loc_model = glGetUniformLocation(program, "model")
    glUniformMatrix4fv(loc_model, 1, GL_TRUE, model_matrix)

    # obj pode ser uma lista de partes (sub-objetos) ou um dicionário único
    if isinstance(obj, list):
        for part in obj:
            _upload_material(program, part.get("material"))
            glBindTexture(GL_TEXTURE_2D, part["texture_id"])
            glDrawArrays(GL_TRIANGLES, part["vertice_inicial"], part["quantos_vertices"])
    else:
        _upload_material(program, obj.get("material"))
        glBindTexture(GL_TEXTURE_2D, obj["texture_id"])
        glDrawArrays(GL_TRIANGLES, obj["vertice_inicial"], obj["quantos_vertices"])
