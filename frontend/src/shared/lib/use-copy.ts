import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Copy text to the clipboard and remember what was copied, briefly.
 *
 * `navigator.clipboard` needs a secure context and permission, and either can
 * be missing on a shop's counter machine, so a plain textarea + execCommand
 * stands behind it. If both fail the caller learns nothing was copied — the
 * text is still on screen to read out, which is what a seller does anyway.
 */
export function useCopy(resetAfterMs = 1400) {
  const [copied, setCopied] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current)
    },
    [],
  )

  const copy = useCallback(
    async (text: string) => {
      const ok = (await writeViaClipboard(text)) || writeViaTextarea(text)
      if (!ok) return false
      setCopied(text)
      if (timer.current) clearTimeout(timer.current)
      timer.current = setTimeout(() => setCopied(null), resetAfterMs)
      return true
    },
    [resetAfterMs],
  )

  return { copied, copy }
}

async function writeViaClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

function writeViaTextarea(text: string): boolean {
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch {
    return false
  }
}
