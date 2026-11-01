const hex=n=>n.toString(16).toUpperCase().padStart(2,'0');
export class ModuleView {
 constructor(canvas,title,module){this.canvas=canvas;this.ctx=canvas.getContext('2d');this.title=title;this.module=module;canvas.width=40+module.channels.length*110;canvas.height=224;}
 draw(state){if(!state)return;const {module:m,canvas:c,ctx:g}=this;const pat=m.orders[state.order],rows=m.patterns[pat];if(!rows)return;
 this.title.textContent=`${m.title ?? 'Original module'} · ${m.channels.length} channels · order ${hex(state.order)} · pattern ${hex(pat)} · row ${hex(state.row)} · tick ${state.tick}`;
 g.fillStyle='#08121b';g.fillRect(0,0,c.width,c.height);g.font='11px monospace';g.textBaseline='middle';
 m.channels.forEach((ch,i)=>{g.fillStyle='#8aafc5';g.fillText(String(ch),40+i*110,12);});
 g.fillStyle='#244456';g.fillRect(0,104,c.width,18);
 for(let offset=-4;offset<=5;offset++){const r=state.row+offset,row=rows[r];if(!row)continue;const y=113+offset*18;g.fillStyle=offset===0?'#eff8ff':'#7897aa';g.fillText(hex(r),4,y);
 m.channels.forEach((ch,i)=>{const cell=row[i];const note=cell?.note;const name=note ?? '...';g.fillStyle=offset===0?'#f0f8ff':note!==undefined?'#afcede':'#425e70';g.fillText(name+' '+(cell?.instrument ?? '..')+' '+(cell?.effect ?? '...'),40+i*110,y);});
 }
 }
}
