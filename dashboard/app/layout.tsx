import type { Metadata } from 'next'
import { Host_Grotesk } from 'next/font/google'
import './globals.css'

const hostGrotesk = Host_Grotesk({
  subsets: ['latin'],
  variable: '--font-host-grotesk',
})

export const metadata: Metadata = {
  title: 'Session Analysis — Tandem Explorer',
  description: 'User session behavior analysis dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={hostGrotesk.variable}>
      <body>{children}</body>
    </html>
  )
}
