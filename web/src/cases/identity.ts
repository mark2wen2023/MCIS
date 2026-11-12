import { getOperator, getRole } from '../api'
export const caseIdentity = () => `${getRole()}\n${getOperator()}`
