"""Carregamento de modelos OBJ, texturas 2D e cubemap da aplicacao."""

import ctypes
import os
from array import array
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_CLAMP_TO_EDGE,
    GL_FLOAT,
    GL_LINEAR,
    GL_LINEAR_MIPMAP_LINEAR,
    GL_REPEAT,
    GL_RGBA,
    GL_STATIC_DRAW,
    GL_TEXTURE_2D,
    GL_TEXTURE_CUBE_MAP,
    GL_TEXTURE_CUBE_MAP_POSITIVE_X,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_R,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_UNSIGNED_BYTE,
    glBindBuffer,
    glBindTexture,
    glBindVertexArray,
    glBufferData,
    glEnableVertexAttribArray,
    glGenBuffers,
    glGenTextures,
    glGenVertexArrays,
    glGenerateMipmap,
    glPixelStorei,
    glTexImage2D,
    glTexParameteri,
    glVertexAttribPointer,
    GL_UNPACK_ALIGNMENT,
)
from PIL import Image


@dataclass(frozen=True)
class MeshPart:
    """Trecho de uma malha que compartilha material e textura."""

    name: str
    first_vertex: int
    vertex_count: int
    texture_id: int


@dataclass(frozen=True)
class Mesh:
    """Conjunto de partes armazenadas no VBO global."""

    parts: tuple[MeshPart, ...]


