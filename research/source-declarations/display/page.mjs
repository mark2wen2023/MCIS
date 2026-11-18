import {scenario,scenarioNames} from './scenarios.mjs';
import {renderDeclarationView} from './view.mjs';
// Each choice replaces the complete rendered result; no asynchronous requests or cache.
export function selectScenario(name){return renderDeclarationView(scenario(name));}
export function mountPrototype(root){
 const select=root.ownerDocument.createElement('select');
 select.setAttribute('aria-label','选择手造合成场景');
 for(const name of scenarioNames){const option=root.ownerDocument.createElement('option');option.value=name;option.textContent=name;select.append(option)}
 const output=root.ownerDocument.createElement('div');
 const update=()=>{output.innerHTML=selectScenario(select.value)};
 select.addEventListener('change',update);root.replaceChildren(select,output);update();
}
