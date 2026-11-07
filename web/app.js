'use strict';
const $ = id => document.getElementById(id);
const canvas = $('map'), ctx = canvas.getContext('2d');
const colors = ['#c54b38', '#e99c3a', '#ded172', '#6d9a7b'];
const labels = ['Unstable', 'High risk', 'Moderate risk', 'Relatively stable'];
let data = null, index = 0, playing = false, lastTick = null, elapsed = 0;

function validate(d) {
  if (d?.metadata?.version !== 1 || !d.terrain || !d.parameters || !Array.isArray(d.frames) || !d.frames.length) throw Error('Expected a version 1 simulation.json');
  const t = d.terrain, p = d.parameters;
  if (!Number.isInteger(t.rows) || !Number.isInteger(t.cols) || t.rows < 2 || t.cols < 2 || t.rows*t.cols > 250000 || !(t.cell_size > 0)) throw Error('Invalid terrain dimensions');
  const matrix = a => Array.isArray(a) && a.length === t.rows && a.every(row => Array.isArray(row) && row.length === t.cols && row.every(Number.isFinite));
  for (const k of ['elevation','slope','direction_x','direction_y','risk']) if (!matrix(t[k])) throw Error(`Invalid terrain ${k}`);
  for (const k of ['cohesion','soil_unit_weight','soil_depth','water_unit_weight','friction_angle','epsilon','flat_fos','simulation_duration','rainfall_duration_hours','rainfall_mm_per_hour']) if (!Number.isFinite(p[k])) throw Error(`Invalid parameter ${k}`);
  if (!Array.isArray(p.risk_thresholds) || p.risk_thresholds.length !== 3 || !p.risk_thresholds.every(Number.isFinite)) throw Error('Invalid risk thresholds');
  let previous = -1;
  for (const f of d.frames) {
    if (!Number.isFinite(f.time) || f.time <= previous || !Number.isFinite(f.saturation) || f.saturation < 0 || f.saturation > 1 || !Number.isFinite(f.rainfall_time_hours) || !Number.isFinite(f.minimum_fos) || !Number.isFinite(f.unstable_cells) || !Number.isFinite(f.moving_particles)) throw Error('Invalid frame values');
    if (!Array.isArray(f.particles) || f.particles.length > 2000 || !f.particles.every(a => Array.isArray(a) && a.length === 5 && a.every(Number.isFinite))) throw Error('Invalid particles');
    previous = f.time;
  }
}

function load(d) {
  validate(d); pause(); data = d; index = 0;
  $('timeline').max = d.frames.length - 1;
  for (const id of ['play','pause','restart','prev','next','timeline']) $(id).disabled = false;
  $('empty').hidden = true;
  $('status').textContent = `Ready · ${d.terrain.rows} × ${d.terrain.cols} cells · ${d.frames.length} saved frames`;
  const p = d.parameters;
  const entries = [['Rainfall', `${p.rainfall_mm_per_hour} mm/h`],['Rainfall exposure', `${p.rainfall_duration_hours} hours`],['Motion duration', `${p.simulation_duration} seconds`],['Grid spacing', `${d.terrain.cell_size} m`],['Cohesion', `${p.cohesion} kPa`],['Friction angle', `${p.friction_angle}°`],['Soil depth', `${p.soil_depth} m`]];
  $('parameters').replaceChildren();
  for (const [name, value] of entries) { const dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = name; dd.textContent = value; $('parameters').append(dt, dd); }
  render();
}

