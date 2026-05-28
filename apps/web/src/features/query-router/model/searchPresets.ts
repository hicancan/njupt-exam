export type QuickSearchIcon =
    | 'calendar'
    | 'shuffle'
    | 'download'
    | 'waypoints'
    | 'trophy'
    | 'file-text';

export interface QuickSearchPreset {
    label: string;
    query: string;
    icon: QuickSearchIcon;
}

export const QUICK_SEARCHES: QuickSearchPreset[] = [
    { label: '期末考试', query: '期末考试', icon: 'calendar' },
    { label: '校历', query: '校历', icon: 'calendar' },
    { label: '四六级', query: '四六级', icon: 'file-text' },
    { label: '计算机等级', query: '计算机等级', icon: 'file-text' },
    { label: '口语考试', query: '口语考试', icon: 'file-text' },
    { label: '比赛报名', query: '竞赛报名', icon: 'trophy' },
    { label: '奖学金', query: '奖学金', icon: 'trophy' },
    { label: '大创', query: '大创', icon: 'trophy' },
];
