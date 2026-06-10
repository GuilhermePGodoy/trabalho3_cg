"""Renderizacao da cena principal e da skybox com OpenGL moderno."""

import ctypes
from pathlib import Path

import numpy as np
from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_DEPTH_TEST,
    GL_FLOAT,
    GL_LEQUAL,
    GL_LESS,
    GL_STATIC_DRAW,
    GL_TEXTURE0,
    GL_TEXTURE_2D,
    GL_TEXTURE_CUBE_MAP,
    GL_TRIANGLES,
    glActiveTexture,
    glBindBuffer,
    glBindTexture,
    glBindVertexArray,
    glBufferData,
    glDepthFunc,
    glDrawArrays,
    glEnable,
    glEnableVertexAttribArray,
    glGenBuffers,
    glGenVertexArrays,
    glVertexAttribPointer,
)

from .scene import LightingState, Material, PointLight, SceneObject
from .shader import Shader


PROJECT_ROOT = Path(__file__).resolve().parent.parent


SKYBOX_VERTICES = np.array(
    [
        -1.0, 1.0, -1.0, -1.0, -1.0, -1.0, 1.0, -1.0, -1.0,
        1.0, -1.0, -1.0, 1.0, 1.0, -1.0, -1.0, 1.0, -1.0,
        -1.0, -1.0, 1.0, -1.0, -1.0, -1.0, -1.0, 1.0, -1.0,
        -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, -1.0, -1.0, 1.0,
        1.0, -1.0, -1.0, 1.0, -1.0, 1.0, 1.0, 1.0, 1.0,
        1.0, 1.0, 1.0, 1.0, 1.0, -1.0, 1.0, -1.0, -1.0,
        -1.0, -1.0, 1.0, 1.0, -1.0, 1.0, 1.0, 1.0, 1.0,
        1.0, 1.0, 1.0, -1.0, 1.0, 1.0, -1.0, -1.0, 1.0,
        -1.0, 1.0, -1.0, 1.0, 1.0, -1.0, 1.0, 1.0, 1.0,
        1.0, 1.0, 1.0, -1.0, 1.0, 1.0, -1.0, 1.0, -1.0,
        -1.0, -1.0, -1.0, -1.0, -1.0, 1.0, 1.0, -1.0, -1.0,
        1.0, -1.0, -1.0, -1.0, -1.0, 1.0, 1.0, -1.0, 1.0,
    ],
    dtype=np.float32,
)


class Renderer:
    """Envia uniforms e desenha objetos, partes emissivas e skybox."""

    def __init__(self, asset_manager, cubemap_texture: int):
        self.assets = asset_manager
        self.cubemap_texture = cubemap_texture
        self.main_shader = Shader(
            PROJECT_ROOT / "shaders/vertex_shader.vs",
            PROJECT_ROOT / "shaders/fragment_shader.fs",
        )
        self.skybox_shader = Shader(
            PROJECT_ROOT / "shaders/skybox.vs",
            PROJECT_ROOT / "shaders/skybox.fs",
        )
        self.skybox_vao, self.skybox_vbo = self._create_skybox_buffers()

        glEnable(GL_DEPTH_TEST)
        self.main_shader.use()
        self.main_shader.set_int("samplerTexture", 0)
        self.skybox_shader.use()
        self.skybox_shader.set_int("skybox", 0)

    def draw(
        self,
        objects: list[SceneObject],
        lights: list[PointLight],
        light_positions: dict[str, np.ndarray],
        lighting: LightingState,
        camera,
        width: int,
        height: int,
    ) -> None:
        """Desenha um quadro completo usando o estado atual da aplicacao."""

        view = camera.view_matrix()
        projection = camera.projection_matrix(width, height)

        # Estes uniforms sao comuns a todos os objetos e mudam uma vez por quadro.
        self.main_shader.use()
        self.main_shader.set_mat4("view", view)
        self.main_shader.set_mat4("projection", projection)
        self.main_shader.set_vec3("viewPos", camera.position)
        self.main_shader.set_int(
            "ambientEnabled", int(lighting.ambient_enabled)
        )
        self.main_shader.set_float(
            "ambientIntensity", lighting.ambient_intensity
        )
        self.main_shader.set_float("diffuseScale", lighting.diffuse_scale)
        self.main_shader.set_float("specularScale", lighting.specular_scale)
        self.main_shader.set_int("numLights", len(lights))

        for index, light in enumerate(lights):
            base = f"lights[{index}]"
            self.main_shader.set_vec3(
                f"{base}.position", light_positions[light.name]
            )
            self.main_shader.set_vec3(f"{base}.color", light.color)
            self.main_shader.set_vec3(
                f"{base}.attenuation", light.attenuation
            )
            self.main_shader.set_int(f"{base}.groupID", light.group_id)
            self.main_shader.set_int(f"{base}.enabled", int(light.enabled))

        glBindVertexArray(self.assets.vao)
        for scene_object in objects:
            self._draw_object(scene_object, lights)
        glBindVertexArray(0)

        self._draw_skybox(view, projection)

    def _draw_object(
        self, scene_object: SceneObject, lights: list[PointLight]
    ) -> None:
        """Configura transformacao/material e desenha as partes de um objeto."""

        self.main_shader.set_mat4("model", scene_object.transform.matrix())
        self.main_shader.set_int("objectGroupID", scene_object.group_id)
        self._set_material(scene_object.material)

        source_light = next(
            (
                light
                for light in lights
                if light.source_object == scene_object.name and light.enabled
            ),
            None,
        )

        for part in scene_object.mesh.parts:
            emission = (
                source_light.color
                if source_light and part.name in scene_object.emissive_parts
                else (0.0, 0.0, 0.0)
            )
            self.main_shader.set_vec3("emissiveColor", emission)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, part.texture_id)
            glDrawArrays(GL_TRIANGLES, part.first_vertex, part.vertex_count)

    def _set_material(self, material: Material) -> None:
        self.main_shader.set_float("material.ka", material.ka)
        self.main_shader.set_float("material.kd", material.kd)
        self.main_shader.set_float("material.ks", material.ks)
        self.main_shader.set_float("material.ns", material.ns)
        self.main_shader.set_float("material.opacity", material.opacity)

    def _draw_skybox(self, view, projection) -> None:
        """Desenha o cubemap no fundo sem encobrir a geometria da cena."""

        # LEQUAL permite que a skybox passe no limite mais distante do depth buffer.
        glDepthFunc(GL_LEQUAL)
        self.skybox_shader.use()
        self.skybox_shader.set_mat4("view", view)
        self.skybox_shader.set_mat4("projection", projection)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.cubemap_texture)
        glBindVertexArray(self.skybox_vao)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        glBindVertexArray(0)
        glDepthFunc(GL_LESS)

    @staticmethod
    def _create_skybox_buffers() -> tuple[int, int]:
        """Cria um cubo unitario usado para amostrar o cubemap."""

        vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        glBindVertexArray(vao)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(
            GL_ARRAY_BUFFER,
            SKYBOX_VERTICES.nbytes,
            SKYBOX_VERTICES,
            GL_STATIC_DRAW,
        )
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(
            0, 3, GL_FLOAT, False, 3 * 4, ctypes.c_void_p(0)
        )
        glBindVertexArray(0)
        return vao, vbo
