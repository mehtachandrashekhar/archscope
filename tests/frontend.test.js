const fs=require('fs'), vm=require('vm');
const path=require('path');
const dir=path.join(__dirname,'..');
const code=fs.readFileSync(path.join(dir,'static/app.js'),'utf8');
const html=fs.readFileSync(path.join(dir,'static/index.html'),'utf8');
const TRICKY="It's a \"test\" & <b>bold</b>";
const mkEl=()=>({value:'',textContent:'',innerHTML:'',disabled:false,className:'',dataset:{},files:[],click(){this.clicked=true},classList:{remove(){},add(){},toggle(){}}});
const mkCtx=(els,qsa,storage)=>({localStorage:storage||{_s:{},getItem(k){return this._s[k]||null},setItem(k,v){this._s[k]=v},removeItem(k){delete this._s[k]}},
 document:{getElementById:id=>els[id]||(els[id]=mkEl()),querySelectorAll:qsa||(()=>[]),addEventListener(type,fn){(this._listeners||(this._listeners={}))[type]=fn},createElement:()=>({click(){this.clicked=true},set href(v){},set download(v){}})},
 fetch:async()=>({ok:true,json:async()=>({projects:[],mode:'demo',local:[],results:[]})}),
 crypto:{randomUUID:()=>'rnd-'+Math.random().toString(36).slice(2,8)},console,setTimeout,clearTimeout,
 URL:{createObjectURL:()=>'blob:x'},Blob:function(d){this.__data=d&&d[0]},window:{location:{hash:''}}});
const boot=(els,qsa,storage)=>{const c=mkCtx(els,qsa,storage);vm.createContext(c);vm.runInContext(code,c);return c;};
let pass=0,fail=0;
const t=(n,c)=>{try{if(c){pass++;console.log('PASS '+n)}else{fail++;console.log('FAIL '+n)}}catch(e){fail++;console.log('FAIL '+n+' -> '+e.message)}};

