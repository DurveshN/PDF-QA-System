interface TogglePanelProps {
  icon: string
  label: string
  enabled: boolean
  onChange: (enabled: boolean) => void
  accentColor?: string
}

const colorMap: Record<string, string> = {
  purple: 'bg-purple-500',
  blue: 'bg-blue-500',
  green: 'bg-green-500',
  gray: 'bg-gray-500',
}

export default function TogglePanel({
  icon,
  label,
  enabled,
  onChange,
  accentColor = 'purple',
}: TogglePanelProps) {
  const activeColor = colorMap[accentColor] ?? colorMap.purple

  return (
    <button
      onClick={() => onChange(!enabled)}
      className={`
        flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
        transition-all duration-200 select-none
        ${
          enabled
            ? `${activeColor} text-white shadow-sm`
            : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
        }
      `}
      aria-pressed={enabled}
      aria-label={`${label}: ${enabled ? 'on' : 'off'}`}
    >
      <span>{icon}</span>
      <span className="hidden sm:inline">{label}</span>
    </button>
  )
}
