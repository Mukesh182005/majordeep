import { useEffect, useState } from 'react'

/**
 * Loads an evidence image with the session cookie (credentials: 'include') and shows
 * it through an object URL, so an unavailable image gets a clear message instead of a
 * broken-image icon.
 */
export default function AuthedImage({ src, alt, className }) {
  const [objectUrl, setObjectUrl] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let revoked = false
    let created = null

    async function load() {
      try {
        const response = await fetch(src, {
          credentials: 'include',
        })
        if (!response.ok) throw new Error(`Evidence image unavailable (${response.status})`)
        created = URL.createObjectURL(await response.blob())
        if (!revoked) setObjectUrl(created)
      } catch {
        if (!revoked) setFailed(true)
      }
    }
    load()

    return () => {
      revoked = true
      if (created) URL.revokeObjectURL(created)
    }
  }, [src])

  if (failed) {
    return (
      <p className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
        This evidence image could not be loaded. The numeric score above is unaffected.
      </p>
    )
  }
  if (!objectUrl) {
    return <div className={`animate-pulse rounded-lg bg-slate-100 ${className}`} style={{ minHeight: '8rem' }} />
  }
  return <img src={objectUrl} alt={alt} className={className} />
}