class AssetManager:
    """Concentra recursos OpenGL e evita recarregar texturas repetidas."""

    def __init__(self):
        self._vertex_data = array("f")
        self._texture_cache: dict[Path, int] = {}
        self._white_texture: int | None = None
        self.vao: int | None = None
        self.vbo: int | None = None

    def load_mesh(
        self,
        obj_path: str | Path,
        default_texture: str | Path | None = None,
        force_white: bool = False,
        split_by_group: bool = False,
        split_connected_materials: set[str] | None = None,
    ) -> Mesh:
        """Carrega um OBJ e escolhe uma textura para cada material usado."""

        obj_path = Path(obj_path)
        default_path = Path(default_texture) if default_texture else None
        split_connected_materials = split_connected_materials or set()
        model = self._parse_obj(obj_path, split_by_group=split_by_group)
        texture_map = self._parse_mtl_textures(model["mtl_path"])
        parts = []

        for part_name, vertices in model["parts"].items():
            material_name = model["part_materials"][part_name]
            vertex_groups = [(part_name, vertices)]
            if material_name in split_connected_materials:
                components = self._split_connected_components(vertices)
                vertex_groups = [
                    (f"{part_name}:component_{index}", component)
                    for index, component in enumerate(components)
                ]

            for rendered_name, rendered_vertices in vertex_groups:
                first_vertex = len(self._vertex_data) // 8
                self._vertex_data.extend(rendered_vertices)

                texture_path = None
                if not force_white:
                    # O MTL fornece apenas map_Kd; seus coeficientes de luz sao ignorados.
                    mapped_texture = texture_map.get(material_name)
                    if mapped_texture:
                        candidate = obj_path.parent / os.path.basename(mapped_texture)
                        if self._is_image(candidate):
                            texture_path = candidate
                    if texture_path is None and self._is_image(default_path):
                        texture_path = default_path

                texture_id = (
                    self.white_texture
                    if texture_path is None
                    else self.load_texture(texture_path)
                )
                parts.append(
                    MeshPart(
                        name=rendered_name,
                        first_vertex=first_vertex,
                        vertex_count=len(rendered_vertices) // 8,
                        texture_id=texture_id,
                    )
                )

        return Mesh(tuple(parts))

    @staticmethod
    def _split_connected_components(vertices: array) -> list[array]:
        """Separa triangulos que nao compartilham nenhuma posicao."""

        triangle_size = 3 * 8
        triangles = [
            vertices[offset : offset + triangle_size]
            for offset in range(0, len(vertices), triangle_size)
        ]
        position_to_triangles: dict[tuple[float, float, float], list[int]] = {}
        for triangle_index, triangle in enumerate(triangles):
            for vertex_offset in range(0, triangle_size, 8):
                position = tuple(triangle[vertex_offset : vertex_offset + 3])
                position_to_triangles.setdefault(position, []).append(
                    triangle_index
                )

        components = []
        visited = set()
        for start in range(len(triangles)):
            if start in visited:
                continue

            pending = [start]
            visited.add(start)
            component_indices = []
            while pending:
                triangle_index = pending.pop()
                component_indices.append(triangle_index)
                triangle = triangles[triangle_index]
                for vertex_offset in range(0, triangle_size, 8):
                    position = tuple(triangle[vertex_offset : vertex_offset + 3])
                    for neighbor in position_to_triangles[position]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            pending.append(neighbor)

            component = array("f")
            for triangle_index in sorted(component_indices):
                component.extend(triangles[triangle_index])
            components.append(component)

        return sorted(components, key=len, reverse=True)

    def create_ground_mesh(self, texture_path: str | Path) -> Mesh:
        """Cria o piso com UVs repetidos e normal apontando para cima."""

        data = (
            (-0.5, 0.0, -0.5, 0.0, 0.0, 0.0, 1.0, 0.0),
            (0.5, 0.0, -0.5, 100.0, 0.0, 0.0, 1.0, 0.0),
            (0.5, 0.0, 0.5, 100.0, 100.0, 0.0, 1.0, 0.0),
            (-0.5, 0.0, -0.5, 0.0, 0.0, 0.0, 1.0, 0.0),
            (0.5, 0.0, 0.5, 100.0, 100.0, 0.0, 1.0, 0.0),
            (-0.5, 0.0, 0.5, 0.0, 100.0, 0.0, 1.0, 0.0),
        )
        first_vertex = len(self._vertex_data) // 8
        for vertex in data:
            self._vertex_data.extend(vertex)
        part = MeshPart(
            "ground",
            first_vertex,
            len(data),
            self.load_texture(texture_path),
        )
        return Mesh((part,))

    def finalize_geometry(self) -> None:
        """Envia todas as malhas para um unico VBO e configura seus atributos."""

        if self.vao is not None:
            return

        vertices = np.frombuffer(self._vertex_data, dtype=np.float32)
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        # Layout intercalado: posicao (3), UV (2) e normal (3) floats.
        stride = 8 * 4
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, False, stride, None)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(
            1, 2, GL_FLOAT, False, stride, ctypes.c_void_p(3 * 4)
        )
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(
            2, 3, GL_FLOAT, False, stride, ctypes.c_void_p(5 * 4)
        )
        glBindVertexArray(0)

        self._vertex_data = array("f")

    @property
    def white_texture(self) -> int:
        """Retorna uma textura neutra para partes sem imagem valida."""

        if self._white_texture is None:
            self._white_texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self._white_texture)
            pixel = np.array([255, 255, 255, 255], dtype=np.uint8)
            glTexImage2D(
                GL_TEXTURE_2D,
                0,
                GL_RGBA,
                1,
                1,
                0,
                GL_RGBA,
                GL_UNSIGNED_BYTE,
                pixel,
            )
            self._set_texture_parameters(mipmaps=False)
        return self._white_texture

    def load_texture(self, path: str | Path) -> int:
        """Carrega uma textura 2D, gera mipmaps e guarda seu ID em cache."""

        path = Path(path).resolve()
        if path in self._texture_cache:
            return self._texture_cache[path]

        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        with Image.open(path) as image:
            # OpenGL e Pillow usam origens verticais opostas para as imagens.
            image = image.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            data = np.asarray(image, dtype=np.uint8)
            glTexImage2D(
                GL_TEXTURE_2D,
                0,
                GL_RGBA,
                image.width,
                image.height,
                0,
                GL_RGBA,
                GL_UNSIGNED_BYTE,
                data,
            )
        glGenerateMipmap(GL_TEXTURE_2D)
        self._set_texture_parameters(mipmaps=True)
        self._texture_cache[path] = texture_id
        return texture_id

    @staticmethod
    def load_cubemap_cross(path: str | Path) -> int:
        """Recorta uma imagem em cruz nas seis faces de um cubemap."""

        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_CUBE_MAP, texture_id)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        with Image.open(path) as source:
            source = source.convert("RGBA")
            face_size = source.width // 4
            # Ordem exigida por GL_TEXTURE_CUBE_MAP_POSITIVE_X: +X, -X, +Y,
            # -Y, +Z e -Z.
            offsets = ((2, 1), (0, 1), (1, 0), (1, 2), (1, 1), (3, 1))
            for index, (column, row) in enumerate(offsets):
                left = column * face_size
                top = row * face_size
                face = source.crop(
                    (left, top, left + face_size, top + face_size)
                ).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                data = np.asarray(face, dtype=np.uint8)
                glTexImage2D(
                    GL_TEXTURE_CUBE_MAP_POSITIVE_X + index,
                    0,
                    GL_RGBA,
                    face_size,
                    face_size,
                    0,
                    GL_RGBA,
                    GL_UNSIGNED_BYTE,
                    data,
                )

        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
        return texture_id

    @staticmethod
    def _set_texture_parameters(mipmaps: bool) -> None:
        min_filter = GL_LINEAR_MIPMAP_LINEAR if mipmaps else GL_LINEAR
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, min_filter)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    @staticmethod
    def _is_image(path: Path | None) -> bool:
        if path is None or not path.exists():
            return False
        try:
            with Image.open(path) as image:
                image.verify()
            return True
        except (OSError, ValueError):
            return False

    @staticmethod
    def _parse_mtl_textures(mtl_path: Path | None) -> dict[str, str]:
        """Le somente nomes de materiais e seus mapas difusos map_Kd."""

        if mtl_path is None or not mtl_path.exists():
            return {}

        textures = {}
        material_name = None
        with mtl_path.open(errors="replace") as file:
            for raw_line in file:
                values = raw_line.strip().split()
                if not values or values[0].startswith("#"):
                    continue
                if values[0] == "newmtl" and len(values) > 1:
                    material_name = values[1]
                elif values[0] == "map_Kd" and material_name:
                    textures[material_name] = " ".join(values[1:])
        return textures

    @staticmethod
    def _parse_obj(path: Path, split_by_group: bool = False) -> dict:
        """Converte faces OBJ em vertices intercalados separados por material."""

        positions = []
        texture_coords = []
        normals = []
        parts: OrderedDict[str, array] = OrderedDict()
        part_materials: dict[str, str] = {}
        material_name = "default"
        group_name = "default"
        mtl_path = None

        with path.open(errors="replace") as file:
            for raw_line in file:
                values = raw_line.strip().split()
                if not values or values[0].startswith("#"):
                    continue

                tag = values[0]
                if tag == "v":
                    positions.append(tuple(float(value) for value in values[1:4]))
                elif tag == "vt":
                    texture_coords.append(
                        tuple(float(value) for value in values[1:3])
                    )
                elif tag == "vn":
                    normals.append(tuple(float(value) for value in values[1:4]))
                elif tag == "mtllib" and len(values) > 1:
                    candidate = path.parent / " ".join(values[1:])
                    mtl_path = candidate if candidate.exists() else None
                elif tag in ("g", "o") and len(values) > 1:
                    group_name = " ".join(values[1:])
                elif tag in ("usemtl", "usemat") and len(values) > 1:
                    material_name = values[1]
                elif tag == "f":
                    face = [
                        AssetManager._parse_face_vertex(token)
                        for token in values[1:]
                    ]
                    part_name = group_name if split_by_group else material_name
                    bucket = parts.setdefault(part_name, array("f"))
                    part_materials[part_name] = material_name
                    # Triangulacao em leque permite faces com tres ou mais vertices.
                    for index in range(1, len(face) - 1):
                        triangle = (face[0], face[index], face[index + 1])
                        needs_face_normal = any(
                            normal_index is None
                            for _, _, normal_index in triangle
                        )
                        face_normal = (
                            AssetManager._face_normal(triangle, positions)
                            if needs_face_normal
                            else None
                        )
                        for vertex_index, uv_index, normal_index in triangle:
                            position = positions[
                                AssetManager._resolve_index(
                                    vertex_index, len(positions)
                                )
                            ]
                            uv = (
                                texture_coords[
                                    AssetManager._resolve_index(
                                        uv_index, len(texture_coords)
                                    )
                                ]
                                if uv_index is not None and texture_coords
                                else (0.0, 0.0)
                            )
                            normal = (
                                normals[
                                    AssetManager._resolve_index(
                                        normal_index, len(normals)
                                    )
                                ]
                                if normal_index is not None and normals
                                else face_normal or (0.0, 1.0, 0.0)
                            )
                            bucket.extend((*position, *uv, *normal))

        return {
            "parts": parts,
            "part_materials": part_materials,
            "mtl_path": mtl_path,
        }

    @staticmethod
    def _parse_face_vertex(token: str) -> tuple[int, int | None, int | None]:
        """Separa um indice OBJ no formato vertice/uv/normal."""

        components = token.split("/")
        vertex = int(components[0])
        uv = int(components[1]) if len(components) > 1 and components[1] else None
        normal = (
            int(components[2]) if len(components) > 2 and components[2] else None
        )
        return vertex, uv, normal

    @staticmethod
    def _resolve_index(index: int, length: int) -> int:
        """Converte indices OBJ positivos ou relativos em indices Python."""

        return index - 1 if index > 0 else length + index

    @staticmethod
    def _face_normal(triangle, positions) -> tuple[float, float, float]:
        """Calcula uma normal geometrica quando o OBJ nao fornece uma."""

        points = []
        for vertex_index, _, _ in triangle:
            points.append(
                np.array(
                    positions[
                        AssetManager._resolve_index(vertex_index, len(positions))
                    ],
                    dtype=np.float32,
                )
            )
        normal = np.cross(points[1] - points[0], points[2] - points[0])
        length = np.linalg.norm(normal)
        if length == 0.0:
            return 0.0, 1.0, 0.0
        return tuple(normal / length)
