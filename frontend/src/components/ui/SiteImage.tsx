import Image from "next/image";
import { clsx } from "clsx";

type SiteImageProps = {
  src: string;
  alt: string;
  aspect?: string;
  rounded?: string;
  className?: string;
  priority?: boolean;
};

// Fills its parent with a real photo/illustration, replacing the old
// dashed-border ImagePlaceholder boxes.
export function SiteImage({
  src,
  alt,
  aspect = "aspect-[4/3]",
  rounded = "rounded-3xl",
  className,
  priority = false,
}: SiteImageProps) {
  return (
    <div className={clsx("relative w-full overflow-hidden", aspect, rounded, className)}>
      <Image src={src} alt={alt} fill sizes="100vw" className="object-cover" priority={priority} />
    </div>
  );
}
