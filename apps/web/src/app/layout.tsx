import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'Jyntrix AI - Intelligent Chat with Memory',
    template: '%s | Jyntrix AI',
  },
  description:
    'Experience AI conversations that remember context across sessions. Jyntrix AI uses advanced memory architecture to provide more personalized and relevant responses.',
  keywords: [
    'AI',
    'chat',
    'memory',
    'artificial intelligence',
    'conversational AI',
    'machine learning',
  ],
  authors: [{ name: 'Jyntrix' }],
  creator: 'Jyntrix',
  publisher: 'Jyntrix',
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: process.env.NEXT_PUBLIC_APP_URL,
    siteName: 'Jyntrix AI',
    title: 'Jyntrix AI - Intelligent Chat with Memory',
    description:
      'Experience AI conversations that remember context across sessions.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Jyntrix AI - Intelligent Chat with Memory',
    description:
      'Experience AI conversations that remember context across sessions.',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0f172a' },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
