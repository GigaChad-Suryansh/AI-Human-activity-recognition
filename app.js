const STEPS=[
  {name:'Pick up container',interaction:'Hand → Container'},
  {name:'Open container',interaction:'Hand → Container'},
  {name:'Insert tool',interaction:'Hand → Tool'},
  {name:'Transfer sample',interaction:'Hand → Sample'},
  {name:'Close container',interaction:'Hand → Container'},
  {name:'Place container back',interaction:'Hand → Rack'}
];
const API_BASE=localStorage.getItem('SPACE_AI_API')||'http://localhost:8000';
const WS_URL=API_BASE.replace(/^http/,'ws')+'/ws/inference';
let state={current:-1,running:false,skipped:false,stream:null,videoURL:null,events:[],ws:null,inferenceTimer:null,lastInference:0,lastResult:null,inputMode:null};
const $=id=>document.getElementById(id);
function now(){return new Date().toLocaleTimeString([], {hour12:false});}
function escapeHtml(s){return String(s).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#039;'}[c]));}
function log(message,type='ok'){const e={timestamp:new Date().toISOString(),message,type};state.events.unshift(e);const el=document.createElement('div');el.className=`event ${type}`;el.innerHTML=`<time>${now()}</time>${escapeHtml(message)}`;$('eventLog').prepend(el);}
function toast(t){$('toast').textContent=t;$('toast').classList.add('show');setTimeout(()=>$('toast').classList.remove('show'),2200)}
function speak(text){$('voiceStatus').textContent='SPEAKING';try{if('speechSynthesis'in window){speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.rate=.95;u.onend=()=>{$('voiceStatus').textContent='READY'};speechSynthesis.speak(u)}else $('voiceStatus').textContent='UNAVAILABLE'}catch{$('voiceStatus').textContent='ERROR'}}
function renderSteps(){$('stepList').innerHTML=STEPS.map((s,i)=>{let cls=i<state.current?'done':i===state.current?'current':'';if(state.skipped&&i===state.current)cls='error';return `<div class="step ${cls}"><div class="num">${i<state.current?'✓':i+1}</div><div><b>${s.name}</b><small>${i<state.current?'Completed':i===state.current?'In progress':'Pending'}</small></div></div>`}).join('');}
function setConfidence(n){n=Math.max(0,Math.min(100,n));$('confidence').textContent=`${Math.round(n)}%`;$('confidenceBar').style.width=`${n}%`;}
function updateUI(){
  renderSteps();
  if(state.current<0){$('activity').textContent='—';$('expected').textContent='—';$('interaction').textContent='—';$('sequence').textContent='—';$('nextStep').textContent='Start experiment';$('stateBadge').textContent='STANDBY';$('stateBadge').className='badge neutral';$('persons').textContent='0';$('objects').textContent='0';$('latency').textContent='—';$('aiHud').textContent='AI: STANDBY';setConfidence(0);return}
  const s=STEPS[state.current];
  $('activity').textContent=state.lastResult?.activity||s.name;
  $('expected').textContent=s.name;
  $('interaction').textContent=state.lastResult?.interaction?`${state.lastResult.interaction.hand} hand → ${state.lastResult.interaction.object}`:s.interaction;
  $('nextStep').textContent=STEPS[state.current+1]?.name||'Experiment complete';
  $('sequence').textContent=state.skipped?'PROTOCOL VIOLATION':'CORRECT';
  $('sequence').className=state.skipped?'':'green-text';
  $('stateBadge').textContent=state.skipped?'PROTOCOL ERROR':state.current===STEPS.length-1?'COMPLETE':'IN PROGRESS';
  $('stateBadge').className=`badge ${state.skipped?'neutral':'blue'}`;
  $('persons').textContent=state.lastResult?.persons??(state.running?1:0);
  $('objects').textContent=state.lastResult?.objects??0;
  $('latency').textContent=state.lastResult?`${state.lastResult.latency_ms} ms`:'—';
  $('aiHud').textContent=state.ws?.readyState===1?'AI: YOLO + POSE / LIVE':'AI: BACKEND OFFLINE';
}
function connectBackend(){
  if(state.ws&&state.ws.readyState===1)return;
  try{
    state.ws=new WebSocket(WS_URL);
    state.ws.onopen=()=>{log('Edge AI backend connected');$('network').textContent='CONNECTED';$('systemPill').innerHTML='<i></i> EDGE AI CONNECTED';$('systemPill').className='pill good';startInference();};
    state.ws.onmessage=e=>{try{const r=JSON.parse(e.data);if(r.type==='error'){log(`Inference error: ${r.message}`,'bad');return}state.lastResult=r;setConfidence((r.confidence||0)*100);updateUI();drawOverlay(r);}catch(err){log(`Invalid backend response: ${err.message}`,'bad');}};
    state.ws.onerror=()=>{log('Backend connection failed — running local UI mode','warn');$('network').textContent='OFFLINE';$('aiHud').textContent='AI: BACKEND OFFLINE';};
    state.ws.onclose=()=>{state.ws=null;stopInference();$('network').textContent='OFFLINE';updateUI();};
  }catch(e){log('WebSocket unavailable — UI-only mode','warn');}
}
function startInference(){stopInference();state.inferenceTimer=setInterval(()=>sendFrame(),250);}
function stopInference(){if(state.inferenceTimer)clearInterval(state.inferenceTimer);state.inferenceTimer=null;}
function sendFrame(){
  if(!state.ws||state.ws.readyState!==1)return;
  const v=$('camera');
  if(!v||!v.videoWidth||!v.videoHeight)return;
  const c=document.createElement('canvas');
  const scale=Math.min(1,640/v.videoWidth);
  c.width=Math.max(1,Math.round(v.videoWidth*scale));
  c.height=Math.max(1,Math.round(v.videoHeight*scale));
  c.getContext('2d').drawImage(v,0,0,c.width,c.height);
  const jpeg=c.toDataURL('image/jpeg',.72);
  state.ws.send(JSON.stringify({frame:jpeg}));
}
function drawOverlay(r){const canvas=$('overlay'),v=$('camera');if(!v.videoWidth)return;canvas.width=v.videoWidth;canvas.height=v.videoHeight;const ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);ctx.lineWidth=3;ctx.font='14px monospace';(r.detections||[]).forEach(d=>{const [x1,y1,x2,y2]=d.box;ctx.strokeStyle=d.label==='person'?'#4db7ff':'#35d59d';ctx.strokeRect(x1,y1,x2-x1,y2-y1);ctx.fillStyle=ctx.strokeStyle;ctx.fillText(`${d.label} ${(d.confidence*100).toFixed(0)}%`,x1,Math.max(15,y1-5));});(r.hands||[]).forEach(h=>{ctx.fillStyle='#ffbe55';ctx.beginPath();ctx.arc(h.x,h.y,8,0,Math.PI*2);ctx.fill();});}
async function startCamera(){
  // If a video file is loaded, use it instead of asking for the broken webcam.
  if(state.videoURL){
    state.inputMode='video';
    const v=$('camera');
    $('cameraPlaceholder').style.display='none';
    $('cameraBtn').textContent='Video Loaded';
    $('cameraStatus').textContent='Video file input';
    try{await v.play();log('Video playback started — using loaded video as camera input');}catch(e){log('Video playback requires a click — press play on the video controls','warn');}
    connectBackend();
    return;
  }
  if(state.stream){stopCamera();return}
  try{
    state.stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720},facingMode:'user'},audio:false});
    state.inputMode='camera';
    $('camera').srcObject=state.stream;
    $('cameraPlaceholder').style.display='none';
    $('cameraBtn').textContent='Stop Camera';
    $('cameraStatus').textContent='Camera connected';
    log('Camera connected — local video input active');
    connectBackend();
  }catch(e){
    $('cameraStatus').textContent=state.videoURL?'Video file input':'Camera unavailable';
    toast(state.videoURL?'Using loaded video instead':'Camera hardware/permission unavailable');
    log(state.videoURL?'Webcam unavailable — loaded video remains available':'Camera unavailable — use Load Video or check browser permission','warn');
  }
}
function stopCamera(){if(state.stream){state.stream.getTracks().forEach(t=>t.stop());state.stream=null}$('camera').srcObject=null;$('cameraBtn').textContent=state.videoURL?'Video Loaded':'Start Camera';$('cameraStatus').textContent=state.videoURL?'Video file input':'Camera idle';stopInference();}
function startExperiment(){state.running=true;state.current=0;state.skipped=false;$('startBtn').textContent='⏭ Confirm / Next Step';$('systemPill').innerHTML='<i></i> EXPERIMENT ACTIVE';$('recordStatus').textContent='MONITORING';log('Experiment EXP-DEMO-001 started');log(`EXPECTED STEP 1 — ${STEPS[0].name}`,'warn');updateUI();if(state.videoURL){state.inputMode='video';$('cameraPlaceholder').style.display='none';connectBackend();const v=$('camera');v.play().then(()=>log('Loaded video playback active — frames sent to Edge AI')).catch(()=>log('Video playback blocked until Play is pressed','warn'));}else if(!state.stream)startCamera();}
function advance(){if(!state.running){startExperiment();return}if(state.current>=STEPS.length-1){log('Experiment complete — all predefined steps processed');return}state.skipped=false;log(`STEP ${state.current+1} CONFIRMED — ${STEPS[state.current].name}`);state.current++;log(`EXPECTED STEP ${state.current+1} — ${STEPS[state.current].name}`,'warn');updateUI();}
function simulateSkip(){if(!state.running){startExperiment();return}const expected=STEPS[state.current];const detected=STEPS[state.current+1];if(!detected)return;state.skipped=true;updateUI();log(`WARNING — expected ${expected.name}; detected ${detected.name}`,'bad');speak(`Warning. ${expected.name} was not completed. Please perform ${expected.name}.`);toast('Protocol violation detected');}
function reset(){stopCamera();if(state.ws){state.ws.close();state.ws=null}if(state.videoURL){URL.revokeObjectURL(state.videoURL)}state={current:-1,running:false,skipped:false,stream:null,videoURL:null,events:[],ws:null,inferenceTimer:null,lastInference:0,lastResult:null,inputMode:null};const v=$('camera');v.removeAttribute('src');v.load();v.controls=false;$('cameraPlaceholder').style.display='grid';$('cameraBtn').textContent='Start Camera';$('cameraStatus').textContent='Camera idle';$('recordStatus').textContent='READY';$('systemPill').innerHTML='<i></i> SYSTEM READY';$('systemPill').className='pill good';$('eventLog').innerHTML='';updateUI();log('System reset — awaiting experiment');}
function snapshot(){const v=$('camera');if(!v.videoWidth){toast('Start the camera or load a video first');return}const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);const a=document.createElement('a');a.href=c.toDataURL('image/jpeg',.9);a.download=`experiment_${Date.now()}.jpg`;a.click();log('Camera snapshot captured');}
$('startBtn').onclick=()=>state.running?advance():startExperiment();
$('resetBtn').onclick=reset;
$('cameraBtn').onclick=startCamera;
$('snapshotBtn').onclick=snapshot;
$('videoFile').onchange=async e=>{
  const f=e.target.files[0];
  if(!f)return;
  if(state.stream)stopCamera();
  if(state.videoURL)URL.revokeObjectURL(state.videoURL);
  state.videoURL=URL.createObjectURL(f);
  state.inputMode='video';
  const v=$('camera');
  v.srcObject=null;
  v.src=state.videoURL;
  v.controls=true;
  v.muted=true;
  v.playsInline=true;
  $('cameraPlaceholder').style.display='none';
  $('cameraStatus').textContent=`Loaded: ${f.name}`;
  log(`Video file loaded — ${f.name}`);
  toast('Video loaded — starting playback');
  try{await v.play();log('Video playback started');}catch(err){log('Autoplay blocked — press Play on the video controls','warn');}
  connectBackend();
};
$('camera').addEventListener('loadedmetadata',()=>{if(state.videoURL){$('cameraPlaceholder').style.display='none';$('cameraStatus').textContent='Video file input ready';updateUI();}});
$('camera').addEventListener('play',()=>{if(state.videoURL){state.inputMode='video';connectBackend();log('Video playing — Edge AI frame pipeline active');}});
$('downloadLog').onclick=()=>{const data=state.events.map(e=>JSON.stringify(e)).join('\n');const blob=new Blob([data+'\n'],{type:'application/x-ndjson'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='events.jsonl';a.click();};
$('fullscreenBtn').onclick=()=>document.documentElement.requestFullscreen?.();
updateUI();
log(`Offline console initialized — backend target ${API_BASE}`);
