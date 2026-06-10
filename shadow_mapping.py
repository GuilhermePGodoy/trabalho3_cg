# =============================================================
# shadow_mapping.py
#
# Módulo auxiliar para integrar shadow mapping ao pipeline
# existente em objects_manager.py (OpenGL + PyOpenGL / ModernGL).
#
# Uso:
#   from shadow_mapping import ShadowMapRenderer
#   smr = ShadowMapRenderer(max_lights=10, map_size=1024)
#   smr.init_gl()
#
#   # No loop de renderização:
#   smr.render_depth_passes(lights, draw_scene_fn)
#   smr.bind_shadow_maps(shader_program)
#   draw_scene_with_lighting(shader_program)
# =============================================================

import numpy as np
from OpenGL.GL import *


# -----------------------------------------------------------------
# Constantes
# -----------------------------------------------------------------
SHADOW_MAP_SIZE = 1024   # resolução dos depth maps (quadrado)
NEAR_PLANE      = 0.1
FAR_PLANE       = 50.0   # ajuste para cobrir toda a cena
LIGHT_ORTHO_SIZE = 10.0  # metade do lado do frustum ortogonal


# -----------------------------------------------------------------
# Grupos de iluminação
# -----------------------------------------------------------------
# Defina estes IDs como constantes compartilhadas entre Python e GLSL.
GROUP_GLOBAL   = 0   # luz/objeto afeta/é afetado por todos
GROUP_INTERIOR = 1   # luz interna da casa
GROUP_EXTERIOR = 2   # luz externa (sol, lâmpadas externas)


# -----------------------------------------------------------------
# Classe principal
# -----------------------------------------------------------------
class ShadowMapRenderer:
    """
    Gerencia os FBOs e depth textures de cada fonte de luz,
    e executa o depth pass antes da render pass principal.
    """

    def __init__(self, max_lights: int = 10, map_size: int = SHADOW_MAP_SIZE):
        self.max_lights  = max_lights
        self.map_size    = map_size
        self.fbos        = []   # um FBO por luz
        self.depth_maps  = []   # uma depth texture por luz
        self._initialized = False

    # ----------------------------------------------------------
    # Inicialização (chame após ter um contexto GL válido)
    # ----------------------------------------------------------
    def init_gl(self):
        for _ in range(self.max_lights):
            depth_tex = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, depth_tex)
            glTexImage2D(
                GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT,
                self.map_size, self.map_size, 0,
                GL_DEPTH_COMPONENT, GL_FLOAT, None
            )
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            # Coordenadas fora do frustum da luz → sem sombra (borda branca)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER)
            glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR,
                             np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32))

            fbo = glGenFramebuffers(1)
            glBindFramebuffer(GL_FRAMEBUFFER, fbo)
            glFramebufferTexture2D(
                GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depth_tex, 0
            )
            glDrawBuffer(GL_NONE)
            glReadBuffer(GL_NONE)
            glBindFramebuffer(GL_FRAMEBUFFER, 0)

            self.depth_maps.append(depth_tex)
            self.fbos.append(fbo)

        self._initialized = True

    # ----------------------------------------------------------
    # Depth passes — um por luz ativa
    # ----------------------------------------------------------
    def render_depth_passes(self, lights: list, draw_scene_fn, depth_shader):
        """
        lights       : lista de dicts com chaves 'position' e 'group_id'
        draw_scene_fn: callable() que desenha toda a geometria (sem texturas/materiais)
        depth_shader : programa GLSL compilado com depth_shader.vs/.fs
        """
        assert self._initialized, "Chame init_gl() antes de render_depth_passes()"

        glViewport(0, 0, self.map_size, self.map_size)
        glUseProgram(depth_shader)

        self._light_space_matrices = []

        for i, light in enumerate(lights[:self.max_lights]):
            lsm = self._compute_light_space_matrix(light['position'])
            self._light_space_matrices.append(lsm)

            glBindFramebuffer(GL_FRAMEBUFFER, self.fbos[i])
            glClear(GL_DEPTH_BUFFER_BIT)

            loc = glGetUniformLocation(depth_shader, "lightSpaceMatrix")
            glUniformMatrix4fv(loc, 1, GL_FALSE, lsm.flatten())

            draw_scene_fn()

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    # ----------------------------------------------------------
    # Vincula os shadow maps ao shader principal
    # ----------------------------------------------------------
    def bind_shadow_maps(self, main_shader, num_lights: int,
                         texture_unit_offset: int = 1):
        """
        main_shader        : programa GLSL principal (vertex+fragment)
        num_lights         : número de luzes ativas
        texture_unit_offset: primeira unidade de textura disponível
                             (geralmente 1, pois 0 é usada pela textura difusa)
        """
        glUseProgram(main_shader)

        for i in range(num_lights):
            unit = texture_unit_offset + i
            glActiveTexture(GL_TEXTURE0 + unit)
            glBindTexture(GL_TEXTURE_2D, self.depth_maps[i])

            loc = glGetUniformLocation(main_shader, f"shadowMap[{i}]")
            glUniform1i(loc, unit)

        # Envia as lightSpaceMatrices para o vertex shader
        for i, lsm in enumerate(self._light_space_matrices[:num_lights]):
            loc = glGetUniformLocation(main_shader, f"lightSpaceMatrix[{i}]")
            glUniformMatrix4fv(loc, 1, GL_FALSE, lsm.flatten())

        loc = glGetUniformLocation(main_shader, "numActiveLights")
        glUniform1i(loc, num_lights)

    # ----------------------------------------------------------
    # Utilitário: envia o groupID do objeto atual ao shader
    # ----------------------------------------------------------
    @staticmethod
    def set_object_group(main_shader, group_id: int):
        loc = glGetUniformLocation(main_shader, "objectGroupID")
        glUniform1i(loc, group_id)

    # ----------------------------------------------------------
    # Envia o groupID de cada luz ao shader principal
    # ----------------------------------------------------------
    @staticmethod
    def set_light_groups(main_shader, lights: list):
        for i, light in enumerate(lights):
            loc = glGetUniformLocation(main_shader, f"lights[{i}].groupID")
            glUniform1i(loc, light.get('group_id', GROUP_GLOBAL))

    # ----------------------------------------------------------
    # Matriz light-space (projeção ortogonal para luzes locais)
    # ----------------------------------------------------------
    @staticmethod
    def _compute_light_space_matrix(light_pos: np.ndarray,
                                    target: np.ndarray = None) -> np.ndarray:
        """
        Gera uma lightSpaceMatrix para uma luz pontual usando projeção
        ortogonal em direção a um alvo (padrão: origem da cena).

        Para luzes pontuais em cenas internas/externas, uma projeção
        ortogonal voltada para o centro da cena é uma boa aproximação.
        Para sombras omnidirecionais perfeitas, use cube shadow maps
        (extensão futura).
        """
        if target is None:
            target = np.zeros(3, dtype=np.float32)

        pos = np.array(light_pos, dtype=np.float32)

        # Vetor "up" — evitar colinearidade com a direção da luz
        forward = target - pos
        forward /= np.linalg.norm(forward)
        up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        if abs(np.dot(forward, up)) > 0.99:
            up = np.array([0.0, 0.0, 1.0], dtype=np.float32)

        # View matrix (lookAt manual)
        right   = np.cross(forward, up);  right   /= np.linalg.norm(right)
        up_real = np.cross(right, forward)

        view = np.array([
            [ right[0],    right[1],    right[2],   -np.dot(right,   pos)],
            [ up_real[0],  up_real[1],  up_real[2], -np.dot(up_real, pos)],
            [-forward[0], -forward[1], -forward[2],  np.dot(forward, pos)],
            [ 0,           0,           0,           1                   ]
        ], dtype=np.float32)

        # Projeção ortogonal
        s = LIGHT_ORTHO_SIZE
        n, f = NEAR_PLANE, FAR_PLANE
        proj = np.array([
            [1/s,  0,        0,           0         ],
            [0,    1/s,      0,           0         ],
            [0,    0,       -2/(f-n),    -(f+n)/(f-n)],
            [0,    0,        0,           1         ]
        ], dtype=np.float32)

        return proj @ view


