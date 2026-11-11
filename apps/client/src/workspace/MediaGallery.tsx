import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, apiBlob } from '../api/client'
import { pendingMedia } from './mediaQueue'

type MediaItem = { id: string; mime: string; size_bytes: number }
type OwnerType = 'observation' | 'task'

export function MediaGallery({ ownerType, ownerId }: { ownerType: OwnerType; ownerId: string }) {
  const media = useQuery({
    queryKey: ['media', ownerType, ownerId],
    queryFn: () => api<MediaItem[]>(`/media/${ownerType}/${ownerId}`),
  })
  const [sources, setSources] = useState<string[]>([])
  const [queued, setQueued] = useState(0)
  useEffect(() => {
    let alive = true
    const objectUrls: string[] = []
    void pendingMedia(ownerType, ownerId).then(async (items) => {
      if (alive) setQueued(items.length)
      for (const item of items) {
        objectUrls.push(URL.createObjectURL(item.blob))
      }
    }).catch(() => undefined)
    if (media.data) {
      void Promise.all(media.data.map((item) => apiBlob(`/media-file/${item.id}`)))
        .then((blobs) => {
          const urls = blobs.map((blob) => URL.createObjectURL(blob))
          objectUrls.push(...urls)
          if (alive) setSources(urls)
        }).catch(() => undefined)
    }
    return () => {
      alive = false
      objectUrls.forEach((url) => URL.revokeObjectURL(url))
    }
  }, [ownerType, ownerId, media.data])
  return <div>
    <h2>Фотографии</h2>
    {sources.length === 0 && queued === 0 && <p className="muted">Фотографии не прикреплены.</p>}
    {queued > 0 && <p className="pending-tag">{queued} фото ожидают отправки</p>}
    <div className="photo-gallery">{sources.map((src, index) => <img key={src} src={src} alt={`Фото ${index + 1}`} />)}</div>
  </div>
}
