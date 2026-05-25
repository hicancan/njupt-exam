import routesData from '../../config/query_routes.json';

export interface QueryRoute {
  id: string;
  triggers?: string[];
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

export interface RouteResult {
  raw_query: string;
  normalized_query: string;
  query_type: string;
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
}

const queryRoutes: QueryRoute[] = routesData as QueryRoute[];

export function routeQuery(rawQuery: string): RouteResult {
  const normalizedQuery = (rawQuery || '').replace(/\s+/g, ' ').trim();
  
  let bestRoute: QueryRoute = {
    id: 'general_search',
    query_type: 'general_search',
    allow_resource_top5: true,
    freshness_preference: 'none'
  };
  
  let confidence = 0.0;
  
  for (const route of queryRoutes) {
    const triggers = route.triggers || [];
    const lowerQuery = normalizedQuery.toLowerCase();
    if (triggers.some(trigger => lowerQuery.includes(trigger.toLowerCase()))) {
      bestRoute = route;
      confidence = 0.95;
      break;
    }
  }
  
  if (/^[A-Za-z]\d{6,8}$/.test(normalizedQuery)) {
    const classRoute = queryRoutes.find(r => r.id === 'class_exam_lookup');
    if (classRoute) {
      bestRoute = classRoute;
      confidence = 0.99;
    }
  }
  
  return {
    raw_query: rawQuery,
    normalized_query: normalizedQuery,
    query_type: bestRoute.query_type || 'general_search',
    route_confidence: confidence,
    route_source: 'query_routes',
    target_domains: [...(bestRoute.must_domains || []), ...(bestRoute.preferred_domains || [])],
    target_intents: bestRoute.preferred_intents || [],
    preferred_sources: bestRoute.preferred_sources || [],
    preferred_channels: bestRoute.preferred_channels || [],
    blocked_domains_for_top5: bestRoute.blocked_domains_for_top5 || [],
    blocked_sources_for_top5: bestRoute.blocked_sources_for_top5 || [],
    allow_resource_top5: bestRoute.allow_resource_top5 !== false,
    freshness_preference: bestRoute.freshness_preference || 'none'
  };
}
