// Shared presentation only. Original algorithms/data remain in production adapters.
import { ModuleView } from './module-view.mjs';
const p=window.player,$=id=>document.getElementById(id);
let timer;
function reveal(){ $('hud').classList.add('visible'); clearTimeout(timer); timer=setTimeout(()=>$('hud').classList.remove('visible'),5000); }
for(const event of ['pointermove','pointerdown','keydown','wheel','touchstart']) addEventListener(event,reveal,{passive:true});
$('scale').onchange=()=>{$('screen').style.transform=`scale(${$('scale').value})`;};
$('volume').oninput=()=>{if(p.outputGain)p.outputGain.gain.value=Number($('volume').value);};
await p.ready;
const meta=p.metadata;
for(const [property,value] of Object.entries(meta.palette ?? {})) {
 if(['accent','text'].includes(property) && CSS.supports('color',value)) document.documentElement.style.setProperty('--'+property,value);
}
$('demo-credits').replaceChildren(...(meta.credits ?? []).map(({role,name})=>{
 const div=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=role;dd.textContent=name;div.append(dt,dd);return div;
}));
for(const [id,url] of [['pouet-link',meta.links?.pouet],['github-link',meta.links?.github]]){
 if(url && /^https:\/\//.test(url)){ const a=$(id);a.href=url;a.hidden=false;a.target='_blank';a.rel='noopener noreferrer'; }
}
const adapter=await import(p.adapterURL);
const moduleData=await adapter.loadDiagnosticsResources?.();
const view=moduleData?new ModuleView($('tracker'),$('tracker-title'),moduleData):null;
$('tracker').hidden=!view;
setInterval(()=>{
 if($('nerd-panel').hidden)return;
 if(view)view.draw(p.trackerState);
 else $('tracker-title').textContent=p.metadata.audio==='none'?'Verified silence':p.trackerState?JSON.stringify(p.trackerState):'Original sound diagnostics unavailable';
},100);
// The production owns its authentic first-animation range and logical cadence.
const preview=meta.landing;
if(preview && Number.isFinite(preview.start) && preview.end>preview.start && preview.drawRate>0){
 const worker=new Worker(new URL('./render-worker.mjs',import.meta.url),{type:'module'});
 const canvas=$('background'),ctx=canvas.getContext('2d');let ready=false,pending=false,last=0,time=preview.start;
 worker.onmessage=({data})=>{
  if(data.type==='ready')ready=true;
  else if(data.type==='frame'){pending=false;if(canvas.width!==data.width||canvas.height!==data.height){canvas.width=data.width;canvas.height=data.height;}ctx.putImageData(new ImageData(new Uint8ClampedArray(data.buffer),data.width,data.height),0,0);worker.postMessage({type:'recycle',buffer:data.buffer},[data.buffer]);}
  else if(data.type==='error'){pending=false;console.error('Landing animation:',data.message);}
 };
 worker.postMessage({type:'init',adapterURL:p.adapterURL});
 setInterval(()=>{
  const now=performance.now();
  if(!p.playing&&!document.hidden&&ready&&!pending){
   if(last)time=preview.start+((time-preview.start+(now-last)/1000)%(preview.end-preview.start));
   pending=true;worker.postMessage({type:'render',time,epoch:0});last=now;
  }else if(p.playing||document.hidden)last=0;
 },1000/preview.drawRate);
}
