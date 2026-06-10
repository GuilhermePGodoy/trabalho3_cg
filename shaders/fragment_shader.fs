/////////////////////////////////////////////

// Fragment shader adaptado do código visto em aula

/////////////////////////////////////////////

// Struct que define uma fonte de luz
struct Light {
    vec3 position;
    vec3 ambient;
    vec3 diffuse;
    vec3 specular;
};

// Array com todas as fontes de luz
#define MAX_LIGHTS 10
uniform int numActiveLights; // Quantas luzes estão realmente ligadas no momento
uniform Light lights[MAX_LIGHTS];

uniform vec3 viewPos; // define coordenadas com a posicao da camera/observador
uniform float ns; // expoente de reflexao especular

// parametros recebidos do vertex shader
varying vec2 out_texture; // recebido do vertex shader
varying vec3 out_normal; // recebido do vertex shader
varying vec3 out_fragPos; // recebido do vertex shader
uniform sampler2D samplerTexture;



void main(){

    vec3 result = vec3(0.0);
    
    vec3 norm = normalize(out_normal); // normaliza vetores perpendiculares
    vec3 viewDir = normalize(viewPos - out_fragPos); // direcao do observador/camera

    for(int i = 0; i < numActiveLights; i++){
        
        // Iluminação ambiente
        vec3 ambient = lights[i].ambient;

        // Reflexão difusa
        vec3 lightDir = normalize(lights[i].position - out_fragPos); // direcao da luz
        float diff = max(dot(norm, lightDir), 0.0); // verifica limite angular (entre 0 e 90)
    	vec3 diffuse = lights[i].diffuse * diff; // iluminacao difusa

        // Reflexão especular
    	vec3 reflectDir = reflect(-lightDir, norm); // direcao da reflexao
    	float spec = pow(max(dot(viewDir, reflectDir), 0.0), ns);
    	vec3 specular = lights[i].specular * spec;        

    	// Combinando as duas fontes
    	// aplicando o modelo de iluminacao
    	result += ambient + diffuse + specular; // acumula a luz dessa fonte
    }
    vec4 texture = texture2D(samplerTexture, out_texture);
    gl_FragColor = vec4(result, 1.0) * texture;
}