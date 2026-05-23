"use client";

import { useRouter } from "next/navigation";

export default function BackButton() {
  const router = useRouter();

  return (
    <button
      onClick={() => router.back()}
      className="text-sm text-[var(--color-accent)] hover:text-[var(--color-accent-light)] transition-colors bg-transparent border-none cursor-pointer"
    >
      &larr; Back
    </button>
  );
}
