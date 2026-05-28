import type { SitegraphFullDocument } from '@njupt-search/contracts';
import { normalizeSearchText as normalize } from '../tokenizer';

export type CampusSearchIntent =
    | 'exam_schedule'
    | 'academic_calendar'
    | 'system_entry'
    | 'form_download'
    | 'academic_policy'
    | 'course_grade_credit'
    | 'scholarship_aid'
    | 'student_affairs'
    | 'innovation_entrepreneurship'
    | 'broad_exploratory';

export type FreshnessMode = 'current_notice' | 'current_term' | 'official_entry' | 'form_version' | 'current_policy' | 'balanced';

export interface QueryIntentProfile {
    intent: CampusSearchIntent;
    authoritySources: string[];
    freshnessMode: FreshnessMode;
}

const includesAny = (text: string, terms: string[]): boolean => terms.some(term => text.includes(normalize(term)));

export const detectQueryIntent = (query: string): QueryIntentProfile => {
    const text = normalize(query);
    const systemAuthority = includesAny(text, ['双创', '创新创业', '大创'])
        ? ['cxcy']
        : includesAny(text, ['心理', '学工', '资助', '就业', '征兵'])
            ? ['xsc']
            : ['jwc'];

    if (includesAny(text, ['教务管理系统', '正方教务', 'jwxt', '双创信息管理系统', '心理健康', '心理咨询', '信息门户', '系统', '门户'])) {
        return { intent: 'system_entry', authoritySources: systemAuthority, freshnessMode: 'official_entry' };
    }
    if (includesAny(text, ['期末考试', '考试安排', '补考', '重修考试', '慕课考试', '考场', '考试周'])) {
        return { intent: 'exam_schedule', authoritySources: ['jwc'], freshnessMode: 'current_term' };
    }
    if (includesAny(text, ['校历', '教学周历', '教学日历', '放假安排'])) {
        return { intent: 'academic_calendar', authoritySources: ['jwc'], freshnessMode: 'current_term' };
    }
    if (includesAny(text, ['申请表', '表格', 'xlsx', 'xls', '下载', '附件'])) {
        return { intent: 'form_download', authoritySources: ['jwc', 'xsc', 'cxcy'], freshnessMode: 'form_version' };
    }
    if (includesAny(text, ['转专业', '推免', '免试攻读', '培养方案', '学籍', '管理办法', '规章制度', '政策文件'])) {
        return { intent: 'academic_policy', authoritySources: ['jwc'], freshnessMode: 'current_policy' };
    }
    if (includesAny(text, ['选课', '成绩', '绩点', '学分', '课程'])) {
        return { intent: 'course_grade_credit', authoritySources: ['jwc'], freshnessMode: 'current_notice' };
    }
    if (includesAny(text, ['奖学金', '助学金', '资助', '困难认定', '家庭经济困难', '评奖评优'])) {
        return { intent: 'scholarship_aid', authoritySources: ['xsc'], freshnessMode: 'current_notice' };
    }
    if (includesAny(text, ['辅导员', '心理', '宿舍', '征兵', '就业', '学工', '一站式'])) {
        return { intent: 'student_affairs', authoritySources: ['xsc'], freshnessMode: 'balanced' };
    }
    if (includesAny(text, ['大创', '创新创业', '双创', '互联网+', '挑战杯', '竞赛报名', '竞赛', '创业'])) {
        return { intent: 'innovation_entrepreneurship', authoritySources: ['cxcy'], freshnessMode: 'current_notice' };
    }
    return { intent: 'broad_exploratory', authoritySources: ['jwc', 'xsc', 'cxcy'], freshnessMode: 'balanced' };
};

export const sourceIdForDocument = (document: SitegraphFullDocument): string => {
    return document.source_id || document.provenance.site_id || document.id.split('-', 1)[0] || '';
};
