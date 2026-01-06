import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import Script from 'next/script';
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

// Script to remove browser extension attributes and suppress hydration warnings
// This handles Bitdefender and similar extensions that inject attributes into the DOM
const extensionCleanupScript = `
(function() {
  var EXTENSION_ATTRS = ['bis_skin_checked', 'bis_register', '__processed_756a1ae4-a334-4b3e-9da1-0e272987e353__'];

  // Suppress hydration mismatch warnings caused by browser extensions
  // This filters out extension-related warnings from the console
  if (typeof window !== 'undefined') {
    var originalError = console.error;
    console.error = function() {
      var args = Array.prototype.slice.call(arguments);
      var message = args[0];
      // Filter out hydration mismatch warnings caused by extension attributes
      if (typeof message === 'string' &&
          (message.includes('Hydration') || message.includes('hydrat')) &&
          (message.includes('bis_skin_checked') ||
           message.includes('bis_register') ||
           message.includes('__processed_'))) {
        return; // Suppress this warning
      }
      // Also filter the generic "A tree hydrated" warning if it mentions our attributes
      if (typeof message === 'string' && message.includes('A tree hydrated')) {
        var fullMessage = args.join(' ');
        if (fullMessage.includes('bis_skin_checked') ||
            fullMessage.includes('bis_register')) {
          return; // Suppress
        }
      }
      return originalError.apply(console, args);
    };
  }

  function cleanElement(el) {
    if (!el || !el.removeAttribute) return;
    EXTENSION_ATTRS.forEach(function(attr) {
      if (el.hasAttribute && el.hasAttribute(attr)) {
        el.removeAttribute(attr);
      }
    });
  }

  function cleanAll() {
    EXTENSION_ATTRS.forEach(function(attr) {
      document.querySelectorAll('[' + attr + ']').forEach(cleanElement);
    });
    cleanElement(document.documentElement);
    cleanElement(document.body);
  }

  // Initial cleanup - run immediately
  cleanAll();

  // Set up MutationObserver to catch any future injections
  if (typeof MutationObserver !== 'undefined') {
    var observer = new MutationObserver(function(mutations) {
      var needsClean = false;
      mutations.forEach(function(mutation) {
        if (mutation.type === 'attributes' && EXTENSION_ATTRS.includes(mutation.attributeName)) {
          cleanElement(mutation.target);
          needsClean = true;
        }
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
          needsClean = true;
        }
      });
      if (needsClean) {
        // Batch cleanup with requestAnimationFrame for performance
        requestAnimationFrame(cleanAll);
      }
    });

    // Start observing the document element immediately
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: EXTENSION_ATTRS,
      childList: true,
      subtree: true
    });
  }

  // Run cleanup at key moments during page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', cleanAll);
  }
  window.addEventListener('load', cleanAll);

  // Multiple cleanup passes to catch race conditions
  setTimeout(cleanAll, 0);
  setTimeout(cleanAll, 16);  // One frame
  setTimeout(cleanAll, 100);
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <Script
          id="extension-cleanup"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{ __html: extensionCleanupScript }}
        />
      </head>
      <body className={`${inter.variable} font-sans`} suppressHydrationWarning>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
