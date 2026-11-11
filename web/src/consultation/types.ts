import type { ConsultationRound } from '../types'
export type Decision = 'Pending' | 'Adopted' | 'PartiallyAdopted' | 'NotAdopted'
export interface ConsultationComment {
  commentId: string; round: number; partyId: string; text: string; decision: Decision;
  feedback?: string; decidedBy?: string | null; decidedUtc?: string | null
}
export interface Round extends ConsultationRound {
  caseId: string
  replies: { partyId: string; utc: string; text: string; commentIds?: string[] }[]
  waivers?: { partyId: string; reason: string; utc: string }[]
  comments: ConsultationComment[]
}
export interface Policy { matrix: Record<string, Record<string, string>> }
