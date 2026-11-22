/** Before removing the edge subtree, move only its still-owned focus.
 * No timers, storage, autofocus-on-load or navigation interception.
 */
export function restoreEdgeFocus(root:HTMLElement|null,target:HTMLElement|null){
 if(!root?.isConnected||!target?.isConnected||root.ownerDocument!==target.ownerDocument)return
 const active=root.ownerDocument.activeElement
 if(!active||!root.contains(active))return
 const region=active.closest('[data-ecfc-edge-focus]')
 if(!region||!root.contains(region))return
 // Focus is best-effort; failure must never prevent content invalidation.
 try{target.focus({preventScroll:true})}catch{/* no retry or delayed focus */}
}
