// Run after copying this template to player/. Writes only the sibling release/.
import {readFile,writeFile,mkdir,cp,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createHash} from 'node:crypto';
const source=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(source,'../release');
const {metadata}=await import(new URL('./app/port.mjs',import.meta.url));
if(metadata.duration!==null&&!(metadata.duration>0))throw Error('Configure a production before packaging');
if(!['none','original-code'].includes(metadata.audio))throw Error('Finish original sound or verify silence before release');
if(!metadata.landing || !(metadata.landing.end>metadata.landing.start) || !(metadata.landing.drawRate>0))throw Error('Configure authentic live landing animation');
if(!(metadata.credits?.length) || !metadata.links?.pouet || !metadata.links?.github)throw Error('Configure credits and production links');
// Fail rather than leave development files from a previous incompatible attempt.
const allowed=new Set(['player','index.html','serve.mjs','Start.cmd','README.md','manifest.json']);
await mkdir(root,{recursive:true});
for(const entry of await readdir(root))if(!allowed.has(entry)&&!entry.startsWith('browser-'))throw Error('Review existing release file before packaging: '+entry);
await mkdir(path.join(root,'player'),{recursive:true});
for(const name of ['app','runtime','production','assets']){
 try{await cp(path.join(source,name),path.join(root,'player',name),{recursive:true});}
 catch(error){if(error.code!=='ENOENT')throw error;}
}
await writeFile(path.join(root,'player/app/release-mode.mjs'),'export const releaseMode = true;\n');
const html=await readFile(path.join(source,'index.html'),'utf8');
const escape=value=>String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const configured=html.replace(/<title>.*?<\/title>/,'<title>'+escape(metadata.title)+'</title>')
 .replace(/(<span id="demo-title">).*?(<\/span>)/,(_,a,b)=>a+escape(metadata.displayTitle ?? metadata.title)+b)
 .replace(/(<p class="group" id="demo-group">).*?(<\/p>)/,(_,a,b)=>a+escape(metadata.group)+b)
 .replace(/(<p class="meta" id="demo-meta">).*?(<\/p>)/,(_,a,b)=>a+escape(metadata.releaseInfo)+b)
 .replace(/(<dl class="credits" id="demo-credits">).*?(<\/dl>)/,(_,a,b)=>a+metadata.credits.map(c=>'<div><dt>'+escape(c.role)+'</dt><dd>'+escape(c.name)+'</dd></div>').join('')+b);
await writeFile(path.join(root,'player/index.html'),configured);
await writeFile(path.join(root,'index.html'),configured.replace('<head>','<head>\n<base href="./player/">'));
await cp(path.join(source,'style.css'),path.join(root,'player/style.css'));
await cp(path.join(source,'server.mjs'),path.join(root,'serve.mjs'));
await writeFile(path.join(root,'Start.cmd'),'@echo off\r\ncd /d "%~dp0"\r\nnode serve.mjs\r\n');
const readme=path.join(root,'README.md');
try{await readFile(readme);}catch{await writeFile(readme,'# Release review pending\n\nPreview: node release/serve.mjs from the repository. Open http://127.0.0.1:1997/ .\n\nComplete docs/guides/release-player-standard.md checklist with actual evidence, performance limits and human review. Publication remains human-owned.\n\nDeploy only after review: use release/ as the static HTTPS publish directory, no build step; preserve relative paths, serve .mjs as JavaScript, do not add Content-Encoding:gzip to explicitly decompressed checkpoints, disable SPA fallback. Test root/player entry, audio, seek and ending on the deployed URL.\n');}
const files=[];
async function inventory(dir){for(const item of await readdir(dir,{withFileTypes:true})){
 const file=path.join(dir,item.name);if(item.isDirectory())await inventory(file);
 else if(file!==path.join(root,'manifest.json')){const bytes=await readFile(file);files.push({path:path.relative(root,file).replaceAll('\\','/'),bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')});}
}}
await inventory(root);await writeFile(path.join(root,'manifest.json'),JSON.stringify({standard:'release-player-v1',files},null,2));
console.log('Packaged '+root+'. Acceptance and human review remain pending; audit unused assets before release.');
