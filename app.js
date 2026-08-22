const STEPS=[
  {name:'Pick up container',interaction:'Hand → Container'},
  {name:'Open container',interaction:'Hand → Container'},
  {name:'Insert tool',interaction:'Hand → Tool'},
  {name:'Transfer sample',interaction:'Hand → Sample'},
  {name:'Close container',interaction:'Hand → Container'},
  {name:'Place container back',interaction:'Hand → Rack'}
];
let state={current:-1,running:false,skipped:false,stream:null,videoURL:null,events:[],recording:false,recorder:null,chunks:[]};
const $=id=>document.getElementById(id);
function now(){return new Date().toLocaleTimeString([], {hour12:false});}
function log(message,type='ok'){
  const e={timestamp:new Date().toISOString(),message,type};state.events.unshift(e);
  const el=document.createElement('div');el.className=`event ${type}`;el.innerHTML=`<time>${now()}</time>${escapeHtml(message)}`;$('eventLog').prepend(el);
}
function escapeHtml(s){return s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));}
function renderSteps(){
  $('stepList').innerHTML=STEPS.map((s,i)=>{let cls=i<state.current?'done':i===state.current?'current':'';if(state.skipped&&i===state.current)cls='error';return `<div class="step ${cls}"><div class="num">${i<state.current?'✓':i+1}</div><div><b>${s.name}</b><small>${i<state.current?'Completed':i===state.current?'In progress':'Pending'}</small></div></div>`}).join('');
}
function setConfidence(n){$('confidence').textContent=`${n}%`;$('confidenceBar').style.width=`${n}%`;}
function updateUI(){
 renderSteps();
 if(state.current<0){$('activity').textContent='—';$('expected').textContent='—';$('interaction').textContent='—';$('sequence').textContent='—';$('nextStep').textContent='Start experiment';$('stateBadge').textContent='STANDBY';$('stateBadge').className='badge neutral';setConfidence(0);return}
 const s=STEPS[state.current];$('activity').textContent=s.name;$('expected').textContent=s.name;$('interaction').textContent=s.interaction;$('nextStep').textContent=STEPS[state.current+1]?.name||'Experiment complete';
 $('sequence').textContent=state.skipped?'STEP SKIPPED':'CORRECT';$('sequence').className=state.skipped?'':'green-text';$('stateBadge').textContent=state.skipped?'PROTOCOL ERROR':state.current===STEPS.length-1?'COMPLETE':'IN PROGRESS';$('stateBadge').className=`badge ${state.skipped?'neutral':'blue'}`;
 $('persons').textContent=state.running?'1':'0';$('objects').textContent=state.running?'3':'0';$('latency').textContent=state.running?`${35+Math.floor(Math.random()*25)} ms`:'—';
 $('aiHud').textContent=state.running?'AI: TRACKING / SEQUENCE VALIDATION':'AI: STANDBY';
}
function speak(text){$('voiceStatus').textContent='SPEAKING';try{if('speechSynthesis'in window){speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.rate=.95;u.onend=()=>{$('voiceStatus').textContent='READY'};speechSynthesis.speak(u)}else $('voiceStatus').textContent='UNAVAILABLE'}catch{$('voiceStatus').textContent='ERROR'}}
function toast(t){$('toast').textContent=t;$('toast').classList.add('show');setTimeout(()=>$('toast').classList.remove('show'),2200)}
async function startCamera(){
 if(state.stream){state.stream.getTracks().forEach(t=>t.stop());state.stream=null;$('camera').srcObject=null;$('cameraBtn').textContent='Start Camera';$('cameraStatus').textContent='Camera idle';return}
 try{state.stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720},facingMode:'user'},audio:false});$('camera').srcObject=state.stream;$('cameraPlaceholder').style.display='none';$('cameraBtn').textContent='Stop Camera';$('cameraStatus').textContent='Camera connected';log('Camera connected — local video input active');}catch(e){toast('Camera permission unavailable');log('Camera unavailable — demo simulation remains active','warn');}
}
function startExperiment(){
 state.running=true;state.current=0;state.skipped=false;$('startBtn').textContent='⏸ Experiment Running';$('systemPill').innerHTML='<i></i> AI PIPELINE ACTIVE';$('systemPill').className='pill good';$('recordStatus').textContent='RECORDING';log('Experiment EXP-DEMO-001 started');log(`STEP 1 DETECTED — ${STEPS[0].name}`);updateUI();setConfidence(93);toast('Experiment started');
 if(!state.stream)startCamera();
}
function advance(){
 if(!state.running){startExperiment();return}
 if(state.current>=STEPS.length-1){log('Experiment already complete','warn');return}
 state.skipped=false;log(`STEP ${state.current+1} CONFIRMED — ${STEPS[state.current].name} — COMPLETED`);state.current++;setConfidence(90+Math.floor(Math.random()*9));updateUI();log(`NEXT STEP — ${STEPS[state.current].name}`,'warn');
 if(state.current===STEPS.length-1)log('FINAL STEP IN PROGRESS — prepare completion check','warn');
}
function simulateSkip(){
 if(!state.running){startExperiment();return}
 const expected=STEPS[state.current];const detected=STEPS[state.current+1];if(!detected){log('No later step available — experiment is complete','warn');return}
 state.skipped=true;updateUI();setConfidence(96);const msg=`Warning. ${expected.name} has been skipped. Please perform ${expected.name}.`;log(`WARNING — expected ${expected.name}; detected ${detected.name}`,'bad');speak(msg);toast('Protocol violation detected');
}
function reset(){if(state.stream){state.stream.getTracks().forEach(t=>t.stop());state.stream=null;$('camera').srcObject=null}$('cameraPlaceholder').style.display='grid';$('cameraBtn').textContent='Start Camera';state={current:-1,running:false,skipped:false,stream:null,videoURL:null,events:[],recording:false,recorder:null,chunks:[]};$('eventLog').innerHTML='';$('recordStatus').textContent='READY';$('systemPill').innerHTML='<i></i> SYSTEM READY';$('systemPill').className='pill good';updateUI();log('System reset — awaiting experiment');}
function snapshot(){const v=$('camera');if(!v.videoWidth){toast('Start the camera first');return}const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);const a=document.createElement('a');a.href=c.toDataURL('image/jpeg',.9);a.download=`experiment_${Date.now()}.jpg`;a.click();log('Camera snapshot captured');}
$('startBtn').onclick=()=>state.running?advance():startExperiment();$('resetBtn').onclick=reset;$('cameraBtn').onclick=startCamera;$('snapshotBtn').onclick=snapshot;$('simulateBtn')?.addEventListener('click',advance);
$('videoFile').onchange=e=>{const f=e.target.files[0];if(!f)return;if(state.videoURL)URL.revokeObjectURL(state.videoURL);state.videoURL=URL.createObjectURL(f);$('camera').srcObject=null;$('camera').src=state.videoURL;$('camera').controls=true;$('cameraPlaceholder').style.display='none';$('cameraStatus').textContent=`Loaded: ${f.name}`;log(`Video file loaded — ${f.name}`);toast('Video loaded');};
$('downloadLog').onclick=()=>{const data=state.events.map(e=>JSON.stringify(e)).join('\n');const blob=new Blob([data+'\n'],{type:'application/x-ndjson'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='events.jsonl';a.click();URL.revokeObjectURL(a.href);};
$('fullscreenBtn').onclick=()=>document.documentElement.requestFullscreen?.();
updateUI();log('Offline AI console initialized');
