import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const authApiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: { 'Content-Type': 'application/json' },
});

export const signupUser = async (email, password) => {
    try {
        const response = await authApiClient.post('/api/signup', { email, password });
        return response.data;
    } catch (error) {
        if (error.response && error.response.data && error.response.data.detail) {
            if (Array.isArray(error.response.data.detail)) {
                throw new Error(error.response.data.detail[0].msg);
            }
            throw new Error(error.response.data.detail);
        }
        throw new Error('Signup failed. Please try again.');
    }
};

export const loginUser = async (email, password) => {
    try {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await axios.post(`${API_BASE_URL}/api/token`, formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        });
        return response.data;
    } catch (error) {
        throw new Error(error.response?.data?.detail || 'Login failed');
    }
};

const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    if (!token) throw new Error("No auth token found. Please log in.");
    return { Authorization: `Bearer ${token}` };
};

export const createCase = async (caseDetails) => {
    try {
        const response = await authApiClient.post('/api/case', caseDetails, {
            headers: getAuthHeaders(),
        });
        return response.data; // Now includes 'id'
    } catch (error) {
        throw new Error(error.response?.data?.detail || 'Failed to create case');
    }
};

// Updated to accept caseId
export const uploadDocuments = async (caseId, files) => {
    const formData = new FormData();
    // Append the case_id so the backend knows where these files belong
    formData.append('case_id', caseId);

    files.forEach(file => {
        formData.append('files', file);
    });

    try {
        const response = await axios.post(`${API_BASE_URL}/api/upload-documents`, formData, {
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    } catch (error) {
        throw new Error(error.response?.data?.detail || 'Failed to upload documents');
    }
};