import { useEffect, useRef, useState } from 'react'
import { websocketUrl } from '../services/api'

export function useWebSocket(enabled = true) {
  const [status, setStatus] = useState('connecting')
  const [lastEvent, setLastEvent] = useState(null)
  const socketRef = useRef(null)

  useEffect(() => {
    if (!enabled) {
      setStatus('disconnected')
      return undefined
    }
    let active = true
    let retryTimer
    let retryDelay = 1000

    function connect() {
      if (!active) return
      setStatus('connecting')
      const socket = new WebSocket(websocketUrl())
      socketRef.current = socket
      socket.onopen = () => {
        retryDelay = 1000
        setStatus('connected')
      }
      socket.onmessage = (message) => {
        try {
          setLastEvent(JSON.parse(message.data))
        } catch {
          setLastEvent(null)
        }
      }
      socket.onerror = () => socket.close()
      socket.onclose = () => {
        if (!active) return
        setStatus('disconnected')
        retryTimer = window.setTimeout(connect, retryDelay)
        retryDelay = Math.min(retryDelay * 2, 10000)
      }
    }

    connect()
    return () => {
      active = false
      window.clearTimeout(retryTimer)
      socketRef.current?.close()
    }
  }, [enabled])

  return { status, lastEvent }
}