'use client'
import type { FC } from 'react'
import React from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import { RiArrowRightUpLine, RiCloseLine, RiCloudFill, RiTerminalBoxFill } from '@remixicon/react'
import Link from 'next/link'
import { useKeyPress } from 'ahooks'
import { Plan, SelfHostedPlan } from '../type'
import TabSlider from '../../base/tab-slider'
import SelectPlanRange, { PlanRange } from './select-plan-range'
import PlanItem from './plan-item'
import SelfHostedPlanItem from './self-hosted-plan-item'
import CustomPlan from './custom-plan'
import { useProviderContext } from '@/context/provider-context'
import GridMask from '@/app/components/base/grid-mask'
import { useAppContext } from '@/context/app-context'
import classNames from '@/utils/classnames'
import { useGetPricingPageLanguage } from '@/context/i18n'

type Props = {
  onCancel: () => void
}

const Pricing: FC<Props> = ({
  onCancel,
}) => {
  const { t } = useTranslation()
  const { plan } = useProviderContext()
  const { isCurrentWorkspaceManager, userProfile, customPlans } = useAppContext()
  const canPay = isCurrentWorkspaceManager
  const [planRange, setPlanRange] = React.useState<PlanRange>(PlanRange.monthly)

  const [currentPlan, setCurrentPlan] = React.useState<string>('cloud')

  // console.log('userProfile', userProfile)
  // console.log('customPlans', customPlans)

  useKeyPress(['esc'], onCancel)

  const pricingPageLanguage = useGetPricingPageLanguage()
  const pricingPageURL = pricingPageLanguage
    ? `https://dify.ai/${pricingPageLanguage}/pricing#plans-and-features`
    : 'https://dify.ai/pricing#plans-and-features'

  return createPortal(
    <div
      className='fixed inset-0 bottom-0 left-0 right-0 top-0 z-[1000] bg-background-overlay-backdrop p-4 backdrop-blur-[6px]'
      onClick={e => e.stopPropagation()}
    >
      <div className='relative h-full w-full overflow-auto rounded-2xl border border-effects-highlight bg-saas-background'>
        <div
          className='fixed right-7 top-7 z-[1001] flex h-9 w-9 cursor-pointer items-center justify-center rounded-[10px] bg-components-button-tertiary-bg hover:bg-components-button-tertiary-bg-hover'
          onClick={onCancel}
        >
          <RiCloseLine className='size-5 text-components-button-tertiary-text' />
        </div>
        <GridMask wrapperClassName='w-full min-h-full' canvasClassName='min-h-full'>
          <div className='flex flex-col items-center px-8 pb-7 pt-12'>
            <div className='title-5xl-bold mb-2 text-text-primary'>
              {t('billing.plansCommon.title')}
            </div>
            <div className='system-sm-regular text-text-secondary'>
              <span>Import note: Hãy đảm chuyển khoản đúng nội dung và đúng số tiền để tránh kích hoạt gói không thành công.</span>
            </div>
          </div>
          <div className='mx-auto w-[1152px]'>
            <div className='pb-8 pt-3'>
              <div className='flex flex-wrap justify-center gap-4'>
                {customPlans.map(plan => (
                  <CustomPlan key={plan.id} plan={plan} />
                ))}
              </div>
            </div>
          </div>
        </GridMask>
      </div >
    </div >,
    document.body,
  )
}
export default React.memo(Pricing)
