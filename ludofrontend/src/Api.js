import axios from "axios";

const API_URL = "http://127.0.0.1:5000";

const getState = () => {
  return axios.get(API_URL + "/state");
};

const postMove = (data) => {
  return axios.post(API_URL + "/take_move", data);
};

const apiFunctions = {
  getState,
  postMove,
};

export default apiFunctions;
