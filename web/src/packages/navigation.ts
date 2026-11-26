/** Abort at navigation intent, not only after React commits an unmount.
 * HashRouter pushState does not emit hashchange; capture same-document links too.
 * A late popstate/hashchange must not cancel a session already started at the destination.
 */
export function onPackageNavigation(cancel: () => void, stillHere?: () => boolean): () => void {
  const link = (event: MouseEvent) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
    const target = event.target instanceof Element ? event.target.closest('a[href]') : null
    if (!(target instanceof HTMLAnchorElement) || target.download || (target.target && target.target !== '_self')) return
    const destination = new URL(target.href, window.location.href)
    if (destination.origin === window.location.origin && destination.pathname === window.location.pathname && destination.search === window.location.search && destination.hash !== window.location.hash) cancel()
  }
  const leaveIfGone = () => { if (stillHere?.()) return; cancel() }
  window.addEventListener('click', link, true)
  window.addEventListener('popstate', leaveIfGone)
  window.addEventListener('hashchange', leaveIfGone)
  window.addEventListener('pagehide', cancel)
  return () => {
    window.removeEventListener('click', link, true)
    window.removeEventListener('popstate', leaveIfGone)
    window.removeEventListener('hashchange', leaveIfGone)
    window.removeEventListener('pagehide', cancel)
  }
}
