import {parseSuggestion,type Suggestion,type SuggestionInput} from './suggestionModel'
import type {Content} from './model'

// A local form gate, not an authenticity/rights or server authorization decision.
export function reviewedSuggestion(result:Suggestion,input:SuggestionInput,acknowledgedDigest:string|null):Content|null {
 if(acknowledgedDigest!==result.inputDigest)return null
 try{return structuredClone(parseSuggestion(result,input).content)}catch{return null}
}
