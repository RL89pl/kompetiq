import { downloadUrl } from '../api/client'

/** Dokument do pobrania: PDF (do druku i podpisu) oraz DOCX (wersja edytowalna). */
export function Download({ path, label }: { path: string; label: string }) {
  return (
    <span className="inline-flex flex-wrap items-baseline gap-x-2">
      <a className="font-bold underline" href={downloadUrl(`${path}?fmt=pdf`)}>{label} (PDF)</a>
      <a className="text-sm underline" href={downloadUrl(`${path}?fmt=docx`)}>wersja DOCX</a>
    </span>
  )
}
