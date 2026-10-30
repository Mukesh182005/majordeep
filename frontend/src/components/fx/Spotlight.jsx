/**
 * Card that jumps up-left on hover and drops a hard offset shadow in `color`.
 * `bg` and `fg` let a card be a solid block of brand colour.
 */
export default function Spotlight({ children, className = '', color = 'var(--acid)', bg, fg }) {
  return (
    <div className={`spotlight card ${className}`}
         style={{ '--spot': color, ...(bg ? { background: bg, borderColor: '#191919' } : {}), ...(fg ? { color: fg } : {}) }}>
      {children}
    </div>
  )
}
