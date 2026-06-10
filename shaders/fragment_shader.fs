#version 330 core

uniform vec4 color;
varying vec2 out_texture;
uniform sampler2D imagem;

void main(){
	vec4 texture = texture2D(imagem, out_texture);
	gl_FragColor = texture;
}