import Link from "next/link";

export default function OfflinePage() {
  return (
    <main className="flex items-center justify-center min-h-screen px-4">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-[var(--foreground)] mb-4">Offline</h1>
        <p className="text-[var(--color-zh-text)] mb-6 max-w-md">
          You&apos;re currently offline. Content you&apos;ve previously viewed is available, but
          new content requires an internet connection.
        </p>
        <Link
          href="/"
          className="text-[var(--color-accent)] hover:text-[var(--color-accent-light)] transition-colors no-underline font-medium"
        >
          Try again &rarr;
        </Link>
      </div>
    </main>
  );
}