# -----------------------------------------------------------------
# Exemplo de integração no loop principal (pseudocódigo)
# -----------------------------------------------------------------
INTEGRATION_EXAMPLE = """
# ---------- setup (uma vez) ----------
smr = ShadowMapRenderer(max_lights=10, map_size=1024)
smr.init_gl()

depth_shader = compile_shader("depth_shader.vs", "depth_shader.fs")
main_shader  = compile_shader("vertex_shader.vs", "fragment_shader.fs")

# Defina as luzes com group_id:
lights = [
    {'position': [0, 3, 0],  'group_id': GROUP_INTERIOR, ...},  # lâmpada sala
    {'position': [2, 3, -1], 'group_id': GROUP_INTERIOR, ...},  # lâmpada cozinha
    {'position': [10, 8, 0], 'group_id': GROUP_EXTERIOR, ...},  # sol externo
]

# Defina o group_id de cada objeto no .mtl ou na cena:
#   paredes internas, móveis → GROUP_INTERIOR
#   fachada, jardim          → GROUP_EXTERIOR
#   paredes que dividem      → GROUP_GLOBAL (recebem ambas)

# ---------- loop de renderização ----------
while running:
    # 1. Depth passes (um FBO por luz)
    smr.render_depth_passes(lights, draw_geometry_only, depth_shader)

    # 2. Render pass principal
    glViewport(0, 0, WIDTH, HEIGHT)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glUseProgram(main_shader)

    smr.bind_shadow_maps(main_shader, len(lights))
    smr.set_light_groups(main_shader, lights)

    for obj in scene_objects:
        smr.set_object_group(main_shader, obj.group_id)
        draw_object(obj, main_shader)
"""
