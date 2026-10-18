"use client";

import { useEffect, useState } from "react";
import { Phone, Smartphone } from "lucide-react";
import { HomeOfferContent } from "@/components/sections/HomeOfferContent";
import { useCloseAfterBottomScroll } from "@/hooks/useCloseAfterBottomScroll";

const POPUP_DISMISSED_EVENT = "lalahari:home-offer-dismissed";

export function HomeOfferPopup() {
	const [isOpen, setIsOpen] = useState(false);
	const closePopup = () => {
		setIsOpen(false);
		window.dispatchEvent(new Event(POPUP_DISMISSED_EVENT));
	};
	const scrollDismissHandlers = useCloseAfterBottomScroll(closePopup);

	useEffect(() => {
		const timer = window.setTimeout(() => setIsOpen(true), 2000);
		return () => window.clearTimeout(timer);
	}, []);

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
			{...scrollDismissHandlers}
			onClick={(event) => {
				if (event.target === event.currentTarget) closePopup();
			}}
		>
			<section
				role="dialog"
				aria-modal="true"
				aria-label="Home offer"
				className="my-auto w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-2xl sm:rounded-3xl"
			>
				<div className="flex items-center justify-between border-b border-black/5 px-5 py-4 sm:px-8">
					{/* <FlashingBadge>Get yourself registered on app and be entitled to our concessional consultations, treatment and lab test, etc at very cheaper rates at home.</FlashingBadge> */}
					{/* <button
						type="button"
						onClick={closePopup}
						aria-label="Close offer"
						className="flex h-11 w-11 items-center justify-center rounded-full text-ink/60 hover:bg-primary-light hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
					>
						<X className="h-6 w-6" />
					</button> */}
				</div>

				<div className="px-5 py-6 sm:px-8 sm:py-8">
					<HomeOfferContent />

					<div className="mt-6 space-y-4">
						<a
							href="#sale_video"
							onClick={closePopup}
							className="inline-flex min-h-14 w-full items-center justify-center rounded-full bg-primary px-6 py-4 text-center text-base font-bold text-white shadow-lg shadow-primary/25 transition-colors hover:bg-primary-dark sm:text-lg"
						>
							Watch our purpose
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
					<p className="mt-5 text-center text-xs text-ink/45">
						At the end, scroll down twice to close this offer.
					</p>
				</div>
			</section>
		</div>
	);
}
