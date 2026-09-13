(() => {
  const API = window.SPACE_AI_API || (location.hostname === 'localhost' || location.hostname === '127.0.0.1' ? location.origin : 'http://localhost:8000');
  const steps = [];
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  function status(text, good=false){
    const el=$('builderStatus');
    if(el){ el.textContent=text; el.style.color=good?'#35d59d':''; }
  }

  function render(){
    $('builderSteps').innerHTML = steps.length
      ? steps.map((s,i)=>`<div class="builder-step"><span class="builder-num">${i+1}</span><input data-i="${i}" class="step-name" value="${esc(s.name)}"/><button data-remove="${i}" class="btn small">Remove</button></div>`).join('')
      : '<div class="builder-empty">No steps yet. Add the experiment actions below.</div>';
    document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{steps.splice(Number(b.dataset.remove),1);render();status('Step removed — review before saving.');});
    document.querySelectorAll('.step-name').forEach(i=>i.onchange=()=>{steps[Number(i.dataset.i)].name=i.value.trim();status('Step edited — review before saving.');});
  }

  function add(step={}){
    steps.push({
      id: step.id || `step-${steps.length+1}`,
      name: step.name || `Step ${steps.length+1}`,
      description: step.description || '',
      objects: Array.isArray(step.objects) ? step.objects : [],
      interaction: step.interaction || '',
      required: step.required !== false
    });
    render();
  }

  async function save(){
    const name=$('experimentName').value.trim();
    if(!name||!steps.length){alert('Enter an experiment name and add at least one step.');return;}
    try{
      status('Saving experiment…');
      const response=await fetch(`${API}/experiments`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,description:$('experimentDescription').value.trim(),steps,verification:'human-verified',source:'user-reviewed'})});
      const data=await response.json();
      if(!response.ok){alert(data.detail||'Could not save experiment');status('Save failed.');return;}
      status(`Saved: ${data.experiment.name} (${data.experiment.steps.length} steps)`,true);
    }catch(e){status('Backend unavailable — start the local server first.');alert(`Could not reach the Edge AI backend at ${API}.`);}
  }

  function showDraft(suggestion){
    steps.splice(0,steps.length,...suggestion.steps);
    render();
    status(`AI draft ready — ${steps.length} steps. Review and edit before saving.`,true);
    alert(`AI Step Assistant\n\nExperiment: ${suggestion.name}\n\n${suggestion.warning}\n\nDraft basis: ${suggestion.basis}\n\nI added ${steps.length} proposed steps to the builder. Review, edit, remove, or add steps before saving.`);
  }

  async function suggest(){
    const name=$('experimentName').value.trim();
    if(!name){alert('Enter the experiment name first.');$('experimentName').focus();return;}
    try{
      status('Generating an offline AI-assisted draft…');
      const response=await fetch(`${API}/experiments/suggest`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,description:$('experimentDescription').value.trim()})});
      const data=await response.json();
      if(!response.ok) throw new Error(data.detail || 'Suggestion failed');
      showDraft(data.suggestion);
    }catch(e){
      status('Assistant unavailable — check that the local backend is running.');
      alert(`Could not generate steps.\n\n${e.message}`);
    }
  }

  $('addStepBtn').onclick=()=>{add();status('New step added — name it and review it.');};
  $('saveExperimentBtn').onclick=save;
  $('suggestStepsBtn').onclick=suggest;

  // Default demo protocol. AI suggestions can replace these steps at any time.
  add({name:'Pick up container'});
  add({name:'Open container'});
  add({name:'Insert tool'});
  add({name:'Transfer sample'});
  add({name:'Close container'});
  add({name:'Place container back'});
})();
