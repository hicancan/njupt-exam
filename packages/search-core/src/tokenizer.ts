const normalize = (value: unknown): string => String(value || '')
    .normalize('NFKC')
    .toLowerCase()
    .replace(/\s+/g, '');

export const normalizeSearchText = normalize;

export const expandSitegraphQueryPhrases = (query: string, queryAliases: Record<string, unknown> = {}): string[] => {
    const candidates = [query];
    const normalizedQuery = normalize(query);
    for (const [key, rawPayload] of Object.entries(queryAliases)) {
        const payload = rawPayload && typeof rawPayload === 'object' ? rawPayload as { aliases?: unknown[] } : {};
        const terms = [key, ...(Array.isArray(payload.aliases) ? payload.aliases.map(String) : [])];
        if (terms.some(term => normalize(term) && normalizedQuery.includes(normalize(term)))) {
            candidates.push(...terms);
        }
    }

    return Array.from(new Set(candidates.map(normalize).filter(text => text.length >= 2)))
        .sort((a, b) => b.length - a.length);
};

export const tokenizeSitegraphQuery = (query: string, queryAliases: Record<string, unknown> = {}): string[] => {
    const candidates = expandSitegraphQueryPhrases(query, queryAliases);

    const tokens = new Set<string>();
    for (const candidate of candidates) {
        const text = normalize(candidate);
        tokens.add(text);
        const matches = text.match(/[\u4e00-\u9fff]{2,}|[a-z0-9][a-z0-9._-]{1,}/g) || [];
        for (const part of matches) {
            if (/^[\u4e00-\u9fff]+$/.test(part)) {
                const maxSize = Math.min(5, part.length);
                for (let size = 2; size <= maxSize; size += 1) {
                    for (let index = 0; index <= part.length - size; index += 1) {
                        tokens.add(part.slice(index, index + size));
                    }
                }
            } else {
                tokens.add(part);
            }
        }
    }
    return Array.from(tokens).sort((a, b) => b.length - a.length);
};
