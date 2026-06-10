# Computacao Grafica - Projeto 3

Projeto em Python e OpenGL com iluminacao ambiente, difusa e especular em
uma cena interna e externa.

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

Abra `notebook.ipynb` com o kernel do ambiente virtual e execute as duas
celulas de codigo.

Tambem e possivel executar diretamente:

```bash
python -c "from cg_project import run; run()"
```

## Controles

| Tecla | Acao |
|---|---|
| `1` | Liga/desliga o farol do carro |
| `2` | Liga/desliga a luminaria amarela |
| `3` | Liga/desliga a luminaria azul |
| `4` | Liga/desliga a luz ambiente |
| `U` / `J` | Aumenta/diminui a intensidade ambiente |
| `I` / `K` | Aumenta/diminui a reflexao difusa |
| `O` / `L` | Aumenta/diminui a reflexao especular |
| `WASD` | Move a camera |
| Mouse | Direciona a camera |
| Scroll | Altera o campo de visao |
| `Esc` | Fecha a aplicacao |

## Iluminacao

- O farol acompanha o carro, que se move automaticamente no ambiente externo.
- Duas luminarias internas usam cores diferentes.
- Luzes internas afetam somente objetos internos.
- O farol afeta somente objetos externos.
- Cada objeto possui coeficientes Phong proprios definidos em `scene.py`.
- Arquivos MTL sao usados somente para localizar texturas.

## Estrutura

- `cg_project/app.py`: janela, entrada e loop principal.
- `cg_project/scene.py`: objetos, materiais, luzes e transformacoes.
- `cg_project/assets.py`: leitura de OBJ/MTL e texturas.
- `cg_project/renderer.py`: envio de uniforms e desenho.
- `cg_project/camera.py`: navegacao da camera.
- `cg_project/shader.py`: compilacao dos shaders.
- `shaders/`: shaders GLSL 330 core.
