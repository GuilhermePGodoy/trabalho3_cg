# Computacao Grafica - Projeto 3: Iluminacao

Projeto em Python e OpenGL com iluminacao ambiente, difusa e especular em
uma cena interna e externa.

## Integrantes

- Bruno Figueiredo Lima - 14562383
- Guilherme Pascoale Godoy - 14576277

## Requisitos

- Python 3
- Bibliotecas listadas em `requirements.txt`
- Driver com suporte a OpenGL 3.3

Instalacao sugerida:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Execucao

Com o ambiente virtual ativado, execute:

```bash
python -c "from cg_project import run; run()"
```

## Controles

| Tecla | Acao |
|---|---|
| `1` | Liga/desliga a luz da fogueira |
| `2` | Liga/desliga a luminaria amarela |
| `3` | Liga/desliga a arandela azul entre as taças |
| `4` | Liga/desliga a luz ambiente |
| `5` | Liga/desliga as luzes dos vagalumes |
| `U` / `J` | Aumenta/diminui a intensidade ambiente |
| `I` / `K` | Aumenta/diminui a reflexao difusa |
| `O` / `L` | Aumenta/diminui a reflexao especular |
| `WASD` | Move a camera |
| Mouse | Direciona a camera |
| Scroll | Altera o campo de visao |
| `Esc` | Fecha a aplicacao |

## Iluminacao

- A fogueira ocupa sua posicao original e emite uma luz alaranjada.
- Nove vagalumes se movem em trajetorias pseudoaleatorias ao redor de um
  centroide proximo a fogueira e a raposa. Cada inseto possui uma pequena
  barriga branca emissiva com uma fonte atenuada, que pisca de forma subita
  e assincrona sem alterar a cor da textura do inseto.
- A luminaria de piso amarela e a arandela azul usam cores diferentes; a
  cupula azul da arandela fica emissiva enquanto sua luz esta ligada.
- Luzes internas afetam somente objetos internos.
- A fogueira afeta somente objetos externos.
- A fachada voltada para a entrada pertence ao exterior; o restante da malha
  da casa pertence ao interior, com excecao da chamine de pedras, que tambem
  pertence ao exterior.
- Cada objeto possui coeficientes Phong proprios definidos em `scene.py`.
- Arquivos MTL sao usados somente para localizar texturas.

## Estrutura

- `cg_project/app.py`: janela, entrada e loop principal.
- `cg_project/scene.py`: objetos, materiais, luzes e transformacoes.
- `cg_project/assets.py`: leitura de OBJ/MTL e texturas.
- `cg_project/renderer.py`: envio de uniforms e desenho.
- `cg_project/camera.py`: navegacao da camera.
- `cg_project/shader.py`: compilacao dos shaders.
- `cg_project/swarm.py`: movimento coeso dos vagalumes.
- `shaders/`: shaders GLSL 330 core.
