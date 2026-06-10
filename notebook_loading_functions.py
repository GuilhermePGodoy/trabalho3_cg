# =============================================================================
#  Funções de carregamento — substitua as células correspondentes no notebook
# =============================================================================

import os
import ntpath
from objects_manager import (
    _find_first_file, parse_mtl, resolve_obj_and_texture, build_object
)
from OpenGL.GL import *
from PIL import Image

global vertices_list
vertices_list = []
global textures_coord_list
textures_coord_list = []
global normals_list
normals_list = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def circular_sliding_window_of_three(arr):
    """Triangulariza uma face poligonal com N vértices."""
    if len(arr) == 3:
        return arr
    circular_arr = arr + [arr[0]]
    result = []
    for i in range(len(circular_arr) - 2):
        result.extend(circular_arr[i:i + 3])
    return result


# ---------------------------------------------------------------------------
# load_model_from_file
# ---------------------------------------------------------------------------

def load_model_from_file(filename):
    """
    Carrega um arquivo Wavefront .obj.

    Retorna um dicionário com:
        vertices        – lista de [x, y, z]
        texture         – lista de [u, v]
        normals         – lista de [nx, ny, nz]
        faces           – lista de (face_verts, face_texs, face_normals, material_name)
        materials       – dict nome→parâmetros Phong (resultado de parse_mtl)

    Tratamento robusto de faces:
        - v       → sem textura, sem normal
        - v/vt    → com textura, sem normal
        - v//vn   → sem textura, com normal
        - v/vt/vn → completo
    """
    vertices = []
    normals = []
    texture_coords = []
    faces = []
    material_name = None  # material ativo na leitura

    folder = os.path.dirname(filename)

    # ------------------------------------------------------------------
    # Lê o .obj e coleta vértices, normais, UVs e faces
    # ------------------------------------------------------------------
    for raw_line in open(filename, "r", errors="replace"):
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        values = line.split()
        if not values:
            continue

        if values[0] == 'v':
            vertices.append([float(v) for v in values[1:4]])

        elif values[0] == 'vn':
            normals.append([float(v) for v in values[1:4]])

        elif values[0] == 'vt':
            texture_coords.append([float(v) for v in values[1:3]])

        elif values[0] in ('usemtl', 'usemat'):
            material_name = values[1]

        elif values[0] == 'f':
            face_verts   = []
            face_texs    = []
            face_normals = []

            for token in values[1:]:
                parts = token.split('/')
                # --- índice de vértice (sempre presente) ---
                face_verts.append(int(parts[0]))

                # --- índice de textura (partes[1], pode estar vazio) ---
                if len(parts) >= 2 and parts[1] != '':
                    face_texs.append(int(parts[1]))
                else:
                    face_texs.append(None)   # sinaliza "sem UV"

                # --- índice de normal (partes[2], pode estar ausente) ---
                if len(parts) >= 3 and parts[2] != '':
                    face_normals.append(int(parts[2]))
                else:
                    face_normals.append(None)   # sinaliza "sem normal"

            faces.append((face_verts, face_texs, face_normals, material_name))

    # ------------------------------------------------------------------
    # Carrega parâmetros de material do .mtl (se existir)
    # ------------------------------------------------------------------
    mtl_path = _find_first_file(folder, [".mtl"])
    materials = parse_mtl(mtl_path) if mtl_path else {}

    return {
        "vertices":  vertices,
        "texture":   texture_coords,
        "normals":   normals,
        "faces":     faces,
        "materials": materials,   # ← NOVO: Ka, Kd, Ks, Ns, map_Kd por material
    }


# ---------------------------------------------------------------------------
# Vetores sentinela para UVs e normais ausentes
# ---------------------------------------------------------------------------
_UV_ZERO     = [0.0, 0.0]
_NORMAL_UP   = [0.0, 1.0, 0.0]


def _get_uv(modelo, idx):
    """Retorna a UV pelo índice (1-based) ou [0,0] se ausente."""
    if idx is None or len(modelo['texture']) == 0:
        return _UV_ZERO
    return modelo['texture'][idx - 1]


def _get_normal(modelo, idx):
    """Retorna a normal pelo índice (1-based) ou [0,1,0] se ausente."""
    if idx is None or len(modelo['normals']) == 0:
        return _NORMAL_UP
    return modelo['normals'][idx - 1]


# ---------------------------------------------------------------------------
# load_obj_and_texture  (caminho simples: 1 textura explícita)
# ---------------------------------------------------------------------------

global numberTextures
numberTextures = 0


