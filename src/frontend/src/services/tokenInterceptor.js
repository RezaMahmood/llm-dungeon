/**
 * Attaches an `Authorization: Bearer <token>` header to every outgoing request
 * and retries once with a freshly-refreshed token on a 401 response.
 */
export function installTokenInterceptor(axiosInstance, { getToken, refreshToken }) {
  axiosInstance.interceptors.request.use(async (requestConfig) => {
    const token = await getToken();
    if (token) {
      requestConfig.headers.Authorization = `Bearer ${token}`;
    }
    return requestConfig;
  });

  axiosInstance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;
      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;
        const newToken = await refreshToken();
        if (newToken) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return axiosInstance(originalRequest);
        }
      }
      return Promise.reject(error);
    },
  );

  return axiosInstance;
}
