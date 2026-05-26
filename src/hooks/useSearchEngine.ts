import { useEffect, useState } from 'react';
import { RankedSitegraphDocument, SitegraphIndexBundle } from '@/types';
import { recallSitegraphDocuments } from '@/utils/searchIndex';

export function useSearchEngine(
    bundle: SitegraphIndexBundle | null,
    searchQuery: string
) {
    const [recalledResults, setRecalledResults] = useState<RankedSitegraphDocument[]>([]);
    const [searching, setSearching] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const trimmed = searchQuery.trim();
    const canSearch = Boolean(bundle && trimmed.length >= 2);

    useEffect(() => {
        const controller = new AbortController();
        if (!bundle || trimmed.length < 2) return () => controller.abort();

        Promise.resolve()
            .then(() => {
                if (!controller.signal.aborted) setSearching(true);
                return recallSitegraphDocuments(bundle, trimmed, controller.signal);
            })
            .then(results => {
                if (!controller.signal.aborted) {
                    setRecalledResults(results);
                    setError(null);
                }
            })
            .catch(err => {
                if (err instanceof DOMException && err.name === 'AbortError') return;
                console.error(err);
                if (!controller.signal.aborted) {
                    setRecalledResults([]);
                    setError(err instanceof Error ? err.message : '搜索 JWC sitegraph 失败');
                }
            })
            .finally(() => {
                if (!controller.signal.aborted) setSearching(false);
            });

        return () => controller.abort();
    }, [bundle, trimmed]);

    return {
        recalledResults: canSearch ? recalledResults : [],
        searching: canSearch ? searching : false,
        searchError: canSearch ? error : null
    };
}
