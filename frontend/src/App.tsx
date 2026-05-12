import { BrowserRouter, Routes, Route } from 'react-router'
import Landing from './pages/Landing'
import CreateGame from './pages/CreateGame'
import JoinGame from './pages/JoinGame'
import JoinByCode from './pages/JoinByCode'
import Lobby from './pages/Lobby'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/create" element={<CreateGame />} />
        <Route path="/join" element={<JoinGame />} />
        <Route path="/join/:code" element={<JoinByCode />} />
        <Route path="/lobby/:sessionId" element={<Lobby />} />
      </Routes>
    </BrowserRouter>
  )
}
