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
  'var(--color-accent-strong)',
  'var(--color-success)',
  'var(--color-warning)',
  'var(--color-avatar-pink)',
  'var(--color-avatar-teal)',
  'var(--color-avatar-orange)',
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
    <div className="player-list-item">
      {/* Avatar circle */}
      <div
        className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold text-white select-none"
        style={{ backgroundColor: avatarColor }}
        aria-hidden="true"
      >
        {initial}
      </div>

      {/* Player name */}
      <span className="player-list-item__name">
        {player.player_name}
        {isCurrentPlayer && (
          <span className="player-list-item__current">
            (você)
          </span>
        )}
      </span>

      {/* Host badge */}
      {player.is_host && (
        <span className="player-list-item__host">
          Host
        </span>
      )}
    </div>
  )
}
