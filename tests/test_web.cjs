// Unit-level replay checks without launching or controlling a browser.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(root, 'output/simulation.json'), 'utf8'));
const elements = new Map();
const context2d = new Proxy({}, {get: (target, key) => target[key] || (()=>{}), set: (target,key,value) => (target[key]=value,true)});
function element() { return {value:'', disabled:true, textContent:'', children:[], style:{}, append(...a){this.children.push(...a);}, replaceChildren(){this.children=[];}, getContext(){return context2d;}}; }
const document = {getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id);},createElement:element,createTextNode:text=>({textContent:text})};
document.getElementById('map').width=900;document.getElementById('map').height=700;
document.getElementById('layer').value='simulation';document.getElementById('speed').value='1';
const box = vm.createContext({document,location:{protocol:'file:'},requestAnimationFrame:()=>{},console});
vm.runInContext(fs.readFileSync(path.join(root,'web/app.js'),'utf8'),box);
box.input=data;vm.runInContext('load(input)',box);
const run = script => vm.runInContext(script,box);
assert.match(elements.get('status').textContent,/Ready/);
assert.equal(run('index'),0);
run("$('next').onclick()");assert.equal(run('index'),1);
run("$('prev').onclick()");assert.equal(run('index'),0);
run("$('timeline').oninput({target:{value:'30'}})");assert.equal(run('index'),30);
assert.match(elements.get('frame').textContent,/Frame 31/);
run("$('play').onclick(); tick(1000); tick(2100)");assert.equal(run('index'),31);
run("$('pause').onclick(); tick(5000)");assert.equal(run('index'),31);
run("$('restart').onclick()");assert.equal(run('index'),0);assert.equal(run('playing'),false);
for (const layer of ['elevation','slope','fos','risk','simulation']) {elements.get('layer').value=layer;run('render()');assert.ok(elements.get('legend').children.length>0);}
run("$('vectors').checked=true; render(); seek(data.frames.length-1); $('play').onclick()");assert.equal(run('index'),0);
run('seek(data.frames.length-2); $("play").onclick(); tick(0); tick(10000)');assert.equal(run('index'),data.frames.length-1);assert.equal(run('playing'),false);
assert.throws(()=>run('load({})'),/Expected/);
const theta=data.terrain.slope[50][50];box.theta=theta;box.m=data.frames.at(-1).saturation;
const expected=JSON.parse(fs.readFileSync(path.join(root,'output/risk_map.json'),'utf8')).factor_of_safety[50][50];
assert.ok(Math.abs(run('fos(theta,m)')-expected)<1e-10);
console.log('PASS: JSON loading, all layers, vectors, Play/Pause/Restart/Previous/Next/timeline, final-frame stop, invalid input, Python/JS FoS parity. DOM/canvas stub only; no visual browser test.');
