import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000/api',
  withCredentials: true, // This is crucial for sending HttpOnly cookies
});

// The request interceptor for adding the Authorization header is no longer needed
// as the browser will handle the cookie automatically.

// We can add a response interceptor to automatically handle token refreshes.
apiClient.interceptors.response.use(
  (response) => response, // Directly return successful responses
  async (error) => {
    const originalRequest = error.config;

    // Check if the error is 401 Unauthorized and it's not a retry request
    // to prevent an infinite loop if the refresh token is also invalid.
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // Mark the request to avoid retrying again

      try {
        // Request a new access token. The refresh token cookie will be sent automatically.
        await apiClient.post('/token/refresh/');
        
        // If refresh is successful, retry the original request.
        // The new access_token cookie will be used automatically.
        return apiClient(originalRequest);
      } catch (refreshError) {
        // If the refresh token is also invalid, the refresh request will fail.
        // Here you would typically trigger a logout action.
        console.error("Session has expired. Please log in again.");
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    // For any other errors, just pass them along.
    return Promise.reject(error);
  }
);

export default apiClient;
