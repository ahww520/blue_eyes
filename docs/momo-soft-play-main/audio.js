export class SoundGarden {
  constructor(){this.enabled=false;this.style=0;this.context=null;this.last=0;this.volume=.17;}
  async unlock(){
    try{this.context??=new (window.AudioContext||window.webkitAudioContext)();await this.context.resume();return true;}catch{return false;}
  }
  tone(freq,end,start,duration,type='sine',volume=1){
    const c=this.context;if(!c||c.state!=='running')return;
    const osc=c.createOscillator(),gain=c.createGain();osc.type=this.style===2&&type==='sine'?'triangle':type;
    const pitch=[1,1.45,.78][this.style];osc.frequency.setValueAtTime(freq*pitch,start);osc.frequency.exponentialRampToValueAtTime(Math.max(35,end*pitch),start+duration);
    gain.gain.setValueAtTime(.0001,start);gain.gain.exponentialRampToValueAtTime(this.volume*volume,start+.012);gain.gain.exponentialRampToValueAtTime(.0001,start+duration);
    osc.connect(gain).connect(c.destination);osc.start(start);osc.stop(start+duration+.02);
    if(this.style>0){
      const harmonic=c.createOscillator(),overtone=c.createGain(),ratio=this.style===2?2.76:2;
      harmonic.type='sine';harmonic.frequency.setValueAtTime(freq*pitch*ratio,start);
      overtone.gain.setValueAtTime(.0001,start);overtone.gain.exponentialRampToValueAtTime(this.volume*volume*.12,start+.007);overtone.gain.exponentialRampToValueAtTime(.0001,start+Math.max(.03,duration*.42));
      harmonic.connect(overtone).connect(c.destination);harmonic.start(start);harmonic.stop(start+duration+.02);
    }
  }
  noise(duration,cutoff=700){
    const c=this.context;if(!c||c.state!=='running')return;const t=c.currentTime,n=Math.floor(c.sampleRate*duration),buffer=c.createBuffer(1,n,c.sampleRate),data=buffer.getChannelData(0);
    for(let i=0;i<n;i++)data[i]=(Math.random()*2-1)*Math.sin(Math.PI*i/n);
    const source=c.createBufferSource(),filter=c.createBiquadFilter(),gain=c.createGain();source.buffer=buffer;filter.type='lowpass';filter.frequency.value=cutoff;gain.gain.setValueAtTime(.045,t);gain.gain.exponentialRampToValueAtTime(.0001,t+duration);source.connect(filter).connect(gain).connect(c.destination);source.start(t);source.stop(t+duration);
  }
  play(name,strength=1){
    if(!this.enabled||!this.context||this.context.state!=='running')return;
    const t=this.context.currentTime;if(t-this.last<.065)return;this.last=t;
    switch(name){
      case 'press':this.tone(420,155,t,.15);this.tone(720,330,t+.045,.11,'sine',.25);this.noise(.1,450);break;
      case 'stretch':this.tone(190,650,t,.23,'sine',.6);this.tone(380,790,t+.03,.2,'sine',.12);break;
      case 'release':this.tone(470,165,t,.18);this.tone(220,470,t+.09,.13,'sine',.4);break;
      case 'tickle':[0,.08,.17].forEach((d,i)=>this.tone(580+i*110,850-i*80,t+d,.095,'sine',.55));break;
      case 'bounce':this.tone(180+strength*120,65,t,.13,'sine',Math.min(.8,strength));this.noise(.065,500);break;
      case 'pop':this.tone(950,260,t,.11,'sine',.8);this.tone(1330,560,t+.05,.09,'sine',.2);break;
      case 'sneeze':this.tone(250,780,t,.22,'sine',.3);this.noise(.16,2400);this.tone(1200,170,t+.23,.13,'triangle',.32);break;
      case 'sleep':this.tone(240,200,t,.55,'sine',.25);this.tone(300,240,t+.32,.5,'sine',.12);break;
      case 'happy':[440,554,659,880].forEach((f,i)=>this.tone(f,f*1.005,t+i*.11,.28,'sine',.55));break;
      case 'bell':this.tone(840,838,t,.42,'sine',.45);this.tone(1260,1257,t,.2,'sine',.12);break;
      default:this.tone(500,300,t,.12,'sine',.5);
    }
  }
}
