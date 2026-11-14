import {PACKET_SHA} from './model'
export function executionIntent(id:string){
 if(!/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(id))throw Error('intent_id_invalid')
 return {schema:'mcis.public-expert-execution-intent.v1',intentId:id,operation:'prepare_public_two_round_review',packetSha256:PACKET_SHA}
}
