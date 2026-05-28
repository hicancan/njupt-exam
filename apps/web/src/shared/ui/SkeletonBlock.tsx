interface SkeletonBlockProps {
    className: string;
}

export function SkeletonBlock({ className }: SkeletonBlockProps) {
    return (
        <div aria-hidden="true" className={`relative overflow-hidden bg-[#f1f3f4] dark:bg-[#303134] ${className}`}>
            <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/40 dark:via-white/10 to-transparent animate-shimmer" />
        </div>
    );
}
