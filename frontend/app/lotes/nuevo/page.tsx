"use client";

import { useRouter } from "next/navigation";
import { NewLotForm } from "@/components/LotForm";
import { PageHeader, useToast } from "@/components/ui";
import { emitTourDone } from "@/lib/tour";

export default function NewLotPage() {
  const router = useRouter();
  const toast = useToast();
  return (
    <>
      <PageHeader title="Registrar lote" description="El lote queda en estado «Registrado». Al agregarle una foto pasa a «Pendiente de inspección»." />
      <NewLotForm
        onCreated={(lot) => {
          toast(`Lote ${lot.code} registrado.`);
          emitTourDone("lot-created", { code: lot.code });
          router.push(`/inspeccion?lote=${lot.code}`);
        }}
      />
    </>
  );
}
