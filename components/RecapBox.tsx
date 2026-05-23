interface RecapBoxProps {
  recapEn: string;
  recapZh: string;
}

export default function RecapBox({ recapEn, recapZh }: RecapBoxProps) {
  if (!recapEn && !recapZh) return null;

  return (
    <div className="recap-box">
      <h3>Key Takeaways / 核心要点</h3>
      {recapEn && <p className="mb-3">{recapEn}</p>}
      {recapZh && (
        <p className="font-[var(--font-zh)] text-[var(--color-zh-text)]" style={{ fontFamily: 'var(--font-zh)' }}>
          {recapZh}
        </p>
      )}
    </div>
  );
}
