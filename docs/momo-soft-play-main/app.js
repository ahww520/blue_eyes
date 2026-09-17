import { SoftRenderer } from './renderer.js?v=ivory';
import { SoundGarden } from './audio.js';

const $=s=>document.querySelector(s),all=s=>[...document.querySelectorAll(s)],clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const SITE_URL='https://estherliu-lab.github.io/momo-soft-play/';
const qrImage=new Image();qrImage.src='site-qr.png';
const canvas=$('#toy'),stage=$('#stage'),fx=$('#effects'),fctx=fx.getContext('2d'),audio=new SoundGarden();
let renderer;try{renderer=new SoftRenderer(canvas);}catch(e){$('#loading').textContent='这次没能唤醒 MOMO，请刷新重试';throw e;}
const today=()=>new Date().toLocaleDateString('en-CA');let day=today(),count=0,prefs={};
try{prefs=JSON.parse(localStorage.getItem('momo-v2-prefs')||'{}');count=Number(localStorage.getItem('momo-joy-'+day))||0;}catch{}
const clean=(v,f,min,max)=>Number.isFinite(Number(v))?clamp(Number(v),min,max):f;
let color=clean(prefs.color,0,0,3),material=clean(prefs.material,0,0,2),soft=clean(prefs.soft,75,25,100),size=clean(prefs.size,100,75,120),haptic=prefs.haptic!==false;
color=prefs.palette==='ivory-v1'?Math.round(color):0;material=Math.round(material);audio.style=Math.round(clean(prefs.soundStyle,0,0,2));audio.enabled=true;
const palette=[{name:'奶油卡其',tint:[1,.99,.965],card:'#f1eadd'},{name:'暖象牙白',tint:[1,1,1],card:'#f6f2e9'},{name:'燕麦米',tint:[1,.955,.885],card:'#ebe1d2'},{name:'香槟奶霜',tint:[1.04,.985,.915],card:'#f2e6d5'}];
const materialNames=['珍珠软胶','绵绵奶冻','细砂陶感'],materialNotes=['微透的边缘，藏着一小团月光','像刚醒的奶冻，慢半拍回到你手心','微微磨砂的触感，安静又细腻'];
const reducedQuery=matchMedia('(prefers-reduced-motion:reduce)');let reduced=reducedQuery.matches;
reducedQuery.addEventListener('change',e=>{reduced=e.matches;});
let w=0,h=0,base={x:0,y:0,b:300},mode='squish',last=0,clock=0,points=new Map(),primary=null,pinchStart=0,particles=[],ready=false,flying=false,flyVelocity={x:0,y:0},lastTouch=0,lastSqueak=0,wakeTimer=0,speechTimer=0,toastTimer=0,holdTimer=0,cardURL=null,cardBlob=null,blinkAt=3.5,blink=0;
const state={x:0,y:0,sx:1,sy:1,r:0,bend:0,press:0,gx:0,gy:0,wobble:0};
const target={...state},velocity=Object.fromEntries(Object.keys(state).map(k=>[k,0]));
let touchUV={x:.5,y:.6},light={x:.32,y:.23},lastDraw=null;
function persist(){try{localStorage.setItem('momo-v2-prefs',JSON.stringify({color,material,soft,size,haptic,soundStyle:audio.style,palette:'ivory-v1'}));}catch{}}
function vibration(ms=9){if(haptic&&navigator.vibrate)navigator.vibrate(ms);}
function speak(message,mood){$('#speech').textContent=message;$('#speech').classList.add('reaction');if(mood)$('#mood').textContent=mood;clearTimeout(speechTimer);speechTimer=setTimeout(()=>{$('#speech').classList.remove('reaction');$('#speech').textContent='试试双击，我还藏了个小惊喜';$('#mood').textContent='和你一起，慢慢变软';},4200);}
function toast(message){$('#toast').textContent=message;$('#toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),2800);}
function refreshCount(){if(today()!==day){day=today();count=0;try{count=Number(localStorage.getItem('momo-joy-'+day))||0;}catch{}}$('#count').textContent=count;}
function register(){refreshCount();count++;try{localStorage.setItem('momo-joy-'+day,String(count));}catch{}refreshCount();if(count%20===0){audio.play('happy');speak('已解锁：MOMO 的特别喜欢','今日成就 · 最佳捏捏搭子');burst(base.x,base.y-base.b*.1,16);}}
function burst(x,y,n=5){if(reduced)return;for(let i=0;i<n;i++)particles.push({x,y,vx:(Math.random()-.5)*110,vy:-45-Math.random()*95,life:1.2,size:5+Math.random()*8,type:Math.random()>.65?'star':'bubble',color:Math.random()>.5?'#b69a77':'#b4a089'});}
function drawFx(dt){fctx.clearRect(0,0,w,h);for(const p of particles){p.life-=dt;p.x+=p.vx*dt;p.y+=p.vy*dt;p.vy+=45*dt;fctx.globalAlpha=Math.max(0,Math.min(.75,p.life));fctx.strokeStyle=p.color;fctx.fillStyle=p.color;fctx.lineWidth=1;
if(p.type==='star'){fctx.font=`${p.size*2}px Georgia`;fctx.fillText('✧',p.x,p.y);}else{fctx.beginPath();fctx.arc(p.x,p.y,p.size,0,Math.PI*2);fctx.stroke();fctx.beginPath();fctx.arc(p.x-p.size*.26,p.y-p.size*.3,p.size*.16,0,Math.PI*2);fctx.fill();}}
fctx.globalAlpha=1;particles=particles.filter(p=>p.life>0);}
function layout(){const rect=stage.getBoundingClientRect();w=rect.width;h=rect.height;const mobile=w<=700;
base={x:w*.5,y:h*(mobile?.53:.45),b:Math.min(w*(mobile?.8:.39),h*(mobile?.42:.65),540)*size/100};
renderer.resize(w,h);const dpr=Math.min(devicePixelRatio||1,2);fx.width=w*dpr;fx.height=h*dpr;fctx.setTransform(dpr,0,0,dpr,0,0);
$('#speech').style.top=Math.max(mobile?200:70,base.y-base.b*.51-30)+'px';
$('.object-caption').style.top=(base.y+base.b*.5+21)+'px';$('.object-caption').style.bottom='auto';
$('#shadow').style.top=(base.y+base.b*.45)+'px';$('#shadow').style.width=base.b*.62+'px';$('#shadow').style.left=(base.x-base.b*.31)+'px';}
new ResizeObserver(layout).observe(stage);
function neutral(){Object.assign(target,{x:0,y:0,sx:1,sy:1,r:0,bend:0,press:0,gx:0,gy:0,wobble:0});}
function cancel(){clearTimeout(holdTimer);clearTimeout(wakeTimer);points.clear();primary=null;flying=false;neutral();}
function reset(){cancel();speak('归位，还是你最喜欢的那一只','已回到你的手心');}
function point(e){const r=canvas.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top};}
function hit(p){return Math.abs(p.x-base.x-state.x)<base.b*.47&&Math.abs(p.y-base.y-state.y)<base.b*.48;}
function modePress(){const softness=soft/100;
if(mode==='squish'){target.sy=1-.29*softness;target.sx=1+.19*softness;target.press=1;target.y=base.b*.065;audio.play('press');}
if(mode==='stretch'){target.sy=1.06;target.sx=.98;target.press=.35;audio.play('stretch');}
if(mode==='tickle'){target.wobble=1;target.sy=.97;audio.play('tickle');}
if(mode==='toss'){target.sy=1.04;target.sx=.96;audio.play('pop');}
}
function start(p,id){if(!ready)return false;const now=performance.now();flying=false;
const entry={...p,startX:p.x,startY:p.y,prevX:p.x,prevY:p.y,time:now,vx:0,vy:0};points.set(id,entry);
if(points.size===1){primary=id;register();touchUV={x:clamp((p.x-base.x-state.x)/base.b+.5,0,1),y:clamp((p.y-base.y-state.y)/base.b+.5,0,1)};modePress();vibration();
const phrases={squish:['咕叽，被你捏成一小团了','慢慢捏，我今天没有别的安排','压力交给我，快乐还给你'],stretch:['再长一点，也不会松开你的手','拉——长——一小团快乐'],tickle:['哈哈哈，那里真的会痒','停一下啦，我的可爱要漏出来了'],toss:['接住我，我把信任都给你了','往上轻轻一抛，快乐就起飞']};
const list=phrases[mode];speak(list[Math.floor(Math.random()*list.length)],{squish:'正在融化，稍等一下',stretch:'可爱被你拉长了',tickle:'被挠到笑出咕叽声',toss:'准备起飞'}[mode]);
clearTimeout(holdTimer);holdTimer=setTimeout(()=>{if(points.size===1&&mode==='squish'){target.sy=.65;target.sx=1.22;target.press=.7;audio.play('sleep');speak('呼，被你捏到快睡着了','隐藏表情 · 融化小困包');blink=1;}},1800);
if(now-lastTouch<320&&mode!=='toss'){clearTimeout(holdTimer);surprise('sneeze');}lastTouch=now;
}else if(points.size===2){clearTimeout(holdTimer);const a=[...points.values()];pinchStart=Math.max(20,Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y));audio.play('stretch');speak('两只手的拥抱，是双倍喜欢','双指拉伸中');}
return true;}
window.addEventListener('pointerdown',()=>audio.unlock(),{capture:true,once:true});
canvas.addEventListener('pointerdown',e=>{const p=point(e);if(!hit(p)||points.size>=2)return;e.preventDefault();canvas.focus({preventScroll:true});audio.unlock();canvas.setPointerCapture(e.pointerId);start(p,e.pointerId);});
canvas.addEventListener('pointermove',e=>{const p=point(e);light.x=clamp(p.x/w,.2,.8);light.y=clamp(p.y/h,.1,.7);if(!points.has(e.pointerId))return;e.preventDefault();const a=points.get(e.pointerId),now=performance.now(),dt=Math.max(8,now-a.time)/1000;const dx=p.x-a.startX,dy=p.y-a.startY;
a.vx=(p.x-a.x)/dt;a.vy=(p.y-a.y)/dt;a.x=p.x;a.y=p.y;a.time=now;
if(Math.abs(dx)+Math.abs(dy)>10)clearTimeout(holdTimer);
if(points.size===2){const pair=[...points.values()],distance=Math.hypot(pair[0].x-pair[1].x,pair[0].y-pair[1].y),scale=clamp(distance/pinchStart,.65,1.65);const angle=Math.atan2(pair[1].y-pair[0].y,pair[1].x-pair[0].x);target.sx=1+(scale-1)*Math.abs(Math.cos(angle));target.sy=1+(scale-1)*Math.abs(Math.sin(angle));target.x=clamp((pair[0].x+pair[1].x)/2-base.x,-w*.17,w*.17);target.y=clamp((pair[0].y+pair[1].y)/2-base.y,-h*.15,h*.15);target.press=.3;target.gx=target.gy=0;return;}
const s=soft/100;
if(mode==='toss'){target.x=clamp(dx,-w*.28,w*.28);target.y=clamp(dy,-h*.25,h*.2);target.r=clamp(dx/base.b*.22,-.3,.3);target.sy=1+Math.min(.15,Math.abs(a.vy)*.00015);target.sx=1/target.sy;}
else if(mode==='tickle'){target.x=clamp(dx*.18,-base.b*.1,base.b*.1);target.r=Math.sin(clock*19)*.025;target.wobble=clamp(Math.abs(a.vx)*.003,.2,1.8);target.gx=clamp(dx*.05,-12,12);target.gy=clamp(dy*.05,-12,12);
if(now-lastSqueak>350&&Math.hypot(a.vx,a.vy)>55){audio.play('tickle');vibration(5);burst(p.x,p.y,2);lastSqueak=now;}}
else if(mode==='stretch'){target.x=clamp(dx*.26,-w*.14,w*.14);target.y=clamp(dy*.23,-h*.15,h*.14);target.gx=clamp(dx*.56*s,-base.b*.35,base.b*.35);target.gy=clamp(dy*.56*s,-base.b*.32,base.b*.32);target.sx=1+Math.min(.28,Math.abs(dx)/base.b*.35*s)-Math.min(.12,Math.abs(dy)/base.b*.13);target.sy=1+Math.min(.3,Math.abs(dy)/base.b*.35*s)-Math.min(.12,Math.abs(dx)/base.b*.13);target.bend=clamp(dx*.06,-18,18);target.r=clamp(dx*.0006,-.14,.14);
if(now-lastSqueak>430&&Math.hypot(a.vx,a.vy)>90){audio.play('stretch');lastSqueak=now;}}
else{target.x=clamp(dx*.5,-w*.18,w*.18);target.y=clamp(dy*.33+base.b*.05,-h*.13,h*.15);target.gx=clamp(dx*.15*s,-24,24);target.gy=clamp(dy*.15*s,-24,24);target.bend=clamp(dx*.12*s,-25,25);target.r=clamp(dx*.0012,-.2,.2);target.press=1+Math.min(.4,Math.abs(dy)/base.b);target.sy=clamp(1-.3*s+dy/base.b*.18,.54,1.12);target.sx=1+.23*s+Math.min(.14,Math.abs(dx)/base.b*.15);}
});
function end(id,cancelled=false){if(!points.has(id))return;const entry=points.get(id);points.delete(id);clearTimeout(holdTimer);blink=0;
if(points.size){const [next,p]=points.entries().next().value;primary=next;p.startX=p.x;p.startY=p.y;target.gx=0;target.gy=0;return;}
primary=null;
if(mode==='toss'&&!cancelled&&!reduced){flying=true;flyVelocity={x:clamp(entry.vx*.65,-750,750),y:clamp(entry.vy*.65,-1100,850)};if(Math.abs(flyVelocity.x)+Math.abs(flyVelocity.y)<100)flyVelocity.y=-480;target.press=0;target.gx=0;target.gy=0;target.sx=target.sy=1;audio.play('release');speak('呜呼——落地也会软软地弹起来','飞行中的小快乐');}
else{neutral();if(!cancelled){velocity.sy=-.55;audio.play('release');vibration(8);if(mode==='tickle')burst(base.x+state.x,base.y+state.y,7);}}
}
canvas.addEventListener('pointerup',e=>end(e.pointerId));canvas.addEventListener('pointercancel',e=>end(e.pointerId,true));canvas.addEventListener('lostpointercapture',e=>{if(points.has(e.pointerId))end(e.pointerId,true);});window.addEventListener('blur',cancel);
canvas.addEventListener('keydown',e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();if(!e.repeat){audio.unlock();start({x:base.x,y:base.y},'keyboard');}}else if(e.key.startsWith('Arrow')){e.preventDefault();flying=false;target.x=clamp(target.x+(e.key==='ArrowLeft'?-20:e.key==='ArrowRight'?20:0),-w*.18,w*.18);target.y=clamp(target.y+(e.key==='ArrowUp'?-20:e.key==='ArrowDown'?20:0),-h*.15,h*.15);}else if(e.key==='Escape')reset();});
canvas.addEventListener('keyup',e=>{if(e.key===' '||e.key==='Enter')end('keyboard');});
function surprise(force){if(!ready)return;clearTimeout(wakeTimer);audio.unlock();const kind=force||['sneeze','happy','sleep'][Math.floor(Math.random()*3)];
if(kind==='sneeze'){target.sx=.86;target.sy=1.13;target.r=-.04;audio.play('sneeze');speak('阿——啾，可爱也会打喷嚏','隐藏表情 · 一小团阿啾');wakeTimer=setTimeout(()=>{target.sx=1.2;target.sy=.78;target.wobble=1.4;burst(base.x,base.y+base.b*.08,12);vibration(15);wakeTimer=setTimeout(()=>{if(!points.size)neutral();},220);},280);}
else if(kind==='happy'){audio.play('happy');target.y=-base.b*.1;target.sx=.93;target.sy=1.09;target.wobble=.5;speak('噔噔，送你一颗看不见的小太阳','隐藏表情 · 开心到起飞');burst(base.x,base.y-base.b*.2,15);wakeTimer=setTimeout(()=>{if(!points.size)neutral();},600);}
else{audio.play('sleep');target.sy=.68;target.sx=1.2;target.y=base.b*.14;blink=1;speak('我先融化一会儿，你也休息一下','隐藏表情 · 奶冻小困包');wakeTimer=setTimeout(()=>{if(!points.size)neutral();blink=0;},2600);}}
function animate(t){const dt=Math.min((t-last)/1000||.016,.032);last=t;clock+=dt;
if(flying){flyVelocity.y+=850*dt;target.x+=flyVelocity.x*dt;target.y+=flyVelocity.y*dt;target.r=clamp(flyVelocity.x*.00035,-.3,.3);
const limitX=Math.max(15,Math.min(w*.27,w*.5-base.b*.4)),floor=h*.72-base.y-base.b*.4,ceiling=-(base.y-base.b*.43-12);
if(target.x>limitX||target.x<-limitX){target.x=clamp(target.x,-limitX,limitX);flyVelocity.x*=-.67;audio.play('bounce',.5);velocity.sx=-1.3;}
if(target.y<ceiling){target.y=ceiling;flyVelocity.y=Math.abs(flyVelocity.y)*.5;}
if(target.y>floor&&flyVelocity.y>0){target.y=floor;const impact=flyVelocity.y;flyVelocity.y*=-.58;flyVelocity.x*=.72;velocity.sy=-clamp(impact*.003,0,2.5);velocity.sx=clamp(impact*.002,0,1.5);audio.play('bounce',clamp(impact/600,.2,1));vibration(10);if(impact<110){flying=false;neutral();}}
}
const stiffness=material===1?70:210-soft*1.25,damping=reduced?30:material===1?10:12;
for(const key of Object.keys(state)){velocity[key]+=((target[key]-state[key])*stiffness-velocity[key]*damping)*dt;state[key]+=velocity[key]*dt;}
if(!reduced&&clock>blinkAt&&points.size===0){blink=Math.sin(clamp((clock-blinkAt)*7,0,Math.PI));if(clock-blinkAt>.46){blink=0;blinkAt=clock+3.2+Math.random()*4;}}
const breath=reduced||points.size||flying?0:Math.sin(clock*1.75)*.005;
const draw={cx:base.x+state.x,cy:base.y+state.y,b:base.b,sx:state.sx-breath,sy:state.sy+breath,r:state.r,bend:state.bend,press:state.press,point:touchUV,grab:{x:state.gx,y:state.gy},wobble:reduced?0:state.wobble,clock,tint:palette[color].tint,material,light,blink};
renderer.draw(draw);lastDraw=draw;drawFx(dt);
$('#shadow').style.transform=`translate(${state.x*.8}px,${state.y*.17}px) scale(${clamp(state.sx*(1+state.y/base.b*.6),.45,1.6)},${clamp(1+state.y/base.b,.35,1.3)})`;
$('#shadow').style.opacity=String(clamp(.75+state.y/base.b*.7,.2,1));
requestAnimationFrame(animate);}
requestAnimationFrame(animate);
renderer.load('momo-opal.png').then(()=>{ready=true;$('#loading').hidden=true;layout();}).catch(()=>{$('#loading').textContent='MOMO 迷路了，刷新就能再见面';});

