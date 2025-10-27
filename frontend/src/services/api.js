import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// This is a new, clean axios instance for public auth routes
const authApiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: { 'Content-Type': 'application/json' },
});

// --- NEW Authentication Functions ---
export const signupUser = async (email, password) => {
    try {
        const response = await authApiClient.post('/api/signup', { email, password });
        return response.data;
    } catch (error) {
        // Pydantic validation errors will be in error.response.data.detail
        if (error.response && error.response.data && error.response.data.detail) {
            if (Array.isArray(error.response.data.detail)) {
                // Handle complex Pydantic errors
                throw new Error(error.response.data.detail[0].msg);
            }
            throw new Error(error.response.data.detail);
        }
        throw new Error('Signup failed. Please try again.');
    }
};

export const loginUser = async (email, password) => {
    try {
        // FastAPI's OAuth2 expects 'x-www-form-urlencoded' data
        const formData = new URLSearchParams();
        formData.append('username', email); // It expects 'username', not 'email'
        formData.append('password', password);

        const response = await axios.post(`${API_BASE_URL}/api/token`, formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        });
        return response.data; // This will be { access_token: "...", token_type: "bearer" }
    } catch (error) {
        throw new Error(error.response?.data?.detail || 'Login failed');
    }
};


// --- UPDATED Protected Functions ---
// These functions now get the token from localStorage and add it to the header

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
        return response.data;
    } catch (error) {
        throw new Error(error.response?.data?.detail || 'Failed to create case');
    }
};

export const uploadDocuments = async (files) => {
    const formData = new FormData();
    files.forEach(file => {
        formData.append('files', file);
    });

    try {
        const response = await axios.post(`${API_BASE_URL}/api/upload-documents`, formData, {
            headers: {
                ...getAuthHeaders(), // Adds the 'Authorization' header
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    } catch (error) {
        throw new Error(error.response?.data?.detail || 'Failed to upload documents');
    }
};
