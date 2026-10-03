"use client";

import { useEffect, useState } from "react";
import { Building2, Clock3, Phone, Smartphone, Wallet, X } from "lucide-react";
import { FlashingBadge } from "@/components/ui/FlashingBadge";

const POPUP_DISMISSED_EVENT = "lalahari:home-offer-dismissed";

export function HomeOfferPopup() {
	const [isOpen, setIsOpen] = useState(false);

	useEffect(() => {
		const timer = window.setTimeout(() => setIsOpen(true), 2000);
		return () => window.clearTimeout(timer);
	}, []);

	const closePopup = () => {
		setIsOpen(false);
		window.dispatchEvent(new Event(POPUP_DISMISSED_EVENT));
	};

	useEffect(() => {
		if (!isOpen) return;

		const previousOverflow = document.body.style.overflow;
		document.body.style.overflow = "hidden";
		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.key === "Escape") closePopup();
		};
		window.addEventListener("keydown", handleKeyDown);

		return () => {
			document.body.style.overflow = previousOverflow;
			window.removeEventListener("keydown", handleKeyDown);
		};
	}, [isOpen]);

	if (!isOpen) return null;

	return (
		<div
			className="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto bg-ink/65 p-3 backdrop-blur-sm sm:items-center sm:p-6"
			onClick={(event) => {
				if (event.target === event.currentTarget) closePopup();
			}}
		>
			<section
				role="dialog"
				aria-modal="true"
				aria-labelledby="home-offer-title"
				className="my-auto w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-2xl sm:rounded-3xl"
			>
				<div className="flex items-center justify-between border-b border-black/5 px-5 py-4 sm:px-8">
					<FlashingBadge>First app consultation free</FlashingBadge>
					<button
						type="button"
						onClick={closePopup}
						aria-label="Close offer"
						className="flex h-11 w-11 items-center justify-center rounded-full text-ink/60 hover:bg-primary-light hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
					>
						<X className="h-6 w-6" />
					</button>
				</div>

				<div className="px-5 py-6 sm:px-8 sm:py-8">
					<h2
						id="home-offer-title"
						className="font-heading text-3xl font-extrabold leading-tight text-ink sm:text-4xl"
					>
						Don&apos;t sell your property or take heavy loans for treatment.
						Before bills, tests and procedures add up, ask us first.
					</h2>
					<p className="mt-3 text-lg font-semibold text-primary-darker sm:text-xl">
						Bills, tests and planned procedures can add up. Ask questions before spending your
						savings or taking a loan.
					</p>

					<ul className="mt-5 space-y-3">
						<li className="flex items-start gap-3 rounded-xl bg-primary-soft p-4">
							<Building2 className="mt-0.5 h-5 w-5 shrink-0 text-primary-darker" />
							<span className="text-sm leading-relaxed text-ink/75 sm:text-base">
								Start with a free app-based symptom consultation, or get an affordable specialist
								consultation from home for ₹200.
							</span>
						</li>
						<li className="flex items-start gap-3 rounded-xl bg-primary-soft p-4">
							<Clock3 className="mt-0.5 h-5 w-5 shrink-0 text-primary-darker" />
							<span className="text-sm leading-relaxed text-ink/75 sm:text-base">
								Save travel and waiting time. Before a planned test or procedure, ask why it is
								recommended, what it may cost, and what risks or side effects to discuss.
							</span>
						</li>
						<li className="flex items-start gap-3 rounded-xl bg-primary-soft p-4">
							<Wallet className="mt-0.5 h-5 w-5 shrink-0 text-primary-darker" />
							<span className="text-sm leading-relaxed text-ink/75 sm:text-base">
								Get symptom-based guidance free on your first app consultation. The app is not a
								doctor diagnosis; seek medical care for urgent symptoms.
							</span>
						</li>
					</ul>

					<div className="mt-6 space-y-4">
						<a
							href="#medical-cost-awareness"
							onClick={closePopup}
							className="inline-flex min-h-14 w-full items-center justify-center rounded-full bg-primary px-6 py-4 text-center text-base font-bold text-white shadow-lg shadow-primary/25 transition-colors hover:bg-primary-dark sm:text-lg"
						>
							Watch the patient story and read sources
						</a>

						<div>
							<h3 className="mb-2 text-sm font-semibold text-ink">
								Prefer a phone consultation? Watch how it works.
							</h3>
							<video
								className="aspect-video w-full rounded-xl bg-ink object-contain"
								src="/videos/generated_call_video.mp4"
								controls
								playsInline
								preload="metadata"
								aria-label="How to get a phone consultation from LalahariHealth"
							/>
						</div>

						<a
							href="tel:+911800000000"
							className="inline-flex min-h-14 w-full items-center justify-center gap-2 rounded-full border-2 border-primary px-6 py-4 text-center text-base font-bold text-primary-darker hover:bg-primary-light sm:text-lg"
						>
							<Phone className="h-5 w-5" />
							Call us directly
						</a>
					</div>

					<div className="mt-5">
						<p className="text-center text-xs font-semibold uppercase tracking-wide text-ink/45">
							App downloads available at launch
						</p>
						<div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
							{["App Store", "Google Play"].map((store) => (
								<div
									key={store}
									aria-disabled="true"
									className="flex cursor-not-allowed items-center justify-between rounded-xl border-2 border-dashed border-black/10 bg-primary-soft px-4 py-3 opacity-70"
								>
									<span className="flex items-center gap-2 text-sm font-semibold text-ink/65">
										<Smartphone className="h-4 w-4" /> {store}
									</span>
									<span className="rounded-full bg-white px-2.5 py-1 text-[10px] font-bold uppercase text-primary-darker">
										Coming soon
									</span>
								</div>
							))}
						</div>
					</div>
				</div>
			</section>
		</div>
	);
}
