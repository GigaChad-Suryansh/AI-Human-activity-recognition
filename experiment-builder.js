(() => {
  const API = window.SPACE_AI_API || (location.hostname === 'localhost' || location.hostname === '127.0.0.1' ? location.origin : 'http://localhost:8000');
  const steps = [];
  const $ = id => document.getElementById(id);
  function render(){
    $('builderSteps').innerHTML = steps.length ? steps.map((s,i)=>`<div class="builder-step"><span class="builder-num">${i+1}</span><input data-i="${i}" class="step-name" value="${s.name.replace(/&/g,'&amp;').replace(/"/g,'&quot;')}"/><button data-remove="${i}" class="btn small">Remove</button></div>`).join('') : '<div class="builder-empty">No steps yet. Add the experiment actions below.</div>';
    document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{steps.splice(Number(b.dataset.remove),1);render();});
    document.querySelectorAll('.step-name').forEach(i=>i.onchange=()=>steps[Number(i.dataset.i)].name=i.value.trim());
  }
  function add(name=''){steps.push({name:name||`Step ${steps.length+1}`,description:'',objects:[],interaction:'',required:true});render();}
  async function save(){
    const name=$('experimentName').value.trim();
    if(!name||!steps.length){alert('Enter an experiment name and add at least one step.');return;}
    const response=await fetch(`${API}/experiments`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,description:$('experimentDescription').value.trim(),steps})});
    const data=await response.json();
    if(!response.ok){alert(data.detail||'Could not save experiment');return;}
    $('builderStatus').textContent=`Saved: ${data.experiment.name} (${data.experiment.steps.length} steps)`;
  }
  async function suggest(){
    const name=$('experimentName').value.trim();
    if(!name){alert('Enter the experiment name first.');return;}
    $('builderStatus').textContent='AI suggestion placeholder — review and confirm the official protocol before training.';
    // Deliberately does not invent mission-critical protocol steps.
    // A future connected LLM/search service can populate reviewed suggestions here.
  }
  $('addStepBtn').onclick=()=>add();
  $('saveExperimentBtn').onclick=save;
  $('suggestStepsBtn').onclick=suggest;
  add('Pick up container');add('Open container');add('Insert tool');add('Transfer sample');add('Close container');add('Place container back');
})();
