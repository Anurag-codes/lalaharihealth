import { Building2, Clock3 } from "lucide-react";

export function HomeOfferContent() {
  return (
    <>
      <h2 className="font-heading text-3xl font-extrabold leading-tight text-ink sm:text-3xl">
        Don&apos;t sell your property/take heavy loans for treatment etc.
      </h2>
      <h2 className="font-heading text-3xl font-extrabold leading-tight text-ink sm:text-3xl">
        Get yourself registered to be entitled to:
      </h2>
      <ul className="mt-3 space-y-2 pl-6 text-ink">
        <li className="list-disc font-heading text-xl font-extrabold leading-tight sm:text-2xl">
          <span className="text-primary">Concessional</span> consultations
        </li>
        <li className="list-disc font-heading text-xl font-extrabold leading-tight sm:text-2xl">
          <span className="text-primary">Concessional</span> Treatment
        </li>
        <li className="list-disc font-heading text-xl font-extrabold leading-tight sm:text-2xl">
          <span className="text-primary">Concessional</span> Lab test
        </li>
      </ul>
      <h2 className="mt-3 font-heading text-2xl font-extrabold leading-tight text-ink sm:text-3xl">
        at very cheaper rates at home.
      </h2>
      <ul className="mt-5 space-y-3">
        <li className="flex items-start gap-3 rounded-xl bg-primary-soft p-4">
          <Building2 className="mt-0.5 h-5 w-5 shrink-0 text-primary-darker" />
          <span className="text- leading-relaxed text-ink/75 sm:text-base">
            Save your travelling time to visit doctors, labs and hospitals.
          </span>
        </li>
        <li className="flex items-start gap-3 rounded-xl bg-primary-soft p-4">
          <Clock3 className="mt-0.5 h-5 w-5 shrink-0 text-primary-darker" />
          <span className="text-sm leading-relaxed text-ink/75 sm:text-base">
            Save your money on consultations, treatement and lab test etc while sitting at home.
          </span>
        </li>
      </ul>
    </>
  );
}
