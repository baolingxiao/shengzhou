export function useAdminRole(
  _username: string | null,
  sessionIsAdmin: boolean,
  _enabled = true,
) {
  return sessionIsAdmin
}
