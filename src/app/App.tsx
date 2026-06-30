import { useState } from 'react'
import { NeuralWakeup } from '../components/boot/NeuralWakeup'
import { UserProfilePage } from '../components/user/UserProfilePage'
import { SystemModalsShell } from '../components/system/SystemModalsShell'
import { UserSessionProvider } from '../contexts/UserSessionContext'
import { MacPermissionsProvider } from '../contexts/MacPermissionsContext'
import { useAuth } from '../hooks/useAuth'

export default function App() {
  const auth = useAuth()
  const [profileOpen, setProfileOpen] = useState(false)

  return (
    <UserSessionProvider session={auth.session}>
      <MacPermissionsProvider>
      <NeuralWakeup
        userName={auth.username ?? '访客'}
        authenticated={auth.isAuthenticated}
        loginError={auth.loginError}
        loggingIn={auth.loggingIn}
        onLogin={auth.login}
        onLogout={auth.logout}
        onOpenProfile={() => setProfileOpen(true)}
      />
      <UserProfilePage
        open={profileOpen}
        onClose={() => setProfileOpen(false)}
        onLogout={auth.logout}
      />
      <SystemModalsShell />
      </MacPermissionsProvider>
    </UserSessionProvider>
  )
}
