(() => {
  const API = window.SPACE_AI_API || (location.hostname === 'localhost' || location.hostname === '127.0.0.1' ? location.origin : 'http://localhost:8000');
  const steps = [];
  const $ = id => document.getElementById(id);
  function status(text, good=false){ const el=$('builderStatus'); if(el){ el.textContent=text; el.style.color=good?'#35d59d':''; } }
  function render(){
    $('builderSteps').innerHTML = steps.length ? steps.map((s,i)=>`<div class="builder-step"><span class="builder-num">${i+1}</span><input data-i="${i}" class="step-name" value="${String(s.name).replace(/&/g,'&amp;').replace(/"/g,'&quot;')}"/><button data-remove="${i}" class="btn small">Remove</button></div>`).join('') : '<div class="builder-empty">No steps yet. Add the experiment actions below.</div>';
    document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{steps.splice(Number(b.dataset.remove),1);render();status('Step removed.');});
    document.querySelectorAll('.step-name').forEach(i=>i.onchange=()=>{steps[Number(i.dataset.i)].name=i.value.trim();status('Step edited — review before saving.');});
  }
  function add(name=''){steps.push({name:name||`Step ${steps.length+1}`,description:'',objects:[],interaction:'',required:true});render();}
  async function save(){
    const name=$('experimentName').value.trim();
    if(!name||!steps.length){alert('Enter an experiment name and add at least one step.');return;}
    try{
      status('Saving experiment…');
      const response=await fetch(`${API}/experiments`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,description:$('experimentDescription').value.trim(),steps})});
      const data=await response.json();
      if(!response.ok){alert(data.detail||'Could not save experiment');status('Save failed.');return;}
      status(`Saved: ${data.experiment.name} (${data.experiment.steps.length} steps)`,true);
    }catch(e){status('Backend unavailable — start the local server first.');alert(`Could not reach the Edge AI backend at ${API}.`);}
  }
  async function suggest(){
    const name=$('experimentName').value.trim();
    if(!name){alert('Enter the experiment name first.');$('experimentName').focus();return;}
    // The safe version does not invent a mission-critical protocol. It provides
    // a visible draft placeholder until a verified research/LLM service is connected.
    status('Preparing an AI-assisted draft…');
    setTimeout(()=>{
      status('Step Assistant is ready — enter or confirm the official protocol before training.',true);
      alert(`Step Assistant\n\nExperiment: ${name}\n\nNo verified protocol source is connected yet, so I will not invent mission-critical steps.\n\nNext: add the official steps with “+ Add Step”. We will connect research/LLM-assisted suggestions next.`);
    },250);
  }
  $('addStepBtn').onclick=()=>{add();status('New step added — name it and review it.');};
  $('saveExperimentBtn').onclick=save;
  $('suggestStepsBtn').onclick=suggest;
  add('Pick up container');add('Open container');add('Insert tool');add('Transfer sample');add('Close container');add('Place container back');
})();
