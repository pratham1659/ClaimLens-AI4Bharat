import axios from './axios';

export const authAPI = {
  login: async (email, password) => {
    console.log('[authAPI.login] Called with email:', email);
    const response = await axios.post('/auth/login', { email, password });
    console.log('[authAPI.login] Response:', response.data);
    return response.data;
  },

  logout: async () => {
    console.log('[authAPI.logout] Called');
    const response = await axios.post('/auth/logout');
    console.log('[authAPI.logout] Response:', response.data);
    return response.data;
  },

  getCurrentUser: async () => {
    console.log('[authAPI.getCurrentUser] Called');
    const response = await axios.get('/auth/me');
    console.log('[authAPI.getCurrentUser] Response:', response.data);
    return response.data;
  },
};
