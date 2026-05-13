import { Insights } from '@/lib/types'
import Dashboard from '@/components/Dashboard'
import { promises as fs } from 'fs'
import path from 'path'

async function getInsights(): Promise<Insights> {
  const filePath = path.join(process.cwd(), 'public', 'insights.json')
  const raw = await fs.readFile(filePath, 'utf-8')
  return JSON.parse(raw)
}

export default async function Home() {
  const insights = await getInsights()
  return <Dashboard insights={insights} />
}
