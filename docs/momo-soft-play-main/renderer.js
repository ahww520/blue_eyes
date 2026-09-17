const N=32;
export class SoftRenderer {
  constructor(canvas){
    this.canvas=canvas;this.gl=canvas.getContext('webgl',{alpha:true,premultipliedAlpha:false,antialias:true,preserveDrawingBuffer:true});this.ready=false;this.img=null;
    if(!this.gl){this.fallback=canvas.getContext('2d');return;}
    const gl=this.gl;
    const vs=`attribute vec2 position;attribute vec2 uv;uniform vec2 resolution;varying vec2 vUv;void main(){vUv=uv;vec2 p=position/resolution;gl_Position=vec4(p.x*2.0-1.0,1.0-p.y*2.0,0.,1.);}`;
    const fs=`precision mediump float;varying vec2 vUv;uniform sampler2D sprite;uniform vec3 tint;uniform vec2 light;uniform float material;uniform float pressure;
    void main(){vec4 px=texture2D(sprite,vUv);if(px.a<.01)discard;float lum=dot(px.rgb,vec3(.299,.587,.114));float cool=smoothstep(-.015,.04,max(px.b,px.g)-px.r);vec3 ivory=vec3(lum*1.07,lum*1.035,lum*.975);vec3 col=mix(px.rgb,ivory,cool)*mix(vec3(1.),tint,.55);vec2 d=(vUv-vec2(.46,.46))*vec2(1.,1.05);float oval=max(0.,1.-dot(d,d)*3.6);float gloss=pow(max(0.,1.-length((vUv-light)*vec2(1.4,1.))*2.5),5.);float edge=pow(1.-oval,2.);float mask=smoothstep(.16,.8,lum);
    if(material<.5){col+=vec3(.095,.085,.068)*gloss*mask;col+=vec3(.025,.021,.014)*edge*mask;}else if(material<1.5){col=mix(col,vec3(.97,.95,.91)*tint,.13*mask);col+=gloss*.025*mask;}else{float grain=fract(sin(dot(vUv,vec2(1229.8,2891.3)))*43758.54);col=mix(col,vec3(.87,.835,.78)*tint,.15*mask)+(grain-.5)*.018*mask;}
    col-=pressure*.035*exp(-length(vUv-vec2(.5,.62))*8.)*mask;
    gl_FragColor=vec4(clamp(col,0.,1.),px.a);}`;
    const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;};
    this.program=gl.createProgram();gl.attachShader(this.program,shader(gl.VERTEX_SHADER,vs));gl.attachShader(this.program,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(this.program);if(!gl.getProgramParameter(this.program,gl.LINK_STATUS))throw new Error('Renderer could not link');gl.useProgram(this.program);
    this.mesh=new Float32Array((N+1)*(N+1)*4);const indices=[];
    for(let y=0;y<N;y++)for(let x=0;x<N;x++){const a=y*(N+1)+x;indices.push(a,a+1,a+N+1,a+1,a+N+2,a+N+1);}
    this.length=indices.length;this.buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,this.buffer);gl.bufferData(gl.ARRAY_BUFFER,this.mesh,gl.DYNAMIC_DRAW);
    const index=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,index);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(indices),gl.STATIC_DRAW);
    for(const [name,offset]of [['position',0],['uv',8]]){const at=gl.getAttribLocation(this.program,name);gl.enableVertexAttribArray(at);gl.vertexAttribPointer(at,2,gl.FLOAT,false,16,offset);}
    this.uniforms={};for(const key of ['resolution','tint','light','material','pressure'])this.uniforms[key]=gl.getUniformLocation(this.program,key);
    gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.clearColor(0,0,0,0);
    canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();this.ready=false;});canvas.addEventListener('webglcontextrestored',()=>location.reload());
  }
  async load(src){
    this.img=new Image();this.img.src=src;await this.img.decode();
    if(this.gl){const gl=this.gl;this.texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,this.texture);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,this.img);}
    this.ready=true;
  }
  resize(w,h){this.w=w;this.h=h;const dpr=Math.min(devicePixelRatio||1,2);this.canvas.width=Math.round(w*dpr);this.canvas.height=Math.round(h*dpr);if(this.gl){this.gl.viewport(0,0,this.canvas.width,this.canvas.height)}else this.fallback.setTransform(dpr,0,0,dpr,0,0);}
  draw(s){
    if(!this.ready)return;
    const {cx,cy,b,sx,sy,r,bend,press,point,grab,wobble,clock,tint,material,light,blink}=s;
    if(!this.gl){const c=this.fallback;c.clearRect(0,0,this.w,this.h);c.save();c.translate(cx,cy);c.rotate(r);c.scale(sx,sy);c.filter='grayscale(1) sepia(.18)';c.drawImage(this.img,-b/2,-b/2,b,b);c.restore();return;}
    const gl=this.gl,cos=Math.cos(r),sin=Math.sin(r);let k=0;
    for(let iy=0;iy<=N;iy++)for(let ix=0;ix<=N;ix++){
      const u=ix/N,v=iy/N;let x=(u-.5)*b,y=(v-.5)*b;
      const deltaX=u-point.x,deltaY=v-point.y,fall=Math.exp(-(deltaX*deltaX+deltaY*deltaY)*16);
      // Local surface indentation follows the touch, rather than scaling the whole sprite.
      x+=deltaX*b*press*.16*fall+grab.x*fall;
      y+=deltaY*b*press*.13*fall+press*b*.026*fall+grab.y*fall;
      // Asymmetric drag and the upper silhouette follow with a slight delay.
      x+=Math.sin(v*Math.PI)*bend+Math.sin(v*8-clock*15)*wobble*b*.022;
      y+=Math.sin(u*Math.PI*2+clock*16)*wobble*b*.01;
      // Compress the existing textured eyelids for a blink; all facial detail comes from the asset.
      if(blink>0){for(const ex of [.38,.625]){const fx=u-ex,fy=v-.458;const eye=Math.exp(-fx*fx*650-fy*fy*800);y-=fy*b*eye*blink*.85;}}
      x*=sx;y*=sy;
      this.mesh[k++]=cx+x*cos-y*sin;this.mesh[k++]=cy+x*sin+y*cos;this.mesh[k++]=u;this.mesh[k++]=v;
    }
    gl.clear(gl.COLOR_BUFFER_BIT);gl.bindBuffer(gl.ARRAY_BUFFER,this.buffer);gl.bufferSubData(gl.ARRAY_BUFFER,0,this.mesh);gl.uniform2f(this.uniforms.resolution,this.w,this.h);gl.uniform3f(this.uniforms.tint,...tint);gl.uniform2f(this.uniforms.light,light.x,light.y);gl.uniform1f(this.uniforms.material,material);gl.uniform1f(this.uniforms.pressure,press);gl.drawElements(gl.TRIANGLES,this.length,gl.UNSIGNED_SHORT,0);
  }
}
