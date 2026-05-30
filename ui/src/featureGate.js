export function normalizeEnabledFeaturesResponse(response) {
  return Array.isArray(response?.features) ? response.features : null
}

export function isFeatureEnabled(featureId, enabledFeatures, bundled = false) {
  if (Array.isArray(enabledFeatures)) return enabledFeatures.includes(featureId)
  return Boolean(bundled)
}
