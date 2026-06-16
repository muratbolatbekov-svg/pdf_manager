function appI18n(key, fallback) {
  const node = document.getElementById('app-i18n');
  if (!node) return fallback;
  try {
    const data = JSON.parse(node.textContent);
    return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : fallback;
  } catch (e) {
    return fallback;
  }
}
