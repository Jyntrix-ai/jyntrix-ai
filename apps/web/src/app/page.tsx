import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import Link from 'next/link';

export default async function HomePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // If user is authenticated, redirect to chat
  if (user) {
    redirect('/chat');
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-surface-elevated dark:from-background-dark dark:to-surface-dark">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-border dark:border-border-dark">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                <span className="text-white font-bold text-sm">J</span>
              </div>
              <span className="font-semibold text-lg text-text-primary dark:text-text-primary-dark">
                Jyntrix AI
              </span>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/login"
                className="text-sm font-medium text-text-secondary dark:text-text-secondary-dark hover:text-text-primary dark:hover:text-text-primary-dark transition-colors"
              >
                Sign in
              </Link>
              <Link
                href="/signup"
                className="btn-primary px-4 py-2 text-sm"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="pt-16">
        <section className="relative overflow-hidden">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 sm:py-32 lg:py-40">
            <div className="text-center">
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-text-primary dark:text-text-primary-dark">
                AI That
                <span className="gradient-text"> Remembers</span>
              </h1>
              <p className="mt-6 text-lg sm:text-xl text-text-secondary dark:text-text-secondary-dark max-w-2xl mx-auto">
                Experience conversations that build on previous context. Jyntrix AI
                uses advanced memory architecture to provide personalized,
                context-aware responses.
              </p>
              <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/signup"
                  className="btn-primary px-8 py-3 text-base"
                >
                  Start Chatting Free
                </Link>
                <Link
                  href="#features"
                  className="btn-secondary px-8 py-3 text-base"
                >
                  Learn More
                </Link>
              </div>
            </div>
          </div>

          {/* Decorative gradient orbs */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-primary-500/20 to-accent-500/20 rounded-full blur-3xl -z-10" />
        </section>

        {/* Features Section */}
        <section id="features" className="py-24 bg-surface dark:bg-surface-dark">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl sm:text-4xl font-bold text-text-primary dark:text-text-primary-dark">
                Why Choose Jyntrix AI?
              </h2>
              <p className="mt-4 text-text-secondary dark:text-text-secondary-dark max-w-2xl mx-auto">
                Built with cutting-edge memory technology for smarter conversations.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* Feature 1 */}
              <div className="p-6 rounded-2xl bg-background dark:bg-background-dark border border-border dark:border-border-dark card-hover">
                <div className="w-12 h-12 rounded-xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center mb-4">
                  <svg
                    className="w-6 h-6 text-primary-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-text-primary dark:text-text-primary-dark mb-2">
                  Persistent Memory
                </h3>
                <p className="text-text-secondary dark:text-text-secondary-dark">
                  Your AI assistant remembers important details across sessions,
                  creating a more personalized experience over time.
                </p>
              </div>

              {/* Feature 2 */}
              <div className="p-6 rounded-2xl bg-background dark:bg-background-dark border border-border dark:border-border-dark card-hover">
                <div className="w-12 h-12 rounded-xl bg-accent-100 dark:bg-accent-900/30 flex items-center justify-center mb-4">
                  <svg
                    className="w-6 h-6 text-accent-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-text-primary dark:text-text-primary-dark mb-2">
                  Real-Time Streaming
                </h3>
                <p className="text-text-secondary dark:text-text-secondary-dark">
                  See responses as they&apos;re generated with smooth streaming.
                  No waiting for complete responses.
                </p>
              </div>

              {/* Feature 3 */}
              <div className="p-6 rounded-2xl bg-background dark:bg-background-dark border border-border dark:border-border-dark card-hover">
                <div className="w-12 h-12 rounded-xl bg-green-100 dark:bg-green-900/30 flex items-center justify-center mb-4">
                  <svg
                    className="w-6 h-6 text-green-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                    />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-text-primary dark:text-text-primary-dark mb-2">
                  Privacy First
                </h3>
                <p className="text-text-secondary dark:text-text-secondary-dark">
                  Your data stays yours. Manage your memories, export or delete
                  them anytime.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-24">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl sm:text-4xl font-bold text-text-primary dark:text-text-primary-dark mb-6">
              Ready to experience smarter AI?
            </h2>
            <p className="text-lg text-text-secondary dark:text-text-secondary-dark mb-8">
              Join thousands of users who are already having more meaningful AI
              conversations.
            </p>
            <Link href="/signup" className="btn-primary px-8 py-3 text-base">
              Get Started for Free
            </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border dark:border-border-dark py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                <span className="text-white font-bold text-xs">J</span>
              </div>
              <span className="text-sm text-text-secondary dark:text-text-secondary-dark">
                Jyntrix AI
              </span>
            </div>
            <p className="text-sm text-text-muted dark:text-text-muted-dark">
              &copy; {new Date().getFullYear()} Jyntrix. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
