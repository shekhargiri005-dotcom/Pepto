import api from './api.js';

/**
 * Get all pets for the current user
 */
export const getMyPets = async () => {
  const response = await api.get('/pets');
  return response.data;
};

/**
 * Get a single pet by ID
 */
export const getPet = async (id) => {
  const response = await api.get(`/pets/${id}`);
  return response.data;
};

/**
 * Create a new pet
 */
export const createPet = async (data) => {
  const response = await api.post('/pets', data);
  return response.data;
};

/**
 * Update pet details
 */
export const updatePet = async (id, data) => {
  const response = await api.put(`/pets/${id}`, data);
  return response.data;
};

/**
 * Delete a pet
 */
export const deletePet = async (id) => {
  const response = await api.delete(`/pets/${id}`);
  return response.data;
};

/**
 * Upload pet photo
 */
export const uploadPetPhoto = async (id, file) => {
  const formData = new FormData();
  formData.append('photo', file);
  const response = await api.post(`/pets/${id}/photo`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

/**
 * Add vaccination record
 */
export const addVaccination = async (petId, data) => {
  const response = await api.post(`/pets/${petId}/vaccinations`, data);
  return response.data;
};

/**
 * Get vaccination records
 */
export const getVaccinations = async (petId) => {
  const response = await api.get(`/pets/${petId}/vaccinations`);
  return response.data;
};

/**
 * Add medical record
 */
export const addMedicalRecord = async (petId, data) => {
  const response = await api.post(`/pets/${petId}/medical`, data);
  return response.data;
};

const petService = {
  getMyPets,
  getPet,
  createPet,
  updatePet,
  deletePet,
  uploadPetPhoto,
  addVaccination,
  getVaccinations,
  addMedicalRecord,
};

export default petService;
