interface Player {
  player_id: string
  player_name: string
  is_host: boolean
}

interface PlayerListItemProps {
  player: Player
  currentPlayerId: string
}

// Deterministic color assignment from player_name hash (6 preset colors from UI-SPEC)
const AVATAR_COLORS = [
  '#6366f1',
  '#22c55e',
  '#f59e0b',
  '#ec4899',
  '#14b8a6',
  '#f97316',
]

function getAvatarColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0
  }
  return AVATAR_COLORS[hash % AVATAR_COLORS.length]
}

export default function PlayerListItem({ player, currentPlayerId }: PlayerListItemProps) {
  const avatarColor = getAvatarColor(player.player_name)
  const initial = player.player_name.charAt(0).toUpperCase()
  const isCurrentPlayer = player.player_id === currentPlayerId

  return (
    <div
      className="flex items-center gap-3 px-4 py-3 rounded-lg transition-opacity duration-200"
      style={{ backgroundColor: '#1a1d27', minHeight: '44px' }}
    >
      {/* Avatar circle */}
      <div
        className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold text-white select-none"
        style={{ backgroundColor: avatarColor }}
        aria-hidden="true"
      >
        {initial}
      </div>

      {/* Player name */}
      <span className="flex-1 text-base font-normal" style={{ color: '#f1f5f9' }}>
        {player.player_name}
        {isCurrentPlayer && (
          <span className="ml-2 text-xs" style={{ color: '#6b7280' }}>
            (você)
          </span>
        )}
      </span>

      {/* Host badge */}
      {player.is_host && (
        <span
          className="flex-shrink-0 px-2 py-0.5 rounded text-xs font-semibold text-white"
          style={{ backgroundColor: '#6366f1' }}
        >
          Host
        </span>
      )}
    </div>
  )
}
