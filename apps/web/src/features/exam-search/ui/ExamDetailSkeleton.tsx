import { SkeletonBlock } from '@/shared/ui/SkeletonBlock';

function ExamCardSkeleton() {
    return (
        <div className="block p-5 pl-4 border-l-4 border-transparent">
            <div className="flex items-start gap-4">
                <SkeletonBlock className="mt-1 h-5 w-5 rounded shrink-0" />

                <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start mb-3 gap-3">
                        <SkeletonBlock className="h-6 w-56 max-w-[70%] rounded" />
                        <SkeletonBlock className="h-5 w-14 rounded shrink-0" />
                    </div>

                    <div className="space-y-3">
                        <div className="flex items-start gap-2">
                            <SkeletonBlock className="h-4 w-4 mt-0.5 rounded shrink-0" />
                            <SkeletonBlock className="h-4 w-80 max-w-full rounded" />
                        </div>
                        <div className="flex items-start gap-2">
                            <SkeletonBlock className="h-4 w-4 mt-0.5 rounded shrink-0" />
                            <SkeletonBlock className="h-4 w-48 max-w-full rounded" />
                        </div>
                        <div className="flex flex-wrap gap-x-5 gap-y-2 pt-1">
                            <SkeletonBlock className="h-6 w-24 rounded" />
                            <SkeletonBlock className="h-5 w-20 rounded" />
                            <SkeletonBlock className="h-5 w-16 rounded" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export function ExamDetailSkeleton() {
    return (
        <div className="fade-in w-full">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-6">
                <div className="min-w-0 flex-1">
                    <SkeletonBlock className="h-8 w-72 max-w-full rounded mb-3" />
                    <div className="flex items-center gap-3">
                        <SkeletonBlock className="h-4 w-28 rounded" />
                        <SkeletonBlock className="h-4 w-20 rounded" />
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
                        <SkeletonBlock className="h-4 w-60 max-w-full rounded" />
                        <SkeletonBlock className="h-4 w-40 rounded" />
                        <SkeletonBlock className="h-4 w-28 rounded" />
                    </div>
                </div>
                <SkeletonBlock className="h-10 w-36 rounded-full shrink-0" />
            </div>

            <div className="mb-6 rounded-lg border border-[#dadce0] dark:border-[#3c4043] bg-[#f8f9fa] dark:bg-[#202124] p-4">
                <div className="flex items-center gap-2 mb-3">
                    <SkeletonBlock className="h-5 w-5 rounded-full" />
                    <SkeletonBlock className="h-4 w-24 rounded" />
                </div>
                <div className="flex flex-wrap gap-2">
                    {[0, 1, 2, 3].map(item => (
                        <SkeletonBlock key={item} className="h-8 w-20 rounded-full" />
                    ))}
                </div>
            </div>

            <div className="space-y-0 border border-[#dadce0] dark:border-[#3c4043] rounded-lg overflow-hidden bg-white dark:bg-[#202124]">
                {[0, 1, 2].map(item => (
                    <div key={item} className={item !== 2 ? 'border-b border-[#dadce0] dark:border-[#3c4043]' : ''}>
                        <ExamCardSkeleton />
                    </div>
                ))}
            </div>
        </div>
    );
}
