/** Invalidate read state at navigation intent, not only after React commits an unmount.
 * HashRouter pushState does not emit hashchange; capture same-document links too.
 */
export function onTrackNavigation(cancel: () => void): () => void {
  const subscribedUrl = window.location.href
  // A new route can mount before its arrival hashchange is dispatched.
  // That event must not cancel the new route's own read.
  const movedAway = () => { if (window.location.href !== subscribedUrl) cancel() }
  const link = (event: MouseEvent) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
    const target = event.target instanceof Element ? event.target.closest('a[href]') : null
    if (!(target instanceof HTMLAnchorElement) || target.download || (target.target && target.target !== '_self')) return
    const destination = new URL(target.href, window.location.href)
    if (destination.origin === window.location.origin && destination.pathname === window.location.pathname && destination.search === window.location.search && destination.hash !== window.location.hash) cancel()
  }
  window.addEventListener('click', link, true)
  window.addEventListener('popstate', movedAway)
  window.addEventListener('hashchange', movedAway)
  window.addEventListener('pagehide', cancel)
  return () => {
    window.removeEventListener('click', link, true)
    window.removeEventListener('popstate', movedAway)
    window.removeEventListener('hashchange', movedAway)
    window.removeEventListener('pagehide', cancel)
  }
}
