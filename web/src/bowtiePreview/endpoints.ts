import type { Model } from './model'

// Index 0 identifies the top event. A null value means the ID is ambiguous.
export function bowtieEndpointIndex(model: Model): Map<string, number | null> {
  const index = new Map<string, number | null>()
  for (const [position, node] of [model.topEvent, ...model.nodes].entries()) {
    if (!node.id.trim()) continue
    index.set(node.id, index.has(node.id) ? null : position)
  }
  return index
}

export function bowtieDraftFocusTarget(model: Model, id: string): string | null {
  const position = bowtieEndpointIndex(model).get(id)
  if (position === null) return null
  return position === undefined ? 'w153-edges' : position === 0 ? 'w153-top' : 'w153-node-' + (position - 1)
}
