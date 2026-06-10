// =============================================================
// depth_shader.fs
// Fragment shader do depth pass.
// Não precisa escrever cor — só o gl_FragDepth implícito basta.
// =============================================================
#version 330 core

void main() {
    // gl_FragDepth é escrito automaticamente pelo rasterizador.
    // Nada precisa ser feito aqui; o driver grava a profundidade
    // no depth attachment do FBO da luz.
}
