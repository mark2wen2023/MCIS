import type {SuggestionInput} from './suggestionModel'

// React instance identity, not an authorization token or cryptographic digest.
// Field order must not reset a preview, but any source value change must.
export function previewSessionKey(input:SuggestionInput,who:string):string {
 return JSON.stringify([who,input.kind,Object.entries(input.source).sort(([a],[b])=>a.localeCompare(b))])
}