// Compact controls keep the play surface free of sliders and tracks.
function syncSettings(){all('[data-color]').forEach((b,i)=>{b.classList.toggle('selected',color===i);b.setAttribute('aria-pressed',color===i);});all('[data-material]').forEach((b,i)=>{b.classList.toggle('selected',material===i);b.setAttribute('aria-pressed',material===i);});$('#color-name').textContent=palette[color].name;$('#material-note').textContent=materialNotes[material];$('.spec-label strong').textContent=materialNames[material]+' · 云朵性格';$('#soft-value').textContent=soft;$('#size-value').textContent=size+'%';$('#soft-label').textContent=soft>=85?'软成一小摊':soft>=60?'软到心里':'弹得刚刚好';$('#sound-style').textContent=['咕叽水滴','啵啵奶糖','软软木琴'][audio.style]+' ↻';$('#haptic').setAttribute('aria-checked',haptic);
for(const b of all('[data-step]')){const [key,d]=b.dataset.step.split(':');const value=key==='soft'?soft:size;b.disabled=Number(d)<0?value<=(key==='soft'?25:75):value>=(key==='soft'?100:120);}persist();}
all('.tool').forEach(b=>b.addEventListener('click',()=>{cancel();mode=b.dataset.mode;all('.tool').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',x===b);});$('#hint').textContent={squish:'按住捏一捏，松手回弹，试试双指拉长它',stretch:'捏住任意一点往外拉，松手就会弹回来',tickle:'在肚子上轻轻来回挪动，听它咕叽笑',toss:'抓住往上甩一下，看看它怎么软软落地'}[mode];audio.play('bell');}));
all('[data-color]').forEach(b=>b.onclick=()=>{color=Number(b.dataset.color);syncSettings();audio.play('bell');});
all('[data-material]').forEach(b=>b.onclick=()=>{material=Number(b.dataset.material);syncSettings();audio.play('pop');});
all('[data-step]').forEach(b=>b.onclick=()=>{const [key,d]=b.dataset.step.split(':');if(key==='soft')soft=clamp(soft+Number(d)*5,25,100);else size=clamp(size+Number(d)*5,75,120);syncSettings();layout();audio.play('pop');});
$('#sound').onclick=async()=>{const enabled=!audio.enabled;if(enabled&&!await audio.unlock()){toast('声音暂时没醒过来，再点一下试试');return;}audio.enabled=enabled;$('#sound').setAttribute('aria-pressed',enabled);$('#sound').setAttribute('aria-label',enabled?'关闭声音':'开启声音');$('#sound span').textContent=enabled?'声音开':'声音关';audio.play('happy');};
$('#sound-style').onclick=async()=>{audio.style=(audio.style+1)%3;syncSettings();if(!audio.enabled)$('#sound').click();else{await audio.unlock();audio.play('tickle');}};
$('#haptic').onclick=()=>{haptic=!haptic;syncSettings();vibration(12);};
$('#settings-toggle').onclick=()=>{cancel();$('#settings-dialog').showModal();$('#settings-toggle').setAttribute('aria-expanded','true');};
for(const id of ['settings-close','settings-done'])$('#'+id).onclick=()=>$('#settings-dialog').close();
$('#settings-dialog').addEventListener('close',()=>$('#settings-toggle').setAttribute('aria-expanded','false'));
$('#reset').onclick=reset;$('#surprise').onclick=()=>surprise();
for(const dialog of all('dialog'))dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});

async function createCard(){
await qrImage.decode();
const c=document.createElement('canvas');c.width=900;c.height=1125;const x=c.getContext('2d'),g=x.createLinearGradient(0,0,900,1125);g.addColorStop(0,'#fbf9f4');g.addColorStop(1,palette[color].card);x.fillStyle=g;x.fillRect(0,0,900,1125);
x.fillStyle='#8b7b66';x.textAlign='left';x.font='22px sans-serif';x.fillText('SOFT OBJECTS STUDIO',65,80);x.textAlign='right';x.fillStyle='#ac9271';x.fillText('NO 002',835,80);
x.textAlign='center';x.fillStyle='#655544';x.font='bold 52px sans-serif';x.fillText('今天，把世界捏软了一点',450,190);x.font='25px sans-serif';x.fillStyle='#9a8a77';x.fillText(today()+'   /   '+palette[color].name,450,246);
if(lastDraw){const r=lastDraw,span=base.b*1.22;const sx=clamp((r.cx-span/2)/w*canvas.width,0,canvas.width),sy=clamp((r.cy-span/2)/h*canvas.height,0,canvas.height),sw=Math.min(span/w*canvas.width,canvas.width-sx),sh=Math.min(span/h*canvas.height,canvas.height-sy);const size=590;const sourceRatio=sw/sh;const dw=sourceRatio>1?size:size*sourceRatio,dh=sourceRatio>1?size/sourceRatio:size;x.drawImage(canvas,sx,sy,sw,sh,450-dw/2,535-dh/2,dw,dh);}
x.fillStyle='#655544';x.font='bold 34px sans-serif';x.fillText('MOMO  /  '+count+' 次小快乐',450,856);x.fillStyle='#998975';x.font='24px sans-serif';x.fillText(materialNames[material]+'  ·  软糯程度 '+soft,450,902);x.textAlign='left';x.fillStyle='#9b8a74';x.font='20px sans-serif';x.fillText('你不必很厉害，今天够可爱就好',65,980);
x.font='18px sans-serif';x.fillStyle='#9b8a74';x.fillText('联络作者',65,1009);x.font='20px sans-serif';x.fillStyle='#8b7b66';x.fillText('x：@hann7712',65,1033);x.fillText('wechat:Canaan-77',65,1065);
x.imageSmoothingEnabled=false;x.drawImage(qrImage,665,948,164,164);x.imageSmoothingEnabled=true;
x.textAlign='center';x.font='18px sans-serif';x.fillStyle='#8b7b66';x.fillText('微信扫码来捏一捏',747,932);
cardBlob=await new Promise(resolve=>c.toBlob(resolve,'image/png'));if(!cardBlob)throw new Error('Card generation failed');if(cardURL)URL.revokeObjectURL(cardURL);cardURL=URL.createObjectURL(cardBlob);$('#card-image').src=cardURL;
}
$('#checkin').onclick=async()=>{if(!ready){toast('等 MOMO 醒来，就能收藏啦');return;}refreshCount();try{await createCard();$('#share-status').textContent='长按卡片保存，或把快乐分享给一个朋友';$('#card-dialog').showModal();audio.play('bell');}catch{toast('这次没有拍好，再试一次吧');}};
$('#card-close').onclick=()=>$('#card-dialog').close();
$('#download').onclick=()=>{if(!cardURL)return;const a=document.createElement('a');a.href=cardURL;a.download='MOMO-'+today()+'.png';a.click();$('#share-status').textContent='收藏卡已准备下载，手机也可以长按图片保存';};
$('#share').onclick=async()=>{if(!cardBlob)return;try{const file=new File([cardBlob],'MOMO-'+today()+'.png',{type:'image/png'}),text=`我和 MOMO 收集了 ${count} 次小快乐，你也来捏捏`;if(navigator.canShare?.({files:[file]}))await navigator.share({title:'MOMO · 把世界捏软一点',text,files:[file]});else if(navigator.share)await navigator.share({title:'MOMO · 软物研究所',text,url:SITE_URL});else if(navigator.clipboard&&isSecureContext){await navigator.clipboard.writeText(SITE_URL);$('#share-status').textContent='链接已复制，也可以长按收藏卡，分享图片';}else $('#share-status').textContent='请保存收藏卡，或复制地址栏的网页链接分享';}catch(e){if(e.name!=='AbortError')$('#share-status').textContent='可以先保存收藏卡，再发送给朋友';}};
syncSettings();refreshCount();
