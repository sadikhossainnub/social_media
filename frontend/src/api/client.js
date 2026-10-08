/**
 * Frappe API Client for Social Desk Portal
 * Handles REST requests to social_media.facebook.portal_api whitelist endpoints.
 */

let csrfToken = window.fbPortalData?.csrfToken || '';

export function setCsrfToken(token) {
  csrfToken = token;
}

export function getCsrfToken() {
  return csrfToken;
}

export async function callApi(method, params = {}, options = {}) {
  const url = `/api/method/social_media.facebook.portal_api.${method}`;
  
  const headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
  };

  if (csrfToken) {
    headers['X-Frappe-CSRF-Token'] = csrfToken;
  }

  const fetchOptions = {
    method: options.httpMethod || 'POST',
    headers,
    credentials: 'same-origin',
  };

  if (fetchOptions.method === 'POST') {
    fetchOptions.body = JSON.stringify(params);
  } else {
    // GET params
    const query = new URLSearchParams(params).toString();
    if (query) {
      fetchOptions.url = `${url}?${query}`;
    }
  }

  try {
    const response = await fetch(fetchOptions.url || url, fetchOptions);
    
    if (response.status === 401) {
      return { success: false, message: 'Session expired. Please log in again.', status_code: 401 };
    }

    const json = await response.json();

    // Update CSRF token if returned in headers or response
    if (response.headers.get('X-Frappe-CSRF-Token')) {
      csrfToken = response.headers.get('X-Frappe-CSRF-Token');
    }

    // Frappe wraps response in `message`
    if (json.message !== undefined) {
      if (typeof json.message === 'object' && json.message.success !== undefined) {
        return json.message;
      }
      return { success: true, data: json.message };
    }

    return json;
  } catch (err) {
    console.error(`API Call failed [${method}]:`, err);
    return { success: false, message: err.message || 'Network error' };
  }
}
