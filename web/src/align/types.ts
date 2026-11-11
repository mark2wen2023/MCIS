import type { Conflict } from '../types'
export type PreviewKind = 'Heading' | 'CourseOverGround' | 'SpeedOverGround'
export interface PreviewSource { sourceId: string; text: string; csvMapping: { timeColumn: string; columns: {column: string; kind: PreviewKind}[] } }
export interface PreviewRequest { sources: PreviewSource[] }
export interface AlignPreview {
  previewOnly: true; persisted: false; caseId: string; caseEpochUtc: string
  result: { caseId: string; conflicts: Conflict[]; clockOffsets: { sourceId: string; offsetSeconds?: number | null; uncertaintySeconds?: number | null; status: string }[];
    calibration: { allCalibrated: boolean; uncalibratedSources: string[]; error?: string; sources: unknown[] };
    importDiagnostics: unknown[]; conflictDiagnostics: unknown[]; stats: Record<string, number> }
}
