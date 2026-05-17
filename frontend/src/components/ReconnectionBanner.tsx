import { useEffect, useRef, useState } from 'react'
import socket from '../socket'
import './ReconnectionBanner.css'

interface ReconnectionBannerProps {
  onStateChange?: (visible: boolean) => void
}

export default function ReconnectionBanner({ onStateChange }: ReconnectionBannerProps) {
  const [bannerState, setBannerState] = useState<'hidden' | 'amber' | 'red'>('hidden')
  const bannerTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    function handleDisconnect() {
      if (bannerTimerRef.current) clearTimeout(bannerTimerRef.current)
      setBannerState('amber')
      bannerTimerRef.current = setTimeout(() => setBannerState('red'), 3000)
    }

    function handleConnect() {
      if (bannerTimerRef.current) clearTimeout(bannerTimerRef.current)
      setBannerState('hidden')
    }

    socket.on('disconnect', handleDisconnect)
    socket.on('connect', handleConnect)

    return () => {
      socket.off('disconnect', handleDisconnect)
      socket.off('connect', handleConnect)
      if (bannerTimerRef.current) clearTimeout(bannerTimerRef.current)
    }
  }, [])

  // Notify parent when banner visibility changes
  useEffect(() => {
    if (onStateChange) {
      onStateChange(bannerState !== 'hidden')
    }
  }, [bannerState, onStateChange])

  if (bannerState === 'hidden') return null

  return (
    <div
      className={`reconnection-banner reconnection-banner--${bannerState}`}
      role="alert"
      aria-live="assertive"
    >
      {bannerState === 'amber' ? 'Reconectando...' : 'Offline — verifique sua conexão'}
    </div>
  )
}
