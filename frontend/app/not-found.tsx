import Link from "next/link";

export default function NotFound() {
  return (
    <div className="max-w-lg py-16">
      <h1 className="text-2xl font-semibold">No encontramos esta página</h1>
      <p className="mt-2 text-sm text-muted">Revise la dirección o vuelva al panel. Si llegó desde un QR, el lote puede haberse borrado al restablecer la demostración.</p>
      <Link href="/" className="btn-primary mt-6">Ir al panel</Link>
    </div>
  );
}
