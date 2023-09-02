import axios from "axios";

const API_URL = "http://127.0.0.1:5000";

const getState = () => {
  return axios.get(API_URL + "/state");
};

const apiFunctions = {
  getState,
};

export default apiFunctions;