def load_obj_and_texture(objFile, texturesList):
    """
    Carrega um .obj + lista de texturas na GPU.
    Retorna (vertice_inicial, quantos_vertices).
    """
    modelo = load_model_from_file(objFile)

    verticeInicial = len(vertices_list)
    print('Processando modelo {}. Vertice inicial: {}'.format(objFile, verticeInicial))

    for face in modelo['faces']:
        verts, texs, norms, _ = face   # material_name ignorado aqui
        for v_id, t_id, n_id in zip(
            circular_sliding_window_of_three(verts),
            circular_sliding_window_of_three(texs),
            circular_sliding_window_of_three(norms),
        ):
            vertices_list.append(modelo['vertices'][v_id - 1])
            textures_coord_list.append(_get_uv(modelo, t_id))
            normals_list.append(_get_normal(modelo, n_id))

    verticeFinal = len(vertices_list)
    print('Processando modelo {}. Vertice final: {}'.format(objFile, verticeFinal))

    global numberTextures
    for tex_path in texturesList:
        load_texture_from_file(numberTextures, tex_path)
        numberTextures += 1

    return verticeInicial, verticeFinal - verticeInicial





def load_texture_from_file(texture_id, img_textura):
    print(texture_id)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    img = Image.open(img_textura)
    img = img.convert("RGB")
    img_width = img.size[0]
    img_height = img.size[1]
    image_data = img.tobytes("raw", "RGB", 0, -1)
    #image_data = np.array(list(img.getdata()), np.uint8)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img_width, img_height, 0, GL_RGB, GL_UNSIGNED_BYTE, image_data)





# ---------------------------------------------------------------------------
# load_object  (caminho avançado: suporte a multi-material via .mtl)
# ---------------------------------------------------------------------------

def load_object(folder):
    """
    Carrega um objeto da pasta indicada.

    • Se houver .mtl → carrega um sub-objeto por material, com os parâmetros
      Phong (Ka, Kd, Ks, Ns) embutidos em cada sub-objeto.
    • Caso contrário → comportamento anterior (1 textura).
    """
    global numberTextures

    mtl_path = _find_first_file(folder, [".mtl"])

    # ------------------------------------------------------------------
    # Caminho simples: sem .mtl
    # ------------------------------------------------------------------
    if not mtl_path:
        obj_path, texture_path = resolve_obj_and_texture(folder)
        texture_id = numberTextures
        vertice_inicial, quantos_vertices = load_obj_and_texture(obj_path, [texture_path])
        return build_object(vertice_inicial, quantos_vertices, texture_id)

    # ------------------------------------------------------------------
    # Caminho multi-material: com .mtl
    # ------------------------------------------------------------------
    print(f"Lendo modelo multi-material: {folder}")

    obj_path = _find_first_file(folder, [".obj"])
    modelo   = load_model_from_file(obj_path)
    materials_map = modelo["materials"]   # ← já veio do load_model_from_file

    # Agrupa faces por material
    faces_por_material = {}
    for face in modelo['faces']:
        mat_name = face[3]   # ← índice correto após refatoração
        if mat_name not in faces_por_material:
            faces_por_material[mat_name] = []
        faces_por_material[mat_name].append(face)

    sub_objetos = []

    for mat_name, faces in faces_por_material.items():
        mat_params  = materials_map.get(mat_name, {})
        tex_filename = mat_params.get("map_Kd")

        # Resolve caminho da textura
        tex_path = None
        if tex_filename:
            tex_nome = ntpath.basename(tex_filename)
            candidate = os.path.join(folder, tex_nome)
            tex_path = candidate if os.path.exists(candidate) else None

        if tex_path is None:
            # Fallback: primeira imagem encontrada na pasta
            tex_path = _find_first_file(folder, [".jpg", ".png", ".jpeg", ".tif", ".tiff", ".bmp"])

        if tex_path is None:
            print(f"  [aviso] nenhuma textura encontrada para material '{mat_name}' — ignorado")
            continue

        verticeInicial = len(vertices_list)

        for face in faces:
            verts, texs, norms, _ = face
            for v_id, t_id, n_id in zip(
                circular_sliding_window_of_three(verts),
                circular_sliding_window_of_three(texs),
                circular_sliding_window_of_three(norms),
            ):
                vertices_list.append(modelo['vertices'][v_id - 1])
                textures_coord_list.append(_get_uv(modelo, t_id))
                normals_list.append(_get_normal(modelo, n_id))   # ← antes faltava

        verticeFinal   = len(vertices_list)
        quantos_vertices = verticeFinal - verticeInicial

        texture_id = numberTextures
        load_texture_from_file(texture_id, tex_path)
        numberTextures += 1

        parte = build_object(
            verticeInicial,
            quantos_vertices,
            texture_id,
            name=mat_name,
            material=mat_params,   # ← parâmetros Phong do .mtl
        )
        sub_objetos.append(parte)

    return sub_objetos
