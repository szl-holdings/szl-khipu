/* Read-only, source-bound UI. No canvas pixel scraping, analytics, CDN or persistence. */
const $ = id => document.getElementById(id);
let last = null;
function reset() { last=null; $('download').disabled=true; $('digest').textContent='UNAVAILABLE'; }
function showCord(values) {
  const ns='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(ns,'svg'); const width=600,height=210;
  svg.setAttribute('viewBox',`0 0 ${width} ${height}`); svg.setAttribute('role','img');svg.setAttribute('aria-label','Synthetic vertical cord count illustration');
  const line=(x1,y1,x2,y2,color,width=3)=>{const el=document.createElementNS(ns,'line');for(const[k,v]of Object.entries({x1,y1,x2,y2,stroke:color,'stroke-width':width}))el.setAttribute(k,v);svg.append(el)};
  line(18,23,582,23,'#edbe7f',6);
  values.forEach((v,i)=>{const x=40+(i+.5)*520/values.length;line(x,25,x,166,'#a58e65',3);
    if(v!==null){const s=String(v);s.split('').slice(0,6).forEach((digit,j)=>{
      const y=55+j*20; const c=document.createElementNS(ns,'circle');c.setAttribute('cx',x);c.setAttribute('cy',y);c.setAttribute('r',Math.max(3,Number(digit)*.45+3));c.setAttribute('stroke','#ecc794');c.setAttribute('stroke-width','3');c.setAttribute('fill','#403423');svg.append(c);
    });}
    const txt=document.createElementNS(ns,'text');txt.setAttribute('x',x);txt.setAttribute('y','191');txt.setAttribute('text-anchor','middle');txt.setAttribute('fill','#8dd5bc');txt.setAttribute('font-size','14');txt.textContent=v===null?'?':String(v);svg.append(txt);
  }); $('schematic').replaceChildren(svg);
}
function safeCords(input){const parts=input.split(',').map(v=>v.trim());if(parts.length<1||parts.length>16)throw Error('Enter 1–16 cord values.');return parts.map(v=>{if(v==='?')return null;if(!/^\d{1,6}$/.test(v))throw Error('Enter only integers or ?.');const n=Number(v);if(n>999999)throw Error('Maximum cord value is 999999.');return n;});}
async function jsonResponse(response){const text=await response.text();if(text.length>50000)throw Error('Response budget');const v=JSON.parse(text);if(!response.ok)throw Error(v.reason||`HTTP ${response.status}`);return v;}
function render(out){last=out; const a=out.arithmetic; $('state').textContent=`${a.state} · MODERN DEMONSTRATION`; $('state').style.borderLeftColor=a.state==='REVIEW_MISMATCH'?'#ff9e88':'#63d5ba';$('observed').textContent=a.observed_sum===null?'UNAVAILABLE':String(a.observed_sum);$('declared').textContent=String(a.declared_total);showCord(a.visible_cords);$('answer').textContent=out.route.text;
  const box=$('citations');box.replaceChildren();for(const citation of out.route.citations||[]){if(!citation.url||!/^https:\/\//.test(citation.url))continue;const a=document.createElement('a');a.href=citation.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=`Source: ${citation.id} ↗`;box.append(a);}
  if(out.reference){const label=document.createElement('span');label.textContent=` · ${out.reference.kh_id}: ${out.reference.status}`;box.append(label)}$('digest').textContent=out.response_sha256;$('download').disabled=false;
}
$('form').addEventListener('submit',async e=>{e.preventDefault();reset();$('state').textContent='CHECKING DECLARED INPUT…';try{const cords=safeCords($('cords').value),total=Number($('total').value);if(!Number.isSafeInteger(total)||total<0||total>15999984)throw Error('Invalid declared total');const id=$('khid').value.trim().toUpperCase();const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cords,declared_total:total,question:$('question').value,kh_id:id||null})});render(await jsonResponse(response));}catch(err){$('state').textContent='UNAVAILABLE · '+String(err.message||err);$('answer').textContent='No evidence from this request.';}});
$('download').addEventListener('click',()=>{if(!last)return;const blob=new Blob([JSON.stringify(last,null,2)],{type:'application/json'});const u=URL.createObjectURL(blob);const a=document.createElement('a');a.download='khipu-yachay-synthetic-receipt.json';a.href=u;a.click();setTimeout(()=>URL.revokeObjectURL(u),2000);});
let searchTimer;$('find').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(loadSources,180)});
async function loadSources(){try{const r=await jsonResponse(await fetch('/api/sources?q='+encodeURIComponent($('find').value.slice(0,80))));const cards=$('sourcecards');cards.replaceChildren();for(const s of r.sources){const card=document.createElement('article');card.className='sourcecard';const t=document.createElement('strong');t.textContent=s.title;const sub=document.createElement('span');sub.textContent=`${s.attribution} · ${s.content_admission} · no bulk training`;const a=document.createElement('a');a.textContent='Open primary source ↗';a.href=s.url;a.target='_blank';a.rel='noopener noreferrer';card.append(t,sub,a);cards.append(card);}}catch(e){$('sourcecards').textContent='Source catalogue unavailable';}}
showCord([12,5,8]);loadSources();
