export function normalizeEnabledFeaturesResponse(response) {
  return Array.isArray(response?.features) ? response.features : null
}
