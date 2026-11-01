import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,cp,readFile,writeFile,readdir,rm} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createPlayerServer} from '../server.mjs';
import {ModuleView} from '../app/module-view.mjs';
const template=fileURLToPath(new URL('../',import.meta.url));
test('standard module view displays source cursor and arbitrary channel names',()=>{
 const text=[];const ctx={fillRect(){},fillText(value){text.push(value);}};
 const title={};const canvas={getContext:()=>ctx};
 const view=new ModuleView(canvas,title,{title:'Original module',channels:['Voice A','Voice B'],orders:[0],patterns:[[[{note:'C-4',instrument:'01',effect:'A06'},{note:'OFF'}]]]});
 view.draw({order:0,row:0,tick:2});
 assert.match(title.textContent,/Original module.*2 channels.*row 00/);
 assert.ok(text.some(t=>t.includes('C-4 01 A06')));assert.ok(text.includes('Voice B'));
});
test('release builder rejects unconfigured adapter and produces both stable entry pages',async()=>{
 const root=await mkdtemp(path.join(tmpdir(),'framework-release-'));
 try{
  const player=path.join(root,'player');await cp(template,player,{recursive:true});
  const builder=path.join(player,'build-release.mjs');
  assert.throws(()=>execFileSync(process.execPath,[builder],{stdio:'pipe'}),/Configure a production/);
  // Explicit shipping-layout fixture only; not original-code or fidelity evidence.
  await writeFile(path.join(player,'app/port.mjs'),`export const metadata={title:'Fixture & test',displayTitle:'Heading <test>',group:'Group',releaseInfo:'Party 1997',credits:[{role:'Code',name:'Author'}],links:{pouet:'https://example.org/a',github:'https://example.org/b'},landing:{start:0,end:1,drawRate:24},duration:1,audio:'none'};`);
  execFileSync(process.execPath,[builder],{stdio:'pipe'});
  execFileSync(process.execPath,[builder],{stdio:'pipe'});
  assert.deepEqual((await readdir(root)).sort(),['player','release']);
  const release=path.join(root,'release');const html=await readFile(path.join(release,'index.html'),'utf8');
  assert.match(html,/<base href=".\/player\/">/);assert.match(html,/Heading &lt;test&gt;/);assert.match(html,/Party 1997/);assert.match(html,/<dd>Author<\/dd>/);
  assert.equal(await readFile(path.join(release,'player/app/release-mode.mjs'),'utf8'),'export const releaseMode = true;\n');
  assert.ok(!(await readdir(path.join(release,'player'))).includes('examples'));
  const server=createPlayerServer(release);await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try{for(const route of ['/','/player/','/player/index.html','/player/app/app.mjs'])assert.equal((await fetch('http://127.0.0.1:'+server.address().port+route)).status,200);}
  finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
  const manifest=JSON.parse(await readFile(path.join(release,'manifest.json'),'utf8'));
  assert.equal(manifest.standard,'release-player-v1');assert.ok(manifest.files.every(f=>f.sha256.length===64));
 }finally{
  if(path.dirname(root)!==path.resolve(tmpdir())||!path.basename(root).startsWith('framework-release-'))throw Error('Unsafe temporary cleanup');
  await rm(root,{recursive:true,force:true});
 }
});
