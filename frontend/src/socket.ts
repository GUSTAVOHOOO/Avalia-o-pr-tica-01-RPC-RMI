import { io } from 'socket.io-client'

// Singleton Socket.IO client instance (D-07, Pattern 8)
// autoConnect: false — pages call socket.connect() when mounting
// In dev: Vite proxies /socket.io → Flask :5000 (Pitfall 1: ws: true in vite.config.ts)
// In prod: same origin as React app (Flask serves both)
const socket = io({ path: '/socket.io', autoConnect: false })

export default socket
