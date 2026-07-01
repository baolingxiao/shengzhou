import { useState } from 'react'
import { NeuralWakeup } from '../components/boot/NeuralWakeup'
import { UserProfilePage } from '../components/user/UserProfilePage'
import { SystemModalsShell } from '../components/system/SystemModalsShell'
import { UserSessionProvider } from '../contexts/UserSessionContext'
import { MacPermissionsProvider } from '../contexts/MacPermissionsContext'
import { PageLanguageProvider } from '../contexts/PageLanguageContext'
import { useAuth } from '../hooks/useAuth'
import { useUserPersona } from '../hooks/useUserPersona'

export default function App() {
  const auth = useAuth()
  const userPersona = useUserPersona(auth.session)
  const [profileOpen, setProfileOpen] = useState(false)

  return (
    <UserSessionProvider session={auth.session}>
      <PageLanguageProvider>
        <MacPermissionsProvider>
          <NeuralWakeup
            userName={auth.username ?? '访客'}
            authenticated={auth.isAuthenticated}
            role={auth.role}
            loginError={auth.loginError}
            loggingIn={auth.loggingIn}
            onLogin={auth.login}
            onRegister={auth.register}
            onLogout={auth.logout}
            onOpenProfile={() => setProfileOpen(true)}
            personaRequired={userPersona.required}
            personaConfigured={userPersona.configured}
            personaLoading={userPersona.loading}
            personaSaving={userPersona.saving}
            personaError={userPersona.error}
            onSavePersona={userPersona.save}
          />
          <UserProfilePage
            open={profileOpen}
            onClose={() => setProfileOpen(false)}
            onLogout={auth.logout}
          />
          <SystemModalsShell />
        </MacPermissionsProvider>
      </PageLanguageProvider>
    </UserSessionProvider>
  )
}
