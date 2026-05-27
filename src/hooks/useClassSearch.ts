import { useMemo } from 'react';
import type { Exam, SearchResult } from '@/types';
import { getClassSearchResult } from '@/utils/examQuery';

export { getClassSearchResult };

export const useClassSearch = (
    exams: Exam[],
    inputValue: string,
    manualSelection: string | null
): SearchResult => {
    return useMemo(
        () => getClassSearchResult(exams, inputValue, manualSelection),
        [exams, inputValue, manualSelection]
    );
};