function fos(theta, m) {
  const p = data.parameters, cos = Math.cos(theta), den = p.soil_unit_weight*p.soil_depth*Math.sin(theta)*cos;
  return den > p.epsilon ? (p.cohesion+(p.soil_unit_weight-m*p.water_unit_weight)*p.soil_depth*cos*cos*Math.tan(p.friction_angle*Math.PI/180))/den : p.flat_fos;
}
function risk(fs) { const n = data.parameters.risk_thresholds.findIndex(t => fs < t); return n < 0 ? 3 : n; }
function legend(items) {
  $('legend').replaceChildren();
  for (const [color, label] of items) { const key = document.createElement('span'), swatch = document.createElement('i'); key.className = 'key'; swatch.className = 'swatch'; swatch.style.background = color; key.append(swatch, document.createTextNode(label)); $('legend').append(key); }
}
function render() {
  if (!data) return;
  const t = data.terrain, f = data.frames[index], layer = $('layer').value;
  const terrainWidth = (t.cols-1)*t.cell_size, terrainHeight = (t.rows-1)*t.cell_size;
  const scale = Math.min((canvas.width-60)/terrainWidth, (canvas.height-60)/terrainHeight);
  const w = terrainWidth*scale, h = terrainHeight*scale, ox = (canvas.width-w)/2, oy = (canvas.height-h)/2;
  ctx.fillStyle = '#e6ede1'; ctx.fillRect(0,0,canvas.width,canvas.height);
  let low = Infinity, high = -Infinity;
  for (const row of t.elevation) for (const z of row) { low = Math.min(low,z); high = Math.max(high,z); }
  // Grid nodes are at x=j*cell_size, y=i*cell_size; edge cells are half-width.
  for (let i=0; i<t.rows; i++) for (let j=0; j<t.cols; j++) {
    const z = (t.elevation[i][j]-low)/Math.max(1e-10,high-low), theta = t.slope[i][j], fs = fos(theta,f.saturation);
    let color;
    if (layer === 'risk' || layer === 'simulation') color = colors[risk(fs)];
    else if (layer === 'slope') color = `hsl(${60-60*Math.min(theta/(Math.PI/3),1)} 65% ${85-45*Math.min(theta/(Math.PI/3),1)}%)`;
    else if (layer === 'fos') color = `hsl(${Math.min(fs/2,1)*125} 48% 57%)`;
    else color = `hsl(${160-z*115} ${28+z*15}% ${28+z*48}%)`;
    const x0 = Math.max(0,j-.5)*t.cell_size*scale, y0 = Math.max(0,i-.5)*t.cell_size*scale;
    const x1 = Math.min(t.cols-1,j+.5)*t.cell_size*scale, y1 = Math.min(t.rows-1,i+.5)*t.cell_size*scale;
    ctx.fillStyle = color; ctx.fillRect(ox+x0,oy+y0,x1-x0+.3,y1-y0+.3);
  }
  if ($('vectors').checked) {
    ctx.strokeStyle = '#183329aa'; ctx.lineWidth = 1.2;
    const stride = Math.max(1,Math.ceil(Math.max(t.rows,t.cols)/14));
    for (let i=1;i<t.rows-1;i+=stride) for (let j=1;j<t.cols-1;j+=stride) {
      const dx=t.direction_x[i][j],dy=t.direction_y[i][j]; if (Math.hypot(dx,dy)<.01) continue;
      const x=ox+j*t.cell_size*scale,y=oy+i*t.cell_size*scale,ex=x+dx*13,ey=y+dy*13;
      ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(ex,ey);ctx.lineTo(ex-dx*4+dy*3,ey-dy*4-dx*3);ctx.moveTo(ex,ey);ctx.lineTo(ex-dx*4-dy*3,ey-dy*4+dx*3);ctx.stroke();
    }
  }
  if (layer === 'simulation') for (const [x,y,vx,vy,active] of f.particles) {
    ctx.beginPath();ctx.arc(ox+x*scale,oy+y*scale,active?2.7:1.8,0,Math.PI*2);ctx.fillStyle=active?'#fff':'#273a30';ctx.fill();ctx.strokeStyle='#273a30';ctx.lineWidth=.7;ctx.stroke();
  }
  if (layer==='risk'||layer==='simulation') { const a=data.parameters.risk_thresholds;legend(colors.map((color,k)=>[color,`${labels[k]} (${k===0?'< '+a[0]:k===3?'≥ '+a[2]:a[k-1]+'–<'+a[k]})`])); }
  else if(layer==='elevation') legend([['#32634f',`Low ${low.toFixed(1)} m`],['#dfdba7',`High ${high.toFixed(1)} m`]]);
  else if(layer==='slope') legend([['#f2f2c0','0° · flat'],['#af2424','60°+ · steep']]);
  else legend([['#c65e5e','0 · unstable'],['#62c65e','2+ · stable (color capped)']]);
  $('timeline').value=index;$('clock').textContent=`Motion ${f.time.toFixed(1)} s / Rainfall ${f.rainfall_time_hours.toFixed(2)} h`;
  $('frame').textContent=`Frame ${index+1} / ${data.frames.length}`;
  $('saturation').textContent=`${(f.saturation*100).toFixed(1)}%`;$('water').value=f.saturation;
  $('minimum').textContent=f.minimum_fos.toFixed(3);$('unstable').textContent=f.unstable_cells.toLocaleString();$('moving').textContent=f.moving_particles.toLocaleString();
}
function pause(){playing=false;lastTick=null;elapsed=0;$('play').textContent='▶ Play';}
function seek(i){pause();if(data){index=Math.max(0,Math.min(data.frames.length-1,i));render();}}
$('play').onclick=()=>{if(!data)return;if(index===data.frames.length-1)index=0;playing=true;lastTick=null;$('play').textContent='▶ Playing';render();};
$('pause').onclick=pause;$('restart').onclick=()=>seek(0);$('prev').onclick=()=>seek(index-1);$('next').onclick=()=>seek(index+1);
$('timeline').oninput=e=>seek(Number(e.target.value));$('layer').onchange=render;$('vectors').onchange=render;
$('file').onchange=async e=>{try{const file=e.target.files[0];if(file)load(JSON.parse(await file.text()));}catch(error){$('status').textContent=`Could not load file: ${error.message}`;}};
function tick(now){
  if(playing&&data){if(lastTick!==null)elapsed+=(now-lastTick)/1000*Number($('speed').value);lastTick=now;
    while(index<data.frames.length-1&&elapsed>=data.frames[index+1].time-data.frames[index].time){elapsed-=data.frames[index+1].time-data.frames[index].time;index++;render();}
    if(index===data.frames.length-1)pause();
  }requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
if(location.protocol==='file:')$('status').textContent='Offline mode: select output/simulation.json below.';
else fetch('../output/simulation.json').then(r=>{if(!r.ok)throw Error(`HTTP ${r.status}`);return r.json();}).then(load).catch(error=>{$('status').textContent=`Default data unavailable (${error.message}). Run python main.py or select a JSON file.`;});
