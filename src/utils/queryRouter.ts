import routesData from '../../config/query_routes.json';

export interface QueryRoute {
  id: string;
  priority?: number;
  triggers?: string[];
  must_have_any?: string[];
  soft_terms?: string[];
  negative_terms?: string[];
  query_type: string;
  must_domains?: string[];
  preferred_domains?: string[];
  preferred_sources?: string[];
  preferred_channels?: string[];
  preferred_intents?: string[];
  blocked_domains_for_top5?: string[];
  blocked_sources_for_top5?: string[];
  allow_resource_top5?: boolean;
  freshness_preference?: string;
  explanation?: string;
}

export interface RouteAlternative {
  query_type: string;
  score: number;
}

export interface RouteResult {
  raw_query: string;
  normalized_query: string;
  query_type: string;
  route_score: number;
  route_confidence: number;
  route_source: string;
  target_domains: string[];
  target_intents: string[];
  preferred_sources: string[];
  preferred_channels: string[];
  blocked_domains_for_top5: string[];
  blocked_sources_for_top5: string[];
  allow_resource_top5: boolean;
  freshness_preference: string;
  alternative_routes: RouteAlternative[];
  explanation: string;
}

const queryRoutes: QueryRoute[] = routesData as QueryRoute[];

export function routeQuery(rawQuery: string): RouteResult {
  const normalizedQuery = (rawQuery || '').replace(/\s+/g, ' ').trim();
  const queryLower = normalizedQuery.toLowerCase();
  
  const scoredRoutes = queryRoutes.map(route => {
    let score = (route.priority !== undefined ? route.priority : 50) / 100.0;
    
    const mustHave = route.must_have_any || [];
    if (mustHave.length > 0) {
      if (!mustHave.some(term => queryLower.includes(term.toLowerCase()))) {
        if (route.id === 'class_exam_lookup' && /^[a-z]\d{6,8}/.test(queryLower)) {
          // Pass
        } else {
          score -= 1000;
        }
      }
    }
    
    if (route.id === 'class_exam_lookup' && /^[a-z]\d{6,8}/.test(queryLower)) {
      score += 100;
    }
    
    const triggers = route.triggers || [];
    for (const trigger of triggers) {
      if (queryLower.includes(trigger.toLowerCase())) {
        score += 50;
      }
    }
    
    const softTerms = route.soft_terms || [];
    for (const term of softTerms) {
      if (queryLower.includes(term.toLowerCase())) {
        score += 15;
      }
    }
    
    const negativeTerms = route.negative_terms || [];
    for (const term of negativeTerms) {
      if (queryLower.includes(term.toLowerCase())) {
        score -= 50;
      }
    }
    
    return { route, score };
  });
  
  scoredRoutes.sort((a, b) => b.score - a.score);
  
  const best = scoredRoutes[0] || {
    route: { id: 'general_search', query_type: 'general_search' } as QueryRoute,
    score: 0
  };
  const bestRoute = best.route;
  const bestScore = best.score;
  
  let confidence = 0.5;
  if (bestScore >= 80) confidence = 0.95;
  else if (bestScore >= 60) confidence = 0.8;
  
  const altRoutes = scoredRoutes
    .slice(1, 4)
    .filter(r => r.score > 0)
    .map(r => ({ query_type: r.route.query_type, score: r.score }));
  
  return {
    raw_query: rawQuery,
    normalized_query: normalizedQuery,
    query_type: bestRoute.query_type || 'general_search',
    route_score: bestScore,
    route_confidence: confidence,
    route_source: 'query_routes_v2',
    target_domains: [...(bestRoute.must_domains || []), ...(bestRoute.preferred_domains || [])],
    target_intents: bestRoute.preferred_intents || [],
    preferred_sources: bestRoute.preferred_sources || [],
    preferred_channels: bestRoute.preferred_channels || [],
    blocked_domains_for_top5: bestRoute.blocked_domains_for_top5 || [],
    blocked_sources_for_top5: bestRoute.blocked_sources_for_top5 || [],
    allow_resource_top5: bestRoute.allow_resource_top5 !== false,
    freshness_preference: bestRoute.freshness_preference || 'none',
    alternative_routes: altRoutes,
    explanation: bestRoute.explanation || ''
  };
}
