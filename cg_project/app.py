"""Inicializacao da janela, controles e loop principal da aplicacao."""

from pathlib import Path

import glfw
import numpy as np
from OpenGL.GL import (
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_SRC_ALPHA,
    glBlendFunc,
    glClear,
    glClearColor,
    glEnable,
    glViewport,
)

from .assets import AssetManager
from .camera import Camera
from .renderer import Renderer
from .scene import LightingState, create_lights, create_scene
from .swarm import FireflySwarm


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Application:
    """Coordena entrada do usuario, atualizacao da cena e renderizacao."""

    def __init__(self, width: int = 1280, height: int = 720, visible: bool = True):
        self.width = width
        self.height = height
        self.visible = visible
        self.camera = Camera(last_x=width / 2, last_y=height / 2)
        self.lighting = LightingState()
        self.delta_time = 0.0
        self.last_frame = 0.0

        if not glfw.init():
            raise RuntimeError("Nao foi possivel inicializar o GLFW")

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        # A janela nasce oculta para que testes possam executar sem piscar na tela.
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        self.window = glfw.create_window(
            width, height, "Computacao Grafica - Projeto 3", None, None
        )
        if self.window is None:
            glfw.terminate()
            raise RuntimeError("Nao foi possivel criar a janela GLFW")

        glfw.make_context_current(self.window)
        self._register_callbacks()
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.assets = AssetManager()
        meshes = self._load_meshes()
        self.assets.finalize_geometry()
        cubemap = self.assets.load_cubemap_cross(
            PROJECT_ROOT / "assets/textures/skybox/galaxy.png"
        )
        self.objects = create_scene(meshes)
        self.objects_by_name = {obj.name: obj for obj in self.objects}
        self.lights = create_lights()
        self.firefly_swarm = FireflySwarm(
            [
                obj
                for obj in self.objects
                if obj.name.startswith("vagalume_")
            ],
            [
                obj
                for obj in self.objects
                if obj.name.startswith("brilho_vagalume_")
            ],
            [
                light
                for light in self.lights
                if light.name.startswith("luz_vagalume_")
            ],
        )
        self.renderer = Renderer(self.assets, cubemap)
        glViewport(0, 0, self.width, self.height)
        self.last_frame = glfw.get_time()

        if visible:
            glfw.show_window(self.window)
            glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_DISABLED)

        self._print_controls()

    def _load_meshes(self) -> dict:
        """Carrega modelos e texturas antes de finalizar o VBO compartilhado."""

        models = PROJECT_ROOT / "assets/models"
        textures = PROJECT_ROOT / "assets/textures"

        specifications = {
            "raposa": (
                models / "raposa/13577_Tibetan_Hill_Fox_v1_L3.obj",
                models / "raposa/Tibetan_Hill_Fox_dif.jpg",
                False,
            ),
            "arvore": (
                models / "arvores/birch_tree.obj",
                models / "arvores/tree_bark_65102.jpg",
                False,
            ),
            "casa": (
                models / "casa/midpoly_town_house_01.obj",
                models / "casa/T_brightwood_basecolor.png",
                False,
            ),
            "fogueira": (
                models / "fogueira/Campfire.obj",
                models / "fogueira/campfire.jpg",
                False,
            ),
            "frango": (
                models / "frango/10864_rotisserie_chicken_v2_L3.obj",
                models / "frango/chicken.jpg",
                False,
            ),
            "porta": (
                models / "porta/aporta.obj",
                models / "porta/T_brightwood_basecolor.png",
                False,
            ),
            "cama": (
                models / "cama/bed.obj",
                models / "cama/bed_d.png",
                False,
            ),
            "comoda": (
                models / "comoda/eb_dresser_01.obj",
                models / "comoda/eb_dresser_01_c.png",
                False,
            ),
            "taca": (
                models / "libertadores/copa_libertadores_2021.obj",
                models / "libertadores/Material_002_baseColor.png",
                False,
            ),
            "lampada": (
                models / "lampada/lampada.obj",
                models / "lampada/Lamp_Porcelan_DIF.png",
                False,
            ),
            "lampada_parede": (
                models
                / "lampada_parede/Brass Color Wall Sconce Art Deco Lamp.obj",
                models
                / (
                    "lampada_parede/"
                    "Brass Color Wall Sconce Art Deco Lamp_"
                    "Brass Color Wall Sconce Art Deco Lamp_BaseColor.png"
                ),
                False,
            ),
            "vagalume": (
                models / "inseto/uploads_files_5014749_Fly_Low_Poly.obj",
                models / "inseto/Fly_Tris_Diffuse.png",
                False,
            ),
            "estrela": (
                models / "estrela/Star_obj.obj",
                None,
                True,
            ),
        }

        meshes = {}
        for name, (obj_path, texture_path, force_white) in specifications.items():
            print(f"Carregando {name}...")
            meshes[name] = self.assets.load_mesh(
                obj_path,
                default_texture=texture_path,
                force_white=force_white,
                split_by_group=name == "lampada_parede",
                split_connected_materials=(
                    {"rocks.002"} if name == "casa" else None
                ),
            )
        meshes["grama"] = self.assets.create_ground_mesh(
            textures / "piso/grass.jpg"
        )
        meshes["brilho_vagalume"] = self.assets.create_sphere_mesh(
            "firefly_glow"
        )
        return meshes

    def run(self, max_frames: int | None = None) -> None:
        """Executa o loop de atualizacao e desenho ate a janela ser fechada."""

        frame_count = 0
        try:
            while not glfw.window_should_close(self.window):
                if max_frames is not None and frame_count >= max_frames:
                    break

                current_frame = glfw.get_time()
                self.delta_time = current_frame - self.last_frame
                self.last_frame = current_frame
                glfw.poll_events()

                self._process_movement()
                self.firefly_swarm.update(self.delta_time)

                glClearColor(0.08, 0.10, 0.14, 1.0)
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                self.renderer.draw(
                    self.objects,
                    self.lights,
                    self._light_positions(),
                    self.lighting,
                    self.camera,
                    self.width,
                    self.height,
                )
                glfw.swap_buffers(self.window)
                frame_count += 1
        finally:
            glfw.destroy_window(self.window)
            glfw.terminate()

    def _light_positions(self) -> dict[str, np.ndarray]:
        """Calcula em coordenadas de mundo as fontes presas aos objetos."""

        return {
            light.name: self.objects_by_name[
                light.source_object
            ].transform.transform_point(light.local_position)
            for light in self.lights
        }

    def _process_movement(self) -> None:
        """Aplica movimento continuo da camera para as teclas pressionadas."""

        speed = 8.0 * self.delta_time
        movement = (
            (glfw.KEY_W, "forward"),
            (glfw.KEY_S, "backward"),
            (glfw.KEY_A, "left"),
            (glfw.KEY_D, "right"),
        )
        for key, direction in movement:
            if glfw.get_key(self.window, key) == glfw.PRESS:
                self.camera.move(direction, speed)

    def _register_callbacks(self) -> None:
        """Registra os callbacks de teclado, janela, mouse e scroll."""

        glfw.set_key_callback(self.window, self._on_key)
        glfw.set_framebuffer_size_callback(self.window, self._on_resize)
        glfw.set_cursor_pos_callback(self.window, self._on_mouse)
        glfw.set_scroll_callback(self.window, self._on_scroll)

    def _on_key(self, window, key, scancode, action, mods) -> None:
        """Alterna luzes e ajusta os termos de iluminacao pelo teclado."""

        del scancode, mods
        if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            glfw.set_window_should_close(window, True)
            return

        if action == glfw.PRESS and key in (
            glfw.KEY_1,
            glfw.KEY_2,
            glfw.KEY_3,
        ):
            light = self.lights[key - glfw.KEY_1]
            light.enabled = not light.enabled
            state = "ligada" if light.enabled else "desligada"
            print(f"{light.name}: {state}")
        elif action == glfw.PRESS and key == glfw.KEY_4:
            self.lighting.ambient_enabled = not self.lighting.ambient_enabled
            state = "ligada" if self.lighting.ambient_enabled else "desligada"
            print(f"luz ambiente: {state}")
        elif action == glfw.PRESS and key == glfw.KEY_5:
            enabled = self.firefly_swarm.toggle_lights()
            state = "ligadas" if enabled else "desligadas"
            print(f"luzes dos vagalumes: {state}")
        elif action == glfw.PRESS and key == glfw.KEY_6:
            star_lights = [
                light
                for light in self.lights
                if light.name.startswith("luz_estrela_")
            ]
            enabled = not any(light.enabled for light in star_lights)
            for light in star_lights:
                light.enabled = enabled
            state = "ligada" if enabled else "desligada"
            print(f"constelacao do cruzeiro do sul: {state}")
        elif action in (glfw.PRESS, glfw.REPEAT):
            if key == glfw.KEY_U:
                self.lighting.change_ambient(0.05)
            elif key == glfw.KEY_J:
                self.lighting.change_ambient(-0.05)
            elif key == glfw.KEY_I:
                self.lighting.change_diffuse(0.1)
            elif key == glfw.KEY_K:
                self.lighting.change_diffuse(-0.1)
            elif key == glfw.KEY_O:
                self.lighting.change_specular(0.1)
            elif key == glfw.KEY_L:
                self.lighting.change_specular(-0.1)
            else:
                return
            self._print_lighting()

    def _on_resize(self, window, width: int, height: int) -> None:
        del window
        self.width = max(width, 1)
        self.height = max(height, 1)
        glViewport(0, 0, self.width, self.height)

    def _on_mouse(self, window, xpos: float, ypos: float) -> None:
        del window
        self.camera.look(xpos, ypos)

    def _on_scroll(self, window, xoffset: float, yoffset: float) -> None:
        del window, xoffset
        self.camera.zoom(yoffset)

    def _print_lighting(self) -> None:
        print(
            "iluminacao: "
            f"ambiente={self.lighting.ambient_intensity:.2f}, "
            f"difusa={self.lighting.diffuse_scale:.2f}, "
            f"especular={self.lighting.specular_scale:.2f}"
        )

    @staticmethod
    def _print_controls() -> None:
        print(
            "Controles: 1/2/3 luzes, 4 ambiente, 5 vagalumes, "
            "6 cruzeiro do sul, "
            "U/J ambiente, I/K difusa, O/L especular, WASD, mouse, Esc"
        )


def run(max_frames: int | None = None, visible: bool = True) -> None:
    """Ponto de entrada publico do projeto."""

    Application(visible=visible).run(max_frames=max_frames)
