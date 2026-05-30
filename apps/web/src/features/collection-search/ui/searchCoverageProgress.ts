import type { SitegraphSearchCoverage } from '@/shared/lib/contracts';

export interface SearchCoverageProgress {
    completedShards: number;
    totalShards: number;
    percent: number;
    label: string;
    complete: boolean;
    showBar: boolean;
}

export function getSearchCoverageProgress(coverage: SitegraphSearchCoverage): SearchCoverageProgress {
    const totalShards = Math.max(0, coverage.total_shards);
    const completedShards = Math.min(
        totalShards,
        Math.max(0, coverage.scanned_shards) + Math.max(0, coverage.proved_no_match_shards)
    );
    const percent = totalShards > 0
        ? Math.min(100, Math.max(0, Math.round(completedShards / totalShards * 100)))
        : 0;

    const completeLabel = coverage.scope === 'scoped' ? '筛选范围已核查' : '全站范围已核查';

    return {
        completedShards,
        totalShards,
        percent: coverage.exhaustive_complete ? 100 : percent,
        label: coverage.exhaustive_complete ? completeLabel : `已核查 ${percent}%`,
        complete: coverage.exhaustive_complete,
        showBar: !coverage.exhaustive_complete,
    };
}
