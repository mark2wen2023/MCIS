/** Case metadata availability, deliberately not a service health indicator. */
export function CaseLoadStatus({ onLobby, loaded }: { onLobby: boolean; loaded: boolean | null }) {
  const label = onLobby ? '请选择案件' : loaded === null ? '案件资料载入中' : loaded ? '案件资料已载入' : '案件资料不可用'
  return <span role="status" className={!onLobby && loaded === true ? 'dot-ok' : undefined}
    title="仅表示当前案件资料读取状态，不代表服务健康检查。">{label}</span>
}