const c1=boot({});
let h=c1.resultCard({id:'w1',title:'Kimbell plans',url:'https://example.com/x',type:'web',thumbnail:'https://img/y.jpg'});
t('1a title link', h.includes('<a href="https://example.com/x" target="_blank" rel="noopener noreferrer">Kimbell plans</a>'));
t('1b image link', h.includes('class="result-media"'));
t('1c no undefined', !h.includes('undefined'));
h=c1.resultCard({id:'w2',title:'<img src=x onerror=alert(1)>',url:'javascript:alert(1)',type:'web'});
t('1d escaped', h.includes('&lt;img')&&!h.includes('<img src=x'));
t('1e js-url blocked', !/href="javascript/.test(h));
h=c1.resultCard({id:'w3',title:TRICKY,url:'https://e.com',type:'image'});
const m=h.match(/onclick="([^"]+)"/);
t('1f onclick attr safe', !!m && !/[<>"&]/.test(m[1]));
let dec=null; try{dec=JSON.parse(decodeURIComponent(m[1].match(/decodeURIComponent\('([^']*)'\)/)[1]))}catch(e){}
t('1g payload intact', !!dec && dec.title===TRICKY);
t('2 catSearch wired', html.includes('id="catSearch"') && code.includes("$('catSearch').value"));
t('3 no asset cap', !fs.readFileSync(path.join(dir,'app.py'),'utf8').includes('min(n,8)'));
const els4={}; const c4=boot(els4); await0(vm.runInContext('runSearch()',c4));
t('4 empty-search message', els4.resultGrid.innerHTML.includes('Enter a project, architect'));
const els5={}; const c5=boot(els5);
t('5a save true', vm.runInContext("save({id:'p1'},null)",c5)===true);
const b1=mkEl(); vm.runInContext("save({id:'p2'},__b)",Object.assign(c5,{__b:b1}));
t('5b saved btn', b1.textContent==='\u2713 Saved'&&b1.disabled);
const b2=mkEl(); t('5c dup false', vm.runInContext("save({id:'p2'},__b)",Object.assign(c5,{__b:b2}))===false);

const sbP=mkEl(), sbA=mkEl();
sbP.dataset={sid:'proj1',label:'+ Board'}; sbA.dataset={sid:'asset1',label:'+ Board'};
const els6={}; const c6=boot(els6,()=>[sbP,sbA]);
vm.runInContext("board=[{id:'proj1',title:'Kimbell Art Museum',architect:'Louis Kahn'},{id:'asset1',title:'Plan 1',url:'https://google.com/search?q=x',type:'plan'}];renderBoard();",c6);
const g=els6.boardGrid.innerHTML;
t('6a remove via data-remove', (g.match(/data-remove=/g)||[]).length===2);
t('6b open via data-open', g.includes('data-open="proj1"'));
t('6c open source link', g.includes('href="https://google.com/search?q=x"'));
t('6d titles shown', g.includes('Kimbell Art Museum')&&g.includes('Plan 1'));
vm.runInContext("board=[{id:'proj1',title:'K'},{id:'asset1',title:'A'}];renderBoard();",c6);
sbP.disabled=true; sbA.disabled=true;
vm.runInContext("removeItem('asset1')",c6);
t('6e board=1 after remove', JSON.parse(c6.localStorage.getItem('archscopeBoard')).length===1);
t('6f removed btn re-enabled', sbA.disabled===false && sbA.textContent==='+ Board');
t('6g other stays saved', sbP.disabled===true && sbP.textContent==='\u2713 Saved');
t('6h removal msg', els6.boardMsg.textContent==='Item removed');

const c7=boot({});
const noImg=c7.resultCard({id:'a1',title:'Section 2',type:'section',url:'https://e.com'});
t('7a labelled placeholder', noImg.includes('class="ph"')&&noImg.includes('Section 2'));
t('7b no blank grey div', !noImg.includes('height:170px;background:#e5e1da'));
const withImg=c7.resultCard({id:'a2',title:'Photo 1',type:'photo',thumbnail:'https://img/p.jpg'});
t('7c first photo image', withImg.includes('<img src="https://img/p.jpg"'));

const els8={}; const c8=boot(els8);
vm.runInContext('exportBoard()',c8);
t('8a empty export blocked', els8.boardMsg.textContent.includes('Board is empty')&&els8.boardMsg.className.includes('err'));
vm.runInContext("board=[{id:'e1',title:'X'}];exportBoard()",c8);
t('8b export msg', els8.boardMsg.textContent==='Exported 1 item(s)');
const imp=async(payload)=>{const e={target:{files:[{text:async()=>payload}],value:'f.json'}};await c8.handleImport(e);};

// 9: XSS hardening + resilient storage
vm.runInContext("board=[{id:'proj1',title:'K',architect:'A'}];renderBoard();",c6);
t('9a board markup has no inline onclick', !g.includes('onclick=') && !els6.boardGrid.innerHTML.includes('onclick='));
const evil="x');alert(1);//";
vm.runInContext(`board=[{id:${JSON.stringify(evil)},title:'Evil'}];renderBoard();`,c6);
const eh=els6.boardGrid.innerHTML;
t('9b malicious id escaped (no raw breakout)', !eh.includes("');alert(1)") && eh.includes('data-remove='));
vm.runInContext("board=[{id:'proj1',title:'K',architect:'A'}];renderBoard();",c6);
const li=c6.document._listeners && c6.document._listeners.click;
t('9c delegation listener registered', typeof li==='function');
li({target:{closest:()=>({dataset:{remove:'proj1'}})}});
t('9d delegated remove works', vm.runInContext('board.length',c6)===0);
let opened=null; c6.openProject=id=>{opened=id};
li({target:{closest:()=>({dataset:{open:'p7'}})}});
t('9e delegated open works', opened==='p7');
const badStore={_s:{archscopeBoard:'{not json'},getItem(k){return this._s[k]||null},setItem(k,v){this._s[k]=v},removeItem(k){delete this._s[k]}};
const els9={}; let c9=null;
try{ c9=boot(els9,null,badStore); }catch(e){ t('9f corrupted storage boot', false); }
if(c9){ t('9f corrupted storage boot no throw', true);
  t('9g board reset to empty', vm.runInContext('board.length',c9)===0);
  t('9h reset message shown', els9.boardMsg.textContent.includes('corrupted'));
  t('9i corrupted entry removed', badStore.getItem('archscopeBoard')===null); }

// 10: mode validation + label + architect preservation
const els10={}; const c10=boot(els10);
c10.fetch=async()=>({ok:false,status:400,json:async()=>({error:'Invalid mode. Valid values: all, web, images.'})});
c10.document.getElementById('search').value='test';
(async()=>{
 await vm.runInContext('runSearch()',c10);
 t('10a 400 -> failure message', els10.resultGrid.innerHTML.includes('Search failed'));
 t('10b 400 -> error surfaced in status', els10.status.textContent.includes('Invalid mode'));
 t('10c local card keeps architect', code.includes('architect:x.project.architect'));
 t('10d mode param sent', code.includes('&mode='));
 t('10e catalogue label honest', code.includes("?' Demo catalogue'") && fs.readFileSync(path.join(dir,'app.py'),'utf8').includes("'mode':'demo'"));

 await imp(JSON.stringify([{id:'i1',title:'Imported A',architect:'X'},{id:'e1',title:'dup'}]));
 t('10f import adds unique', JSON.parse(c8.localStorage.getItem('archscopeBoard')).length===2);
 t('10g import msg', els8.boardMsg.textContent==='Imported 1 item(s)');
 await imp('not json');
 t('10h bad file msg', els8.boardMsg.textContent.includes('Import failed'));
 t('10i board unchanged after fail', JSON.parse(c8.localStorage.getItem('archscopeBoard')).length===2);
 t('10j import UI present', html.includes('id="importFile"')&&html.includes('id="boardMsg"'));
 console.log('\n'+pass+' passed, '+fail+' failed'); process.exit(fail?1:0);
})();
function await0(p){ if(p&&typeof p.then==='function') p.then(()=>{}); }
