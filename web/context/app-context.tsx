'use client'

import { createRef, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import useSWR from 'swr'
import { createContext, useContext, useContextSelector } from 'use-context-selector'
import type { FC, ReactNode } from 'react'
import { fetchAppList } from '@/service/apps'
import Loading from '@/app/components/base/loading'
import { fetchCurrentWorkspace, fetchCustomPaymentSetting, fetchCustomPlans, fetchLanggeniusVersion, fetchUserProfile, getSystemFeatures } from '@/service/common'
import type { App } from '@/types/app'
import type { CustomPaymentSettingResponse, CustomPlanResponse, ICurrentWorkspace, LangGeniusVersionResponse, UserProfileResponse } from '@/models/common'
import MaintenanceNotice from '@/app/components/header/maintenance-notice'
import { noop } from 'lodash-es'

export type AppContextValue = {
  apps: App[]
  mutateApps: VoidFunction
  userProfile: UserProfileResponse
  paymentSetting: CustomPaymentSettingResponse
  customPlans: Array<CustomPlanResponse>
  mutateUserProfile: VoidFunction
  currentWorkspace: ICurrentWorkspace
  isCurrentWorkspaceManager: boolean
  isCurrentWorkspaceOwner: boolean
  isCurrentWorkspaceEditor: boolean
  isCurrentWorkspaceDatasetOperator: boolean
  mutateCurrentWorkspace: VoidFunction
  pageContainerRef: React.RefObject<HTMLDivElement>
  langeniusVersionInfo: LangGeniusVersionResponse
  useSelector: typeof useSelector
  isLoadingCurrentWorkspace: boolean
}

const initialLangeniusVersionInfo = {
  current_env: '',
  current_version: '',
  latest_version: '',
  release_date: '',
  release_notes: '',
  version: '',
  can_auto_update: false,
}

const initialWorkspaceInfo: ICurrentWorkspace = {
  id: '',
  name: '',
  plan: '',
  status: '',
  created_at: 0,
  role: 'normal',
  providers: [],
}

const AppContext = createContext<AppContextValue>({
  apps: [],
  mutateApps: noop,
  userProfile: {
    id: '',
    name: '',
    email: '',
    avatar: '',
    avatar_url: '',
    is_password_set: false,
  },
  paymentSetting: {
    account_name: '',
    account_id: '',
    bank_id: '',
  },
  customPlans: [],
  currentWorkspace: initialWorkspaceInfo,
  isCurrentWorkspaceManager: false,
  isCurrentWorkspaceOwner: false,
  isCurrentWorkspaceEditor: false,
  isCurrentWorkspaceDatasetOperator: false,
  mutateUserProfile: noop,
  mutateCurrentWorkspace: noop,
  pageContainerRef: createRef(),
  langeniusVersionInfo: initialLangeniusVersionInfo,
  useSelector,
  isLoadingCurrentWorkspace: false,
})

export function useSelector<T>(selector: (value: AppContextValue) => T): T {
  return useContextSelector(AppContext, selector)
}

export type AppContextProviderProps = {
  children: ReactNode
}

export const AppContextProvider: FC<AppContextProviderProps> = ({ children }) => {
  const pageContainerRef = useRef<HTMLDivElement>(null)

  const { data: appList, mutate: mutateApps } = useSWR({ url: '/apps', params: { page: 1, limit: 30, name: '' } }, fetchAppList)
  const { data: userProfileResponse, mutate: mutateUserProfile } = useSWR({ url: '/account/profile', params: {} }, fetchUserProfile)
  const { data: currentWorkspaceResponse, mutate: mutateCurrentWorkspace, isLoading: isLoadingCurrentWorkspace } = useSWR({ url: '/workspaces/current', params: {} }, fetchCurrentWorkspace)

  // Custom
  const { data: customPlansResponse } = useSWR({ url: 'custom/plans', params: {} }, fetchCustomPlans)
  const { data: customPaymentSettingResponse } = useSWR({ url: 'custom/payment_settings', params: {} }, fetchCustomPaymentSetting)
  // End custom

  const { data: systemFeatures } = useSWR({ url: '/console/system-features' }, getSystemFeatures, {
    fallbackData: defaultSystemFeatures,
  })

  // Custom
  const [customPlans, setCustomPlans] = useState<Array<CustomPlanResponse>>([])
  const [paymentSetting, setPaymentSetting] = useState<CustomPaymentSettingResponse>()
  // End custom

  const [userProfile, setUserProfile] = useState<UserProfileResponse>()
  const [langeniusVersionInfo, setLangeniusVersionInfo] = useState<LangGeniusVersionResponse>(initialLangeniusVersionInfo)
  const [currentWorkspace, setCurrentWorkspace] = useState<ICurrentWorkspace>(initialWorkspaceInfo)
  const isCurrentWorkspaceManager = useMemo(() => ['owner', 'admin'].includes(currentWorkspace.role), [currentWorkspace.role])
  const isCurrentWorkspaceOwner = useMemo(() => currentWorkspace.role === 'owner', [currentWorkspace.role])
  const isCurrentWorkspaceEditor = useMemo(() => ['owner', 'admin', 'editor'].includes(currentWorkspace.role), [currentWorkspace.role])
  const isCurrentWorkspaceDatasetOperator = useMemo(() => currentWorkspace.role === 'dataset_operator', [currentWorkspace.role])
  const updateUserProfileAndVersion = useCallback(async () => {
    if (userProfileResponse && !userProfileResponse.bodyUsed) {
      const result = await userProfileResponse.json()
      setUserProfile(result)
      const current_version = userProfileResponse.headers.get('x-version')
      const current_env = process.env.NODE_ENV === 'development' ? 'DEVELOPMENT' : userProfileResponse.headers.get('x-env')
      const versionData = await fetchLanggeniusVersion({ url: '/version', params: { current_version } })
      setLangeniusVersionInfo({ ...versionData, current_version, latest_version: versionData.version, current_env })
    }
  }, [userProfileResponse])

  useEffect(() => {
    updateUserProfileAndVersion()
  }, [updateUserProfileAndVersion, userProfileResponse])

  // Custom
  useEffect(() => {
    if (customPlansResponse && !customPlansResponse.bodyUsed) {
      customPlansResponse.json().then((res: Array<CustomPlanResponse>) => {
        setCustomPlans(res)
      })
    }
  }, [customPlansResponse])

  useEffect(() => {
    if (customPaymentSettingResponse && !customPaymentSettingResponse.bodyUsed) {
      customPaymentSettingResponse.json().then((res: CustomPaymentSettingResponse) => {
        setPaymentSetting(res)
      })
    }
  }, [customPaymentSettingResponse])
  // End custom

  useEffect(() => {
    if (currentWorkspaceResponse)
      setCurrentWorkspace(currentWorkspaceResponse)
  }, [currentWorkspaceResponse])

  if (!appList || !userProfile)
    return <Loading type='app' />

  return (
    <AppContext.Provider value={{
      apps: appList.data,
      mutateApps,
      userProfile,
      paymentSetting,
      customPlans,
      mutateUserProfile,
      pageContainerRef,
      langeniusVersionInfo,
      useSelector,
      currentWorkspace,
      isCurrentWorkspaceManager,
      isCurrentWorkspaceOwner,
      isCurrentWorkspaceEditor,
      isCurrentWorkspaceDatasetOperator,
      mutateCurrentWorkspace,
      isLoadingCurrentWorkspace,
    }}>
      <div className='flex h-full flex-col overflow-y-auto'>
        {globalThis.document?.body?.getAttribute('data-public-maintenance-notice') && <MaintenanceNotice />}
        <div ref={pageContainerRef} className='relative flex grow flex-col overflow-y-auto overflow-x-hidden bg-background-body'>
          {children}
        </div>
      </div>
    </AppContext.Provider>
  )
}

export const useAppContext = () => useContext(AppContext)

export default AppContext
