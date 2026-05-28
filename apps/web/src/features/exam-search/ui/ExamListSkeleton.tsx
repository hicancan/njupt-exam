import { SkeletonBlock } from '@/shared/ui/SkeletonBlock';

export function ExamListSkeleton() {
    const classWidths = ['w-24', 'w-28', 'w-24', 'w-32', 'w-28', 'w-24', 'w-32', 'w-28'];

    return (
        <div className="w-full mt-2 fade-in">
            <SkeletonBlock className="h-4 w-72 max-w-full rounded mb-6" />

            <div className="flex flex-wrap gap-3">
                {classWidths.map((width, index) => (
                    <SkeletonBlock key={index} className={`h-10 ${width} rounded-full shadow-sm`} />
                ))}
            </div>
        </div>
    );
}
