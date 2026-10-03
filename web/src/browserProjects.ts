import type { Lang, Style } from './api'

const DB_NAME = 'mococo-public-projects'
const STORE = 'projects'

export interface BrowserProject {
  slug: string
  title: string
  style: Style
  script_langs: Lang[]
  subtitle_langs: Lang[]
  voice_langs: Lang[]
  target_minutes: number
  brief: string
  created: number
  film_name: string
  film_size: number
  film: File
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: 'slug' })
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function inStore<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDb()
  try {
    return await new Promise<T>((resolve, reject) => {
      const tx = db.transaction(STORE, mode)
      const request = run(tx.objectStore(STORE))
      let result: T
      request.onsuccess = () => { result = request.result }
      request.onerror = () => reject(request.error)
      tx.oncomplete = () => resolve(result)
      tx.onerror = () => reject(tx.error)
      tx.onabort = () => reject(tx.error ?? new Error('Browser storage was unavailable'))
    })
  } finally {
    db.close()
  }
}

export async function listBrowserProjects(): Promise<BrowserProject[]> {
  const projects = await inStore<BrowserProject[]>('readonly', (store) => store.getAll())
  return projects.sort((a, b) => b.created - a.created)
}

export function getBrowserProject(slug: string): Promise<BrowserProject | undefined> {
  return inStore<BrowserProject | undefined>('readonly', (store) => store.get(slug))
}

export async function saveBrowserProject(project: BrowserProject): Promise<void> {
  if (await getBrowserProject(project.slug)) throw new Error(`Project ${project.slug} already exists in this browser`)
  await inStore<IDBValidKey>('readwrite', (store) => store.add(project))
}

export async function deleteBrowserProject(slug: string): Promise<void> {
  await inStore<undefined>('readwrite', (store) => store.delete(slug))
}
